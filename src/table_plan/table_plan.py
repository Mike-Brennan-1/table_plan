from ortools.sat.python import cp_model
from ortools_utils import *

class SeatingSolver:
    def __init__(self, config: dict):
        self.config = config

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        

        self.tables = None
        self.delegates = None
        self.exhibitors = None
        self.maximise_for_affinity = None
        self.interactions = None

        self.delegate_school = None
        self.exhibitor_company = None

        self.schools = None
        self.exclusive_schools = None
        self.companies = None
        self.table_used = None
        self.table_used_by_school = {}
        
        self.x = None
        self.y = None
        self.z = None
        self.k = None
        self.n = None
        self.q_sc = None
        self.spread = None
        self.spread_scale_factor = 1000000

    def load_input_data(self, data: dict):
        self.delegates = data.delegates
        self.exhibitors = data.exhibitors
        self.delegate_school = data.delegate_school
        self.exhibitor_company = data.exhibitor_company

        self.schools = data.schools
        self.exclusive_schools = data.exclusive_schools
        self.companies = data.companies
        if self.config["maximise_for_affinity"]:
            self.interactions = data.interactions

    def make_tables(self):
        self.tables = make_table_list(self.config["table_count"])

        self.table_used = {
            t : self.model.new_bool_var(
                f"table_used_{t}") for t in self.tables
        }

    def make_seating_variables(self):
        
        self.x = make_seating_bool_vars(
            self.model, 
            self.delegates, 
            self.tables, 
            "x"
        )

        self.y = make_seating_bool_vars(
            self.model, 
            self.exhibitors, 
            self.tables, 
            "y"
        )

        self.z = make_seating_bool_vars(
            self.model, 
            self.schools,
            self.tables, 
            "z"
        )

        self.k = make_seating_bool_vars(
            self.model,
            self.companies,
            self.tables,
            "k"
        )

    def capacity_constraints(self):

        self.n = {}

        minimum_capacity = self.config["minimum_capacity"]
        maximum_capacity = self.config["maximum_capacity"]

        for t in self.tables:
            self.n[t] = self.model.new_int_var(0, maximum_capacity, f"n_{t}")

            self.model.add(
                self.n[t] ==
                sum(self.x[d, t] for d in self.delegates) +
                sum(self.y[e, t] for e in self.exhibitors)
            )

            self.model.add(self.n[t] >= minimum_capacity * self.table_used[t])
            self.model.add(self.n[t] <= maximum_capacity * self.table_used[t])

    def assignment_constraints(self):

        for d in self.delegates:
            self.model.add(sum(self.x[d, t] for t in self.tables) == 1)

        for e in self.exhibitors:
            self.model.add(sum(self.y[e, t] for t in self.tables) == 1)

    def grouping_constraints(self):

        for d in self.delegates:
            s = self.delegate_school[d]
            for t in self.tables:
                self.model.add(self.x[d, t] <= self.z[s, t])

        for t in self.tables:
            self.model.add(sum(self.k[c, t] for c in self.companies) <= self.config["max_companies"])

        for s in self.schools:
            tables_used = self.model.new_int_var(0, len(self.tables), f"tables_used_{s}")

            self.model.add(
                tables_used == sum(self.z[s, t] for t in self.tables)
            )

            self.table_used_by_school[s] = tables_used

        self.spread = self.model.new_int_var(0, 1000000, "spread")

        self.model.add(
            self.spread == sum(self.table_used_by_school[s] for s in self.schools)
        )

        if self.exclusive_schools:
            for es, num_tables in self.exclusive_schools.items():
                
                self.model.add(
                    sum(self.z[es, t] for t in self.tables) == num_tables
                )
                
                for t in self.tables:
                    self.model.add(
                        sum(self.z[s, t] for s in self.schools if s != es) == 0
                    ).only_enforce_if(self.z[es, t])
                
        if self.config["exhibitors_sit_together"]:
            for e in self.exhibitors:
                c = self.exhibitor_company[e]
                for t in self.tables:
                    self.model.add(self.y[e, t] == self.k[c, t])
                self.model.add(sum(self.y[e, t] for t in self.tables) == 1)

            for ec in self.companies:
                self.model.add(sum(self.k[ec, t] for t in self.tables) == 1)

    def affinity_vars(self):
        self.q_sc = {}

        for (school, company), score in self.interactions.items():
            if company not in self.companies:
                continue
            for t in self.tables:
                self.q_sc[school, company, t] = self.model.new_bool_var(f"q_sc_{school}_{company}_{t}")

                self.model.add_bool_and(self.z[school, t], self.k[company, t]).only_enforce_if(self.q_sc[school, company, t])

    def minimise_spread(self):
        self.model.minimize(
            self.spread * self.spread_scale_factor
        )

    def maximise_objective(self):
        objective_components = []

        for (school, company), score in self.interactions.items():
            if company not in self.companies:
                continue
            for t in self.tables:
                objective_components.append(
                    score * self.q_sc[school, company, t]
                    )
            
        self.model.maximize(sum(objective_components))

    def build_model(self):
        self.make_tables()
        self.make_seating_variables()
        self.capacity_constraints()
        self.assignment_constraints()
        self.grouping_constraints()
        self.minimise_spread()

        if self.config["maximise_for_affinity"]:
            self.affinity_vars()
            self.maximise_objective()

        #self.model.minimize(sum(self.table_used[t] for t in self.tables))

    def extract_solution(self, status):
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return None

        solution = {}

        for t in self.tables:
            delegates_at_table = [
                d for d in self.delegates
                if self.solver.Value(self.x[d, t])
            ]

            exhibitors_at_table = [
                e for e in self.exhibitors
                if self.solver.Value(self.y[e, t])
            ]

            if delegates_at_table or exhibitors_at_table:
                solution[t] = {
                    "delegates": delegates_at_table,
                    "exhibitors": exhibitors_at_table
                }

        return solution

    def solve(self, data: dict):
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        self.load_input_data(data)
        self.build_model()

        status = self.solver.Solve(self.model)

        return self.extract_solution(status)
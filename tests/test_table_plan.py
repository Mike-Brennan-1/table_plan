import pytest

from data_config import ModelInput
from table_plan import SeatingSolver


def make_config(**overrides):
    config = {
        "table_count": 2,
        "minimum_capacity": 0,
        "maximum_capacity": 4,
        "exhibitors_sit_together": True,
        "max_companies": 1,
        "maximise_for_affinity": False,
    }
    config.update(overrides)
    return config


@pytest.fixture
def model_input():
    # Delegates 0-1 from school 0, delegates 2-3 from school 1,
    # exhibitors 10-11 from company 100, exhibitor 12 from company 101.
    return ModelInput(
        delegates=[0, 1, 2, 3],
        exhibitors=[10, 11, 12],
        delegate_school={0: 0, 1: 0, 2: 1, 3: 1},
        exhibitor_company={10: 100, 11: 100, 12: 101},
        schools={0, 1},
        companies={100, 101},
    )


def table_of(solution, guest, role):
    tables = [t for t, seated in solution.items() if guest in seated[role]]
    assert len(tables) == 1, f"{role[:-1]} {guest} seated at {tables}"
    return tables[0]


def test_every_guest_seated_exactly_once(model_input):
    solution = SeatingSolver(make_config()).solve(model_input)

    assert solution is not None
    seated_delegates = sorted(d for t in solution.values() for d in t["delegates"])
    seated_exhibitors = sorted(e for t in solution.values() for e in t["exhibitors"])
    assert seated_delegates == model_input.delegates
    assert seated_exhibitors == model_input.exhibitors


def test_capacity_respected(model_input):
    solution = SeatingSolver(make_config(maximum_capacity=4)).solve(model_input)

    for seated in solution.values():
        assert len(seated["delegates"]) + len(seated["exhibitors"]) <= 4


def test_minimise_spread_keeps_schools_together(model_input):
    solution = SeatingSolver(make_config()).solve(model_input)

    assert table_of(solution, 0, "delegates") == table_of(solution, 1, "delegates")
    assert table_of(solution, 2, "delegates") == table_of(solution, 3, "delegates")


def test_exhibitors_from_same_company_sit_together(model_input):
    solution = SeatingSolver(make_config()).solve(model_input)

    assert table_of(solution, 10, "exhibitors") == table_of(solution, 11, "exhibitors")


def test_max_companies_per_table(model_input):
    solution = SeatingSolver(make_config(max_companies=1)).solve(model_input)

    assert table_of(solution, 10, "exhibitors") != table_of(solution, 12, "exhibitors")


def test_infeasible_returns_none(model_input):
    # 7 guests cannot fit on 2 tables of 3.
    solution = SeatingSolver(make_config(maximum_capacity=3)).solve(model_input)

    assert solution is None


def test_minimum_capacity_infeasible_returns_none(model_input):
    # Each table holds exactly 0 or 4 guests, so 7 guests can't be seated.
    solution = SeatingSolver(make_config(minimum_capacity=4, maximum_capacity=4)).solve(model_input)

    assert solution is None


def test_empty_tables_are_omitted():
    data = ModelInput(
        delegates=[0, 1],
        exhibitors=[],
        delegate_school={0: 0, 1: 0},
        exhibitor_company={},
        schools={0},
        companies=set(),
    )

    solution = SeatingSolver(make_config(table_count=3)).solve(data)

    assert len(solution) == 1


def test_exclusive_school_gets_table_to_itself(model_input):
    model_input.exclusive_schools = {0: 1}
    config = make_config(table_count=3, maximum_capacity=5, max_companies=2)

    solution = SeatingSolver(config).solve(model_input)

    exclusive_table = table_of(solution, 0, "delegates")
    assert sorted(solution[exclusive_table]["delegates"]) == [0, 1]


def test_max_companies_enforced_when_exhibitors_can_split(model_input):
    config = make_config(exhibitors_sit_together=False, max_companies=1)

    solution = SeatingSolver(config).solve(model_input)

    company = model_input.exhibitor_company
    for seated in solution.values():
        assert len({company[e] for e in seated["exhibitors"]}) <= 1


def test_maximise_for_affinity_pairs_high_affinity_school_and_company(model_input):
    model_input.interactions = {
        (0, 100): 100, (0, 101): 0,
        (1, 100): 0, (1, 101): 100,
    }
    config = make_config(maximum_capacity=5, maximise_for_affinity=True)

    solution = SeatingSolver(config).solve(model_input)

    assert table_of(solution, 0, "delegates") == table_of(solution, 10, "exhibitors")
    assert table_of(solution, 2, "delegates") == table_of(solution, 12, "exhibitors")


def test_maximise_for_affinity_still_keeps_schools_together(model_input):
    model_input.interactions = {
        (0, 100): 100, (0, 101): 100,
        (1, 100): 100, (1, 101): 100,
    }
    config = make_config(maximum_capacity=5, maximise_for_affinity=True)

    solution = SeatingSolver(config).solve(model_input)

    assert table_of(solution, 0, "delegates") == table_of(solution, 1, "delegates")
    assert table_of(solution, 2, "delegates") == table_of(solution, 3, "delegates")


def test_time_limit_defaults_and_can_be_configured(model_input):
    default_solver = SeatingSolver(make_config())
    default_solver.solve(model_input)

    custom_solver = SeatingSolver(make_config(time_limit_seconds=5))
    custom_solver.solve(model_input)

    assert default_solver.solver.parameters.max_time_in_seconds == 60
    assert custom_solver.solver.parameters.max_time_in_seconds == 5


def test_solve_can_be_called_repeatedly(model_input):
    solver = SeatingSolver(make_config())

    first = solver.solve(model_input)
    second = solver.solve(model_input)

    assert first is not None and second is not None

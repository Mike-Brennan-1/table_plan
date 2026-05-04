from ortools.sat.python import cp_model

def make_table_list(
      tables: int
) -> list:
   
   """A helper function to make a list of variables for use in `ortools` models.

   Example usage:

   ```my_list = make_tabe_list(3)
   >> my_list = ["T1", "T2", "T3"]```
   """
   table_list = [f"T{t}" for t in range(tables)]
   return table_list

def make_seating_bool_vars(
                model: cp_model.CpModel,
                iterable: list,
                tables: list,
                var_name: str
) -> dict[tuple[str, str], cp_model.IntVar]:

   var_dict = {}

   for i in iterable:
      for t in tables:
         var_dict[i, t] = model.new_bool_var(f"{var_name}_{i}_{t}")
   
   return var_dict
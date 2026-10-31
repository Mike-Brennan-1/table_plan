from ortools.sat.python import cp_model

from ortools_utils import make_seating_bool_vars, make_table_list


def test_make_table_list_is_zero_indexed():
    assert make_table_list(3) == ["T0", "T1", "T2"]


def test_make_table_list_zero_tables():
    assert make_table_list(0) == []


def test_make_seating_bool_vars_creates_var_per_pair():
    model = cp_model.CpModel()
    tables = make_table_list(2)

    var_dict = make_seating_bool_vars(model, [10, 11, 12], tables, "x")

    assert set(var_dict) == {(i, t) for i in [10, 11, 12] for t in tables}
    assert var_dict[10, "T1"].name == "x_10_T1"


def test_make_seating_bool_vars_empty_iterable():
    model = cp_model.CpModel()
    assert make_seating_bool_vars(model, [], ["T0"], "x") == {}

import polars as pl
import pytest

from load_data import DataLoader


@pytest.fixture
def csv_files(tmp_path):
    delegates = tmp_path / "delegates.csv"
    pl.DataFrame({
        "School Account (Conference Register)": ["Beta School", "Alpha School", "Beta School"],
        "first_name": ["Ann", "Bob", "Cat"],
        "last_name": ["A", "B", "C"],
        "Job Title": ["Head", "Teacher", "Teacher"],
        "whole tables booked": ["1", None, "0"],
        "Unused Column": ["x", "y", "z"],
    }).write_csv(delegates)

    exhibitors = tmp_path / "exhibitors.csv"
    pl.DataFrame({
        "company": ["Gamma Ltd", "Gamma Ltd"],
        "first_name": ["Dan", "Eve"],
        "surname": ["D", "E"],
        "Status Reason": ["Active", "Active"],
        "whole tables booked": [0, 0],
    }).write_csv(exhibitors)

    interactions = tmp_path / "interactions.csv"
    pl.DataFrame({
        "Company": ["Gamma Ltd", "Gamma Ltd", "Gamma Ltd", "Unknown Ltd"],
        "school name": ["Alpha School", "Alpha School", "Unknown School", "Beta School"],
        "Time": ["t1", "t2", "t3", "t4"],
    }).write_csv(interactions)

    return delegates, exhibitors, interactions


@pytest.fixture
def loader(csv_files):
    delegates, exhibitors, interactions = csv_files
    loader = DataLoader()
    loader.df_configs = [
        {
            "path": str(delegates),
            "col_map": {
                "School Account (Conference Register)": "organisation",
                "first_name": "First name",
                "last_name": "Surname",
                "Job Title": "Job Title",
                "whole tables booked": "whole tables booked",
            },
            "type": "delegate",
        },
        {
            "path": str(exhibitors),
            "col_map": {
                "company": "organisation",
                "first_name": "First name",
                "surname": "Surname",
                "Status Reason": "Job Title",
                "whole tables booked": "whole tables booked",
            },
            "type": "exhibitor",
        },
    ]
    loader.interactions_config = {
        "path": str(interactions),
        "col_map": {"Company": "Company", "school name": "School"},
    }
    return loader


def test_clean_data_selects_and_renames(loader, csv_files):
    config = loader.df_configs[0]

    df = loader.clean_data(config["path"], config["col_map"])

    assert df.columns == ["organisation", "First name", "Surname", "Job Title", "whole tables booked"]
    assert df.height == 3


def test_clean_data_writes_csv_when_requested(loader, tmp_path):
    config = loader.df_configs[1]
    out_path = tmp_path / "cleaned.csv"

    df = loader.clean_data(config["path"], config["col_map"], w_path=str(out_path), write_cleaned_csv=True)

    assert pl.read_csv(out_path).equals(df)


def test_clean_data_raises_on_missing_column(loader):
    config = loader.df_configs[0]

    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        loader.clean_data(config["path"], {"Not A Column": "x"})


def test_add_group_id_assigns_ids_alphabetically():
    df = pl.DataFrame({"organisation": ["Charlie", "Alpha", "Charlie", "Bravo"]})

    result = DataLoader().add_group_id(df)

    assert result["group_id"].to_list() == [2, 0, 2, 1]


def test_join_datasets_combines_and_indexes(loader):
    df = loader.join_datasets()

    assert df.height == 5
    assert df["guest_id"].to_list() == [0, 1, 2, 3, 4]
    assert df["type"].to_list() == ["delegate"] * 3 + ["exhibitor"] * 2

    org_to_group = dict(zip(df["organisation"], df["group_id"]))
    assert org_to_group == {"Alpha School": 0, "Beta School": 1, "Gamma Ltd": 2}


def test_join_datasets_with_no_configs_returns_empty(loader):
    loader.df_configs = []
    assert loader.join_datasets().is_empty()


def test_load_interactions_drops_unknowns_and_duplicates(loader):
    combined = loader.join_datasets()

    interactions = loader.load_interactions(combined)

    # Unknown school/company rows are dropped by the inner joins, and the two
    # Alpha/Gamma rows collapse to one because Time isn't in the col_map.
    assert interactions.height == 1
    row = interactions.row(0, named=True)
    assert row["School"] == "Alpha School"
    assert row["Company"] == "Gamma Ltd"
    assert row["school_group_id"] == 0
    assert row["company_group_id"] == 2


def test_prepare_model_inputs_builds_mappings(loader):
    combined = loader.join_datasets()

    model_input = loader.prepare_model_inputs(combined)

    assert model_input.delegates == [0, 1, 2]
    assert model_input.exhibitors == [3, 4]
    assert model_input.delegate_school == {0: 1, 1: 0, 2: 1}
    assert model_input.exhibitor_company == {3: 2, 4: 2}
    assert model_input.schools == {0, 1}
    assert model_input.companies == {2}
    assert model_input.interactions is None


def test_prepare_model_inputs_exclusive_schools(loader):
    combined = loader.join_datasets()

    model_input = loader.prepare_model_inputs(combined, exclusives=True)

    # Beta School has "1" and "0" -> max is 1; Alpha School's null becomes 0.
    assert model_input.exclusive_schools == {1: 1}


def test_prepare_model_inputs_without_exclusives(loader):
    combined = loader.join_datasets()

    model_input = loader.prepare_model_inputs(combined, exclusives=False)

    assert model_input.exclusive_schools is None

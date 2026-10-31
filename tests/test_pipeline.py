import polars as pl
import pytest

import pipeline
from data_config import ModelInput
from pipeline import interactions_from_df


def test_interactions_from_df_maps_school_company_pairs():
    df = pl.DataFrame({"delegates": [0, 1], "5": [10, 20], "6": [30, 40]})

    interactions = interactions_from_df(df)

    assert len(interactions) == 4
    assert interactions[(1, 6)] == 40


def test_interactions_from_df_company_keys_match_group_ids():
    df = pl.DataFrame({"delegates": [0], "5": [10]})

    interactions = interactions_from_df(df)

    assert (0, 5) in interactions


class FakeLoader:
    def __init__(self, loading_interactions=False):
        self.loading_interactions = loading_interactions

    def join_datasets(self):
        return pl.DataFrame({"guest_id": [0]})

    def prepare_model_inputs(self, df):
        return ModelInput(
            delegates=[0], exhibitors=[], delegate_school={0: 0},
            exhibitor_company={}, schools={0}, companies=set(),
        )

    def load_interactions(self, combined_df):
        return pl.DataFrame()


class FakeRecommender:
    def recommender_pipeline(self, df):
        return pl.DataFrame({"delegates": [0], "5": [42]})


class FakeSolver:
    received = None

    def __init__(self, config):
        self.config = config

    def solve(self, model_input):
        FakeSolver.received = model_input
        return {"T0": {"delegates": [0], "exhibitors": []}}


@pytest.fixture
def fakes(monkeypatch):
    monkeypatch.setattr(pipeline, "DataLoader", FakeLoader)
    monkeypatch.setattr(pipeline, "Recommender", FakeRecommender)
    monkeypatch.setattr(pipeline, "SeatingSolver", FakeSolver)
    FakeSolver.received = None


def test_run_pipeline_without_affinity(fakes):
    solution, combined_df = pipeline.run_pipeline({"maximise_for_affinity": False})

    assert solution == {"T0": {"delegates": [0], "exhibitors": []}}
    assert combined_df["guest_id"].to_list() == [0]
    assert FakeSolver.received.interactions is None


def test_run_pipeline_with_affinity_passes_interactions(fakes):
    pipeline.run_pipeline({"maximise_for_affinity": True})

    assert FakeSolver.received.interactions == {(0, 5): 42}

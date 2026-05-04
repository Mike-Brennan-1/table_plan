from load_data import DataLoader
from recommender import Recommender
from table_plan import SeatingSolver

import polars as pl




def interactions_from_df(df: pl.DataFrame) -> dict:
    """
    Converts recommender output into solver-friendly dict:
    (school, company) -> score
    """
    interactions = {}

    company_cols = [c for c in df.columns if c != "delegates"]

    for row in df.iter_rows(named=True):
        school = row["delegates"]

        for col in company_cols:
            interactions[(school, col)] = row[col]

    return interactions


def run_pipeline(config: dict):
    loader = DataLoader(loading_interactions = config["maximise_for_affinity"])

    combined_df = loader.join_datasets()

    model_input = loader.prepare_model_inputs(combined_df)
    
    if config["maximise_for_affinity"]:
        interactions_df = loader.load_interactions(combined_df)
        recommender = Recommender()
        affinity_df = recommender.recommender_pipeline(interactions_df)
        model_input.interactions = interactions_from_df(affinity_df)
    else:
        model_input.interactions = None

    solver = SeatingSolver(config)

    solution = solver.solve(model_input)

    return solution, combined_df



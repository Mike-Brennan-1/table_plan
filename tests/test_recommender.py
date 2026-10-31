import math

import numpy as np
import polars as pl
import pytest

from recommender import Recommender, RecommenderEvaluator


@pytest.fixture
def interactions_df():
    return pl.DataFrame({
        "school_group_id": [0, 0, 1, 2, 2, 3],
        "company_group_id": [5, 6, 5, 6, 7, 7],
    })


@pytest.fixture
def recommender():
    return Recommender()


def test_make_sparse_matrix_shape_and_labels(recommender, interactions_df):
    X, delegates, exhibitors = recommender.make_sparse_matrix(interactions_df)

    assert X.shape == (4, 3)
    assert delegates == [0, 1, 2, 3]
    assert exhibitors == [5, 6, 7]
    assert X.toarray().tolist() == [
        [1, 1, 0],
        [1, 0, 0],
        [0, 1, 1],
        [0, 0, 1],
    ]


def test_make_sparse_matrix_sums_duplicate_interactions(recommender):
    df = pl.DataFrame({"school_group_id": [0, 0], "company_group_id": [5, 5]})

    X, _, _ = recommender.make_sparse_matrix(df)

    assert X.toarray().tolist() == [[2]]


def test_make_sparse_matrix_custom_column_names():
    rec = Recommender(delegate_id_col_name="d", exhibitor_id_col_name="e")
    df = pl.DataFrame({"d": [1, 2], "e": [9, 9]})

    X, delegates, exhibitors = rec.make_sparse_matrix(df)

    assert X.shape == (2, 1)
    assert delegates == [1, 2]
    assert exhibitors == [9]


def test_describe_matrix(recommender, interactions_df):
    X, _, _ = recommender.make_sparse_matrix(interactions_df)

    description = recommender.describe_matrix(X)

    assert "(4, 3)" in description
    assert "Total non-zero interactions: 6" in description


def test_cosine_similarity_transpose_is_item_item(recommender, interactions_df):
    X, _, _ = recommender.make_sparse_matrix(interactions_df)

    item_sim = recommender.calculate_cosine_similarity(X, transpose=True)
    user_sim = recommender.calculate_cosine_similarity(X, transpose=False)

    assert item_sim.shape == (3, 3)
    assert user_sim.shape == (4, 4)
    np.testing.assert_allclose(np.diag(item_sim), 1.0)
    np.testing.assert_allclose(item_sim, item_sim.T)


def test_predict_rows_are_l1_normalised(recommender, interactions_df):
    X, delegates, exhibitors = recommender.make_sparse_matrix(interactions_df)
    sim = recommender.calculate_cosine_similarity(X)

    pred = recommender.predict(X, sim, delegates, exhibitors, cast_to_int=False)

    np.testing.assert_allclose(pred.sum(axis=1), 1.0)


def test_predict_scales_and_casts_to_int(recommender, interactions_df):
    X, delegates, exhibitors = recommender.make_sparse_matrix(interactions_df)
    sim = recommender.calculate_cosine_similarity(X)

    pred = recommender.predict(X, sim, delegates, exhibitors, scale_factor=100)

    assert np.issubdtype(pred.dtype, np.integer)
    # Truncation means each row sums to at most the scale factor.
    assert (pred.sum(axis=1) <= 100).all()
    assert (pred.sum(axis=1) >= 100 - pred.shape[1]).all()


def test_predict_to_polars(recommender, interactions_df):
    X, delegates, exhibitors = recommender.make_sparse_matrix(interactions_df)
    sim = recommender.calculate_cosine_similarity(X)

    df = recommender.predict(X, sim, delegates, exhibitors, to_polars=True, row_index_name="schools")

    assert df.columns == ["schools", "5", "6", "7"]
    assert df["schools"].to_list() == delegates


def test_recommender_pipeline_ranks_interacted_company_highest(recommender, interactions_df):
    df = recommender.recommender_pipeline(interactions_df)

    # School 1 only interacted with company 5.
    school_1 = df.filter(pl.col("delegates") == 1).row(0, named=True)
    assert school_1["5"] > school_1["6"] > school_1["7"]


@pytest.fixture
def evaluator(recommender):
    return RecommenderEvaluator(recommender)


def test_random_mask_zeroes_requested_fraction(evaluator, recommender, interactions_df):
    np.random.seed(0)
    X, _, _ = recommender.make_sparse_matrix(interactions_df)
    original = X.toarray()

    X_masked, test_pairs = evaluator.random_mask(X, split=0.5)

    assert len(test_pairs) == 3
    assert len(set(test_pairs)) == 3
    for i, j in test_pairs:
        assert original[i, j] == 1
        assert X_masked[i, j] == 0
    assert X_masked.count_nonzero() == 3


def test_random_mask_zero_split_masks_nothing(evaluator, recommender, interactions_df):
    X, _, _ = recommender.make_sparse_matrix(interactions_df)

    X_masked, test_pairs = evaluator.random_mask(X, split=0.0)

    assert test_pairs == []
    assert X_masked.count_nonzero() == 6


def test_calculate_log_loss(evaluator):
    loss = evaluator.calculate_log_loss([1, 1], [0.5, 0.5])
    assert loss == pytest.approx(math.log(2))


def test_evaluate_returns_finite_loss(evaluator, interactions_df):
    np.random.seed(0)

    loss = evaluator.evaluate(interactions_df, split=0.5)

    assert np.isfinite(loss)
    assert loss >= 0


def test_evaluate_multiple(evaluator, interactions_df):
    np.random.seed(0)

    report = evaluator.evaluate_multiple(interactions_df, n_runs=3, split=0.5)

    assert report["n_runs"] == 3
    assert np.isfinite(report["average log_loss"])


def test_evaluate_multiple_verbose_returns_losses(evaluator, interactions_df):
    np.random.seed(0)

    report, losses = evaluator.evaluate_multiple(interactions_df, n_runs=4, split=0.5, verbose=True)

    assert len(losses) == 4
    assert report["average log_loss"] == pytest.approx(np.mean(losses))


def test_evaluate_solution_sums_affinity_scores(evaluator):
    affinity_df = pl.DataFrame({"delegates": [0, 1], "5": [70, 10], "6": [30, 90]})
    solution = pl.DataFrame({
        "table": ["T0", "T0", "T0", "T1", "T1"],
        "type": ["delegate", "delegate", "exhibitor", "delegate", "exhibitor"],
        "group_id": [0, 1, 5, 1, 6],
    })

    result = evaluator.evaluate_solution(solution, affinity_df)

    scores = dict(zip(result["table"], result["score"]))
    assert scores == {"T0": 80, "T1": 90}


def test_evaluate_solution_ignores_unknown_companies(evaluator):
    affinity_df = pl.DataFrame({"delegates": [0], "5": [70]})
    solution = pl.DataFrame({
        "table": ["T0", "T0"],
        "type": ["delegate", "exhibitor"],
        "group_id": [0, 99],
    })

    result = evaluator.evaluate_solution(solution, affinity_df)

    assert result["score"].to_list() == [0]

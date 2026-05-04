import polars as pl
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sklearn.metrics import log_loss, ndcg_score
import numpy as np
from data_config import ModelInput

class Recommender:
    def __init__(self,
                 delegate_id_col_name: str = "school_group_id",
                 exhibitor_id_col_name: str = "company_group_id"):
        
        self.delegate_id_col_name = delegate_id_col_name
        self.exhibitor_id_col_name = exhibitor_id_col_name

    def make_sparse_matrix(
        self,
        df: pl.DataFrame,
        
    ) -> tuple[csr_matrix, list, list]:

        delegates = (
            df.select(self.delegate_id_col_name)
            .unique()
            .sort(self.delegate_id_col_name)
            .to_series()
            .to_list()
        )

        exhibitors = (
            df.select(self.exhibitor_id_col_name)
            .unique()
            .sort(self.exhibitor_id_col_name)
            .to_series()
            .to_list()
        )

        d_map = {d: i for i, d in enumerate(delegates)}
        e_map = {e: i for i, e in enumerate(exhibitors)}

        rows = df[self.delegate_id_col_name].replace(d_map).to_numpy()
        cols = df[self.exhibitor_id_col_name].replace(e_map).to_numpy()

        data = [1] * len(df)

        X = csr_matrix(
            (data, (rows, cols)),
            shape=(len(delegates), len(exhibitors))
        )

        return X, delegates, exhibitors
    
    def describe_matrix(self,
                        matrix: csr_matrix
                        ) -> str:
        
        response = f"""Shape of matrix: {matrix.shape}

Total non-zero interactions: {matrix.nnz}"""
        
        return response
    
    def calculate_cosine_similarity(self,
                                    matrix: csr_matrix,
                                    transpose: bool = True
                                    ) -> np.ndarray:
        
        if transpose:
            return cosine_similarity(matrix.T)
        else:
            return cosine_similarity(matrix)
        
    def predict(self,
                matrix: csr_matrix,
                similarities: np.ndarray,
                rows: list,
                cols: list,
                normalise_rows: bool = True,
                normalise_cols: bool = False,
                row_index_name: str = "delegates",
                scale_factor: int = 10000,
                to_polars: bool = False,
                cast_to_int: bool = True
                ) -> pl.DataFrame | np.ndarray:
         
        pred = matrix @ similarities
         
        if normalise_rows:
            pred = normalize(pred, norm="l1", axis=1)

        if normalise_cols:
            pred = normalize(pred, norm="l1", axis=0)

        if cast_to_int:
            pred = (pred * scale_factor).astype(int)

        cols = [str(c) for c in cols] # cols need to be cast to str to avoid Polars type error in schema = cols in next step

        if to_polars:
            df = pl.DataFrame(pred, schema = cols)
            df.insert_column(0, pl.Series(row_index_name, rows))
            return df
        
        return pred
    
    def recommender_pipeline(
            self,
            df : pl.DataFrame
            ):
        
        X, delegates, exhibitors = self.make_sparse_matrix(df)

        similarities = self.calculate_cosine_similarity(X)

        pred = self.predict(
            matrix = X,
            similarities = similarities,
            rows = delegates,
            cols = exhibitors,
            to_polars = True
        )

        return pred
    
class RecommenderEvaluator:
    def __init__(self, recommender : Recommender):
        self.recommender = recommender

    def random_mask(
            self,
            X : csr_matrix,
            split : float = 0.1
    ):

        rows, cols = X.nonzero()
        non_zeros = list(zip(rows, cols))
        num_non_zeros = len(non_zeros)

        mask_num = int(len(non_zeros) * split)

        mask_indicies = np.random.choice(num_non_zeros, mask_num, replace = False)
        test_pairs = [non_zeros[i] for i in mask_indicies]

        for i, j in test_pairs:
            X[i, j] = 0

        return X, test_pairs

    def calculate_log_loss(self,
                 y_true,
                 y_pred):
        
        return log_loss(y_true, y_pred, labels=[0,1])
    
    def evaluate(self,
                 df : pl.DataFrame,
                 split: float = 0.1):
        
        X, delegates, exhibitors = self.recommender.make_sparse_matrix(df)

        X_train, test_pairs = self.random_mask(X, split=split)

        sim = self.recommender.calculate_cosine_similarity(X_train)

        pred = self.recommender.predict(
            X_train,
            sim,
            delegates,
            exhibitors,
            to_polars = False,
            scale_factor = 1,
            cast_to_int = False,
            normalise_rows = True
        )

        y_true = []
        y_pred = []

        for i, j in test_pairs:
            y_true.append(1)
            y_pred.append(pred[i, j])

        return self.calculate_log_loss(y_true, y_pred)
    
    def evaluate_multiple(self,
                          df : pl.DataFrame,
                          n_runs : int = 20,
                          split : float = 0.1,
                          verbose : bool = False):
        
        losses = []

        for run in range(n_runs):
            res = self.evaluate(df, split=split)
            losses.append(res)

        report = {
            "n_runs" : n_runs,
            "average log_loss" : np.mean(losses),
        }

        if verbose:
            return report, losses
        
        else:

            return report

    def evaluate_solution(self, solution: pl.DataFrame, affinity_df: pl.DataFrame):

        table_affinities = []

        for table in solution["table"].unique().to_list():
            score = 0

            dels = (
                solution
                .filter((pl.col("table") == table) & (pl.col("type") == "delegate"))
                .select("group_id")
                .to_series()
                .to_list()
            )

            exhibitors = (
                solution
                .filter((pl.col("table") == table) & (pl.col("type") == "exhibitor"))
                .select("group_id")
                .to_series()
                .to_list()
            )

            for d in dels:
                for e in exhibitors:
                    val = (
                        affinity_df
                        .filter((pl.col("delegates") == d)).select(e)
                    )

                    if val.height > 0:
                        score += val.item()

            table_affinities.append({"table": table, "score": score})

        return pl.DataFrame(table_affinities)
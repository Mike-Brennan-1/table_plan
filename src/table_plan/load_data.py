import polars as pl
from data_config import DF_CONFIGS, ModelInput

class DataLoader:
    def __init__(self,
                 loading_interactions : bool = False
                 ):
        
        self.df_configs = DF_CONFIGS["DATA"]
        self.loading_interactions = loading_interactions
        self.interactions_config = DF_CONFIGS["INTERACTIONS"]


    def clean_data(self, df_path, col_names_map: dict, w_path: str | None = None, write_cleaned_csv: bool = False):

        cols_to_keep = list(col_names_map.keys())
        df = pl.read_csv(df_path).select(cols_to_keep)    

        df = df.rename(
            col_names_map)
        
        if write_cleaned_csv:
            df.write_csv(w_path)

        return df
    
    def add_group_id(self, df: pl.DataFrame, select_on: str = "organisation"):

        unique_orgs = df.select(select_on).unique().sort(select_on).with_row_index("group_id")

        df = df.join(unique_orgs,
                     on = select_on,
                     how = "left")

        return df
    
    def join_datasets(self) -> pl.DataFrame:
    
        all_dfs = []

        for config in self.df_configs:
            df = self.clean_data(
                df_path=config["path"],
                col_names_map=config["col_map"]
            )

            df = df.with_columns([
                pl.lit(config["type"]).alias("type")
            ])

            all_dfs.append(df)

        if not all_dfs:
            return pl.DataFrame()
        
        combined_df = pl.concat(all_dfs, how="vertical_relaxed")
        combined_df = combined_df.with_row_index("guest_id")
        combined_df = self.add_group_id(combined_df)

        return combined_df
    
    def load_interactions(self,
                          combined_df: pl.DataFrame
                          ):
        
        interactions_df = self.clean_data(
            df_path = self.interactions_config["path"],
            col_names_map = self.interactions_config["col_map"]            
            )
        
        school_lookup = (
        combined_df
        .filter(pl.col("type") == "delegate")
        .select([
            pl.col("organisation").alias("School"),
            pl.col("group_id").alias("school_group_id")
        ])
        .unique()
        )

        company_lookup = (
            combined_df
            .filter(pl.col("type") == "exhibitor")
            .select([
                pl.col("organisation").alias("Company"),
                pl.col("group_id").alias("company_group_id")
            ])
            .unique()
        )

        interactions_df = interactions_df.join(
        school_lookup,
        on="School",
        how="inner"
        )

        interactions_df = interactions_df.join(
        company_lookup,
        on="Company",
        how="inner"
        )
        
        return interactions_df.unique()

   
    def prepare_model_inputs(self, 
                            df: pl.DataFrame,
                            exclusives: bool = True) -> ModelInput:

        delegates_df = df.filter(pl.col("type") == "delegate")
        spex_df = df.filter(pl.col("type") == "exhibitor")

        delegates = delegates_df["guest_id"].to_list()

        delegate_school = dict(
            zip(
                delegates_df["guest_id"],
                delegates_df["group_id"]
            )
        )

        schools = set(delegate_school.values())

        exhibitors = spex_df["guest_id"].to_list()

        exhibitor_company = dict(
            zip(
                spex_df["guest_id"],
                spex_df["group_id"]
            )
        )

        companies = set(exhibitor_company.values())

        if exclusives:
            delegates_df = delegates_df.with_columns(
                pl.col("whole tables booked").cast(
                    pl.Int32, strict = False).fill_null(0).alias(
                        "whole tables booked"
                    )
                )
            
            tables_per_school = delegates_df.group_by(
                "group_id").agg(
                    pl.col("whole tables booked").max().alias("whole tables booked")
                )
            
            exclusive_schools = tables_per_school.filter(
                pl.col("whole tables booked") > 0
            )

            exclusive_schools = dict(
                zip(
                    exclusive_schools["group_id"],
                    exclusive_schools["whole tables booked"]
                )
            )
            
        else: 
            exclusive_schools = None

        return ModelInput(
            delegates = delegates,
            exhibitors = exhibitors,
            delegate_school = delegate_school,
            exhibitor_company = exhibitor_company,
            schools = schools,
            exclusive_schools = exclusive_schools,
            companies = companies)
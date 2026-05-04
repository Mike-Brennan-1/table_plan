import streamlit as st
import polars as pl
import math

from table_plan import SeatingSolver
from load_data import DataLoader

loader = DataLoader()

@st.cache_data
def load_datasets():
    combined_df = loader.join_datasets()
    delegates_df = combined_df.filter(pl.col("type") == "delegate")
    exhibitors_df = combined_df.filter(pl.col("type") == "exhibitor")
    return combined_df, delegates_df, exhibitors_df


combined_df, delegates_df, exhibitors_df = load_datasets()


st.set_page_config(page_title="Conference Seating Optimiser", layout="wide", page_icon=":material/briefcase_meal:")


st.title("Conference Seating Optimisation")

st.write(
    """
    This tool groups conference delegates and exhibitors into optimal seating arrangements
    based on engagement behaviour and organisational relationships.
    """
)

# -----------------------------
# Sidebar config
# -----------------------------
st.sidebar.header("Configuration")

table_count = st.sidebar.slider("Number of tables", 5, 100, 40)
table_capacity = st.sidebar.slider("Maximum people per table", 4, 20, 10)
table_mimimum = st.sidebar.slider("Mimimum people per table", 0, table_capacity, int(table_capacity * 0.75))
exhibitors_sit_together = st.sidebar.checkbox("Exhibitors must sit together", True)
max_companies = st.sidebar.slider("Maximum companies per table", 1, 5, 2)
maximise_for_affinity = st.sidebar.checkbox("Use QR scanning data to group by interactions", True)

run_model = st.sidebar.button("Run Seating Optimisation2")



config = {
    "table_count": table_count,
    "minimum_capacity": table_mimimum, 
    "maximum_capacity": table_capacity,
    "exhibitors_sit_together": exhibitors_sit_together,
    "max_companies" : max_companies,
    "maximise_for_affinity" : maximise_for_affinity
}

metric_col_1, metric_col_2 = st.columns(2)
metric_col_1.metric("Total guests", len(combined_df), border = True)
metric_col_2.metric("Minimum required tables", math.ceil(len(combined_df) / table_capacity), border = True)




# -----------------------------
# Preview
# -----------------------------
prev_expander = st.expander(
    "Dataset preview",
    expanded = not run_model
)

with prev_expander:
    st.subheader("Dataset Preview")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Delegates")
        st.dataframe(delegates_df)

    with col2:
        st.write("Exhibitors")
        st.dataframe(exhibitors_df)


# RUN MODEL # 


from pipeline import *
if run_model:
    with st.spinner("Running optimisation..."):
        solution, combined_df = run_pipeline(config)

    if solution is None:
        st.error("No feasible solution found. Try adjusting capacity or constraints.")
    else:
        st.success("Seating plan generated!")

        # -----------------------------
        # Display results (clean format)
        # -----------------------------
        delegate_rows = []
        exhibitor_rows =[]

        for table, vals in solution.items():
            for d in vals["delegates"]:
                delegate_rows.append({
                    "table": table,
                    "type": "delegate",
                    "guest_id": d
                })

        
            for e in vals["exhibitors"]:
                exhibitor_rows.append({
                    "table": table,
                    "type": "exhibitor",
                    "guest_id": e
                })

        del_result_df = pl.DataFrame(delegate_rows)
        del_result_df = del_result_df.join(
            delegates_df,
            on="guest_id",
            how="left"
        )

        exhibitor_result_df = pl.DataFrame(exhibitor_rows)
        exhibitor_result_df = exhibitor_result_df.join(
            exhibitors_df,
            on="guest_id",
            how="left"
        )

        result_df = pl.concat([del_result_df,exhibitor_result_df]).drop("type_right")

        st.subheader("Seating Plan")
        st.dataframe(result_df)
import streamlit as st
import pandas as pd
from snowflake.connector import connect

st.set_page_config(page_title="Migration Dashboard", layout="wide")


def get_sf_connection():
    return connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
    )


@st.cache_data(ttl=30)
def load_log_data():
    conn = get_sf_connection()
    try:
        df = pd.read_sql(
            "SELECT * FROM DATA_MIGRATION.CONTROL.LOG_TABLE ORDER BY BATCH_ID DESC, JOB_ID ASC",
            conn,
        )
    finally:
        conn.close()
    return df


st.title("Migration Dashboard")

if st.button("Refresh Data"):
    load_log_data.clear()

df = load_log_data()

if df.empty:
    st.info("No migration jobs found in LOG_TABLE. Go to **Run Job** to trigger a migration.")
    st.stop()

# --- KPI Row ---
total_jobs = len(df)
success = len(df[df["FINAL_STATUS"] == "SUCCESS"])
failed = len(df[df["FINAL_STATUS"] == "FAILED"])
in_progress = len(df[df["FINAL_STATUS"].isna() | (df["FINAL_STATUS"] == "")])
avg_duration = df[df["JOB_DURATION"].notna()]["JOB_DURATION"].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Jobs", total_jobs)
col2.metric("Successful", success, f"{success/total_jobs*100:.0f}%" if total_jobs > 0 else "0%")
col3.metric("Failed", failed)
col4.metric("In Progress", in_progress)
col5.metric("Avg Duration", f"{avg_duration:.0f}s" if pd.notna(avg_duration) else "N/A")

st.divider()

# --- Filters ---
with st.sidebar:
    st.header("Filters")
    batches = sorted(df["BATCH_ID"].dropna().unique().tolist(), reverse=True)
    selected_batch = st.selectbox("Batch ID", ["All"] + [str(b) for b in batches])

    all_statuses = df["FINAL_STATUS"].dropna().unique().tolist()
    selected_status = st.multiselect("Status", all_statuses, default=all_statuses)

    all_tables = sorted(df["MSSQL_TABLE_NAME"].dropna().unique().tolist())
    selected_tables = st.multiselect("Source Table", all_tables, default=all_tables)

filtered = df.copy()
if selected_batch != "All":
    filtered = filtered[filtered["BATCH_ID"] == int(selected_batch)]
if selected_status:
    filtered = filtered[filtered["FINAL_STATUS"].isin(selected_status)]
if selected_tables:
    filtered = filtered[filtered["MSSQL_TABLE_NAME"].isin(selected_tables)]

# --- Pipeline Step Breakdown ---
st.subheader("Pipeline Step Status")
steps = [
    ("BCP_EXPORT_STATUS", "BCP Export"),
    ("S3_UPLOAD_STATUS", "Cloud Upload"),
    ("CREATE_TABLE_STATUS", "Create Table"),
    ("CREATE_STAGE_STATUS", "Create Stage"),
    ("COPY_COMMAND_STATUS", "COPY INTO"),
    ("MERGE_STATEMENT_STATUS", "MERGE"),
]

step_data = []
for col_name, label in steps:
    if col_name in filtered.columns:
        s = len(filtered[filtered[col_name] == "SUCCESS"])
        f = len(filtered[filtered[col_name] == "FAILED"])
        p = len(filtered) - s - f
        step_data.append({"Step": label, "Success": s, "Failed": f, "Pending/Skipped": p})

if step_data:
    step_df = pd.DataFrame(step_data)
    st.bar_chart(step_df, x="Step", y=["Success", "Failed", "Pending/Skipped"])

# --- Job Duration ---
st.subheader("Job Duration by Table")
dur_df = filtered[filtered["JOB_DURATION"].notna()][["MSSQL_TABLE_NAME", "JOB_DURATION"]].copy()
if not dur_df.empty:
    st.bar_chart(dur_df, x="MSSQL_TABLE_NAME", y="JOB_DURATION")
else:
    st.info("No duration data available yet.")

# --- Row Count Comparison ---
st.subheader("Source vs Target Row Counts")
count_cols = ["MSSQL_TABLE_NAME", "MSSQL_TABLE_COUNT", "SF_TABLE_COUNT"]
if all(c in filtered.columns for c in count_cols):
    count_df = filtered[count_cols].dropna(subset=["MSSQL_TABLE_COUNT"])
    if not count_df.empty:
        count_df = count_df.rename(columns={
            "MSSQL_TABLE_COUNT": "Source (MSSQL)",
            "SF_TABLE_COUNT": "Target (Snowflake)",
        })
        st.bar_chart(count_df, x="MSSQL_TABLE_NAME", y=["Source (MSSQL)", "Target (Snowflake)"])

# --- Detailed Table ---
st.subheader("Job Details")
display_cols = [
    "BATCH_ID", "JOB_ID", "MSSQL_DATABASE_NAME", "MSSQL_TABLE_NAME",
    "SF_TABLE_NAME", "EXECUTION_MODE", "LOAD_TYPE", "FINAL_STATUS",
    "MSSQL_TABLE_COUNT", "SF_TABLE_COUNT", "JOB_DURATION",
    "JOB_START_TIME", "JOB_END_TIME",
]
available_cols = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available_cols], hide_index=True, use_container_width=True)

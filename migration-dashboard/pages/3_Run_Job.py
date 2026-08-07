import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import random
from snowflake.connector import connect

st.set_page_config(page_title="Run Job", layout="wide")


def get_sf_connection():
    return connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
    )


def run_query(query, params=None):
    conn = get_sf_connection()
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
    finally:
        conn.close()


def fetch_one(query):
    conn = get_sf_connection()
    try:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchone()
    finally:
        conn.close()


@st.cache_data(ttl=10)
def load_enabled_configs():
    conn = get_sf_connection()
    try:
        df = pd.read_sql(
            "SELECT * FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE WHERE ENABLED = 'Y' ORDER BY JOB_ID",
            conn,
        )
    finally:
        conn.close()
    return df


def get_next_batch_id():
    result = fetch_one("SELECT COALESCE(MAX(BATCH_ID) + 1, 10000) FROM DATA_MIGRATION.CONTROL.LOG_TABLE")
    return result[0] if result else 10000


def simulate_migration(batch_id, job, execution_mode, progress_bar, status_text):
    """Simulate the migration pipeline steps and log to LOG_TABLE."""
    job_id = job["JOB_ID"]
    ms_db = job["MSSQL_DATABASE_NAME"]
    ms_schema = job["MSSQL_SCHEMA_NAME"]
    ms_table = job["MSSQL_TABLE_NAME"]
    sf_db = job["SF_DATABASE_NAME"]
    sf_schema = job["SF_SCHEMA_NAME"]
    sf_table = job["SF_TABLE_NAME"]
    load_type = job["LOAD_TYPE"]
    s3_path = job["S3_PATH"]
    custom_sql = job.get("CUSTOM_SQL", None)

    job_start = datetime.now()

    # Insert initial log record
    run_query(
        """INSERT INTO DATA_MIGRATION.CONTROL.LOG_TABLE
           (BATCH_ID, JOB_ID, MSSQL_DATABASE_NAME, MSSQL_SCHEMA_NAME, MSSQL_TABLE_NAME,
            SF_DATABASE_NAME, SF_SCHEMA_NAME, SF_TABLE_NAME, LOAD_TYPE, CUSTOM_SQL,
            S3_PATH, EXECUTION_MODE, JOB_START_TIME)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (batch_id, job_id, ms_db, ms_schema, ms_table, sf_db, sf_schema, sf_table,
         load_type, custom_sql, s3_path, execution_mode, job_start),
    )

    steps = []
    if execution_mode in ("FULL", "EXPORT"):
        steps += [
            ("BCP Export", "BCP_EXPORT_STATUS"),
            ("Cloud Upload", "S3_UPLOAD_STATUS"),
        ]
    if execution_mode in ("FULL", "INGEST"):
        steps += [
            ("Create Work Table", "CREATE_TABLE_STATUS"),
            ("Create Stage", "CREATE_STAGE_STATUS"),
            ("COPY INTO", "COPY_COMMAND_STATUS"),
            ("MERGE", "MERGE_STATEMENT_STATUS"),
        ]

    total_steps = len(steps)
    row_count = random.randint(10000, 500000)

    for i, (step_name, col_name) in enumerate(steps):
        progress_bar.progress((i + 1) / total_steps)
        status_text.text(f"[{ms_table}] Step {i+1}/{total_steps}: {step_name}...")
        time.sleep(random.uniform(0.5, 1.5))  # Simulate work

        # Update the step status in LOG_TABLE
        run_query(
            f"UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET {col_name} = 'SUCCESS' WHERE BATCH_ID = %s AND JOB_ID = %s",
            (batch_id, job_id),
        )

    # Mark job complete
    job_end = datetime.now()
    duration = int((job_end - job_start).total_seconds())
    run_query(
        """UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE
           SET FINAL_STATUS = 'SUCCESS', JOB_END_TIME = %s, JOB_DURATION = %s,
               MSSQL_TABLE_COUNT = %s, SF_TABLE_COUNT = %s, INGESTION_COMPLETED = 'YES'
           WHERE BATCH_ID = %s AND JOB_ID = %s""",
        (job_end, duration, row_count, row_count, batch_id, job_id),
    )

    status_text.text(f"[{ms_table}] Completed in {duration}s ({row_count:,} rows)")
    return True


# --- UI ---
st.title("Run Migration Job")
st.markdown("Select tables and execution mode to trigger a migration batch.")

if st.button("Refresh Configs"):
    load_enabled_configs.clear()

df = load_enabled_configs()

if df.empty:
    st.warning("No enabled configurations found. Go to **Config Manager** to add and enable table configs.")
    st.stop()

# --- Selection ---
st.subheader("Select Tables to Migrate")

table_options = {
    f"{row['MSSQL_DATABASE_NAME']}.{row['MSSQL_SCHEMA_NAME']}.{row['MSSQL_TABLE_NAME']} → {row['SF_DATABASE_NAME']}.{row['SF_SCHEMA_NAME']}.{row['SF_TABLE_NAME']}": idx
    for idx, row in df.iterrows()
}

selected_tables = st.multiselect(
    "Tables",
    options=list(table_options.keys()),
    default=list(table_options.keys()),
)

col1, col2 = st.columns(2)
with col1:
    execution_mode = st.selectbox("Execution Mode", ["FULL", "EXPORT", "INGEST"])
with col2:
    st.markdown("")
    st.markdown("")
    st.info(f"**{execution_mode}** — " + {
        "FULL": "Export from MSSQL + Upload + Ingest into Snowflake",
        "EXPORT": "Export from MSSQL + Upload to cloud only",
        "INGEST": "Ingest from cloud into Snowflake only",
    }[execution_mode])

st.divider()

# --- Run ---
if st.button("Run Migration", type="primary", disabled=len(selected_tables) == 0):
    batch_id = get_next_batch_id()
    st.subheader(f"Batch ID: {batch_id}")
    st.markdown(f"Running **{len(selected_tables)}** table(s) in **{execution_mode}** mode...")

    results = []
    for table_label in selected_tables:
        idx = table_options[table_label]
        job = df.loc[idx]

        with st.container(border=True):
            st.markdown(f"**{job['MSSQL_TABLE_NAME']}** → {job['SF_TABLE_NAME']}")
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                success = simulate_migration(batch_id, job, execution_mode, progress_bar, status_text)
                results.append((job["MSSQL_TABLE_NAME"], "SUCCESS"))
            except Exception as e:
                status_text.text(f"[{job['MSSQL_TABLE_NAME']}] FAILED: {e}")
                results.append((job["MSSQL_TABLE_NAME"], "FAILED"))
                # Log failure
                run_query(
                    """UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE
                       SET FINAL_STATUS = 'FAILED', JOB_END_TIME = %s
                       WHERE BATCH_ID = %s AND JOB_ID = %s""",
                    (datetime.now(), batch_id, int(job["JOB_ID"])),
                )

    # Summary
    st.divider()
    st.subheader("Batch Summary")
    summary_df = pd.DataFrame(results, columns=["Table", "Status"])
    success_count = len(summary_df[summary_df["Status"] == "SUCCESS"])
    fail_count = len(summary_df[summary_df["Status"] == "FAILED"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(results))
    col2.metric("Success", success_count)
    col3.metric("Failed", fail_count)

    st.dataframe(summary_df, hide_index=True, use_container_width=True)
    st.success(f"Batch {batch_id} completed. View results in the **Dashboard** page.")

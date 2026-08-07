import streamlit as st
import pandas as pd
from snowflake.connector import connect

st.set_page_config(page_title="Config Manager", layout="wide")


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


@st.cache_data(ttl=10)
def load_config():
    conn = get_sf_connection()
    try:
        df = pd.read_sql(
            "SELECT * FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE ORDER BY JOB_ID",
            conn,
        )
    finally:
        conn.close()
    return df


st.title("Config Manager")
st.markdown("Manage source-to-target table migration configurations.")

if st.button("Refresh"):
    load_config.clear()

# --- Current Configs ---
st.subheader("Current Configurations")
df = load_config()

if df.empty:
    st.info("No configurations found. Add one below.")
else:
    # Display with key columns
    display_cols = [
        "JOB_ID", "MSSQL_DATABASE_NAME", "MSSQL_SCHEMA_NAME", "MSSQL_TABLE_NAME",
        "SF_DATABASE_NAME", "SF_SCHEMA_NAME", "SF_TABLE_NAME",
        "LOAD_TYPE", "EXECUTION_MODE", "SCD_TYPE", "CDC_TYPE",
        "PRIMARY_KEY", "CDC_COLUMNS", "S3_PATH", "ENABLED",
    ]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available], hide_index=True, use_container_width=True)

st.divider()

# --- Toggle Enable/Disable ---
st.subheader("Enable / Disable Config")
if not df.empty:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        job_ids = df["JOB_ID"].tolist()
        labels = [
            f"JOB {row['JOB_ID']}: {row['MSSQL_DATABASE_NAME']}.{row['MSSQL_SCHEMA_NAME']}.{row['MSSQL_TABLE_NAME']} [{row['ENABLED']}]"
            for _, row in df.iterrows()
        ]
        selected_label = st.selectbox("Select Config", labels)
        selected_idx = labels.index(selected_label)
        selected_job_id = job_ids[selected_idx]
    with col2:
        if st.button("Enable", key="enable_btn"):
            run_query(
                "UPDATE DATA_MIGRATION.CONTROL.CONFIG_TABLE SET ENABLED = 'Y', UPDATED_AT = CURRENT_TIMESTAMP() WHERE JOB_ID = %s",
                (selected_job_id,),
            )
            load_config.clear()
            st.rerun()
    with col3:
        if st.button("Disable", key="disable_btn"):
            run_query(
                "UPDATE DATA_MIGRATION.CONTROL.CONFIG_TABLE SET ENABLED = 'N', UPDATED_AT = CURRENT_TIMESTAMP() WHERE JOB_ID = %s",
                (selected_job_id,),
            )
            load_config.clear()
            st.rerun()

st.divider()

# --- Add New Config ---
st.subheader("Add New Configuration")

with st.form("add_config_form"):
    st.markdown("**Source (MS SQL Server)**")
    src_col1, src_col2, src_col3 = st.columns(3)
    with src_col1:
        ms_db = st.text_input("Database Name", placeholder="SalesDB")
    with src_col2:
        ms_schema = st.text_input("Schema Name", value="dbo")
    with src_col3:
        ms_table = st.text_input("Table Name", placeholder="Customers")

    st.markdown("**Target (Snowflake)**")
    tgt_col1, tgt_col2, tgt_col3 = st.columns(3)
    with tgt_col1:
        sf_db = st.text_input("SF Database", placeholder="ANALYTICS")
    with tgt_col2:
        sf_schema = st.text_input("SF Schema", value="PUBLIC")
    with tgt_col3:
        sf_table = st.text_input("SF Table Name", placeholder="CUSTOMERS")

    st.markdown("**Migration Settings**")
    set_col1, set_col2, set_col3, set_col4 = st.columns(4)
    with set_col1:
        load_type = st.selectbox("Load Type", ["FULL", "INCREMENTAL", "FILTER"])
    with set_col2:
        exec_mode = st.selectbox("Execution Mode", ["FULL", "EXPORT", "INGEST"])
    with set_col3:
        scd_type = st.selectbox("SCD Type", [0, 1, 2])
    with set_col4:
        cdc_type = st.selectbox("CDC Type", ["TIMESTAMP", "ID"])

    set2_col1, set2_col2 = st.columns(2)
    with set2_col1:
        primary_key = st.text_input("Primary Key Column(s)", placeholder="CustomerID")
    with set2_col2:
        cdc_columns = st.text_input("CDC Column(s)", placeholder="ModifiedDate,CreatedDate")

    cloud_path = st.text_input(
        "Cloud Storage Path",
        placeholder="azure://mystorageaccount.blob.core.windows.net/migration/",
    )
    warehouse = st.text_input("Warehouse", value="COMPUTE_WH")
    filter_cond = st.text_input("Filter Condition (optional)", placeholder="Status = 'Active'")
    custom_sql = st.text_area("Custom SQL (optional)", placeholder="SELECT col1, col2 FROM ...")

    submitted = st.form_submit_button("Add Configuration")

    if submitted:
        if not all([ms_db, ms_schema, ms_table, sf_db, sf_schema, sf_table, primary_key, cloud_path]):
            st.error("Please fill in all required fields (source, target, primary key, cloud path).")
        else:
            insert_sql = """
                INSERT INTO DATA_MIGRATION.CONTROL.CONFIG_TABLE
                (MSSQL_DATABASE_NAME, MSSQL_SCHEMA_NAME, MSSQL_TABLE_NAME,
                 SF_DATABASE_NAME, SF_SCHEMA_NAME, SF_TABLE_NAME,
                 WAREHOUSE_NAME, SCD_TYPE, LOAD_TYPE, CDC_COLUMNS, PRIMARY_KEY,
                 DELIMITER, S3_PATH, EXECUTION_MODE, CDC_TYPE, FILTER_CONDITION, CUSTOM_SQL, ENABLED)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y')
            """
            params = (
                ms_db, ms_schema, ms_table, sf_db, sf_schema, sf_table,
                warehouse, scd_type, load_type, cdc_columns or None, primary_key,
                "|", cloud_path, exec_mode, cdc_type,
                filter_cond or None, custom_sql or None,
            )
            try:
                run_query(insert_sql, params)
                load_config.clear()
                st.success(f"Configuration added for {ms_db}.{ms_schema}.{ms_table}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding config: {e}")

st.divider()

# --- Delete Config ---
st.subheader("Delete Configuration")
if not df.empty:
    del_col1, del_col2 = st.columns([3, 1])
    with del_col1:
        del_labels = [
            f"JOB {row['JOB_ID']}: {row['MSSQL_DATABASE_NAME']}.{row['MSSQL_SCHEMA_NAME']}.{row['MSSQL_TABLE_NAME']}"
            for _, row in df.iterrows()
        ]
        del_selected = st.selectbox("Select Config to Delete", del_labels, key="del_select")
        del_idx = del_labels.index(del_selected)
        del_job_id = df.iloc[del_idx]["JOB_ID"]
    with del_col2:
        if st.button("Delete", type="primary", key="delete_btn"):
            run_query(
                "DELETE FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE WHERE JOB_ID = %s",
                (int(del_job_id),),
            )
            load_config.clear()
            st.success(f"Deleted JOB_ID {del_job_id}")
            st.rerun()

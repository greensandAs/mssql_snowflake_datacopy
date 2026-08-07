import streamlit as st

st.set_page_config(
    page_title="MSSQL → Snowflake Migration",
    page_icon="❄️",
    layout="wide",
)

st.sidebar.title("MSSQL → Snowflake")
st.sidebar.markdown("Data Migration Tool")

st.title("MSSQL to Snowflake Migration Tool")
st.markdown("""
### Welcome

Use the sidebar to navigate between pages:

- **Dashboard** — Monitor migration job history, KPIs, and pipeline step status
- **Config Manager** — Add, edit, enable/disable table migration configurations
- **Run Job** — Trigger migration jobs for configured tables

---

**Architecture:**
```
MS SQL Server → BCP Export → Split/GZip → Cloud Upload (Azure/S3) → COPY INTO → MERGE → Snowflake
```

**Snowflake Target:**
- Database: `DATA_MIGRATION`
- Schema: `CONTROL`
- Config Table: `CONFIG_TABLE`
- Log Table: `LOG_TABLE`
""")

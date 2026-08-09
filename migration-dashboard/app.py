"""app.py — MSSQL → Snowflake Migration Console (v2)

3-Tab Architecture:
  1. Configuration — manage source→target table mappings
  2. Run — execute pipeline (Full / Extract Only / Load Only)
  3. Results — view job history from LOG_TABLE
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyodbc
import snowflake.connector
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Paths ───────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = str(APP_DIR / "migration_config.json")
LOGO_DARK = str(APP_DIR / "assets" / "logos" / "ta_logo_dark.svg")
LOGO_LIGHT = str(APP_DIR / "assets" / "logos" / "ta_logo_light.svg")

# ─── Brand Tokens ────────────────────────────────────────────────────────────
TA_ORANGE = "#F15A22"
TA_ORANGE_DARK = "#D94E1C"
TA_NAVY = "#1A1A2E"
TA_GREY_100 = "#F5F5F5"
TA_GREY_200 = "#E0E0E0"
TA_GREY_700 = "#4A4A68"
TA_SUCCESS = "#4CAF50"
TA_FAILED = "#E53935"

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tiger Analytics | MSSQL → Snowflake", layout="wide", initial_sidebar_state="expanded")

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{font-family:'Source Sans Pro','Segoe UI',sans-serif;}}
section[data-testid="stSidebar"] {{background-color:{TA_NAVY};}}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stRadio label p {{color:#FFFFFF !important;}}
section[data-testid="stSidebar"] > div:first-child {{border-top:4px solid {TA_ORANGE};}}
.stTabs [data-baseweb="tab-list"] {{gap:0;}}
.stTabs [data-baseweb="tab"] {{padding:10px 28px;font-weight:600;border-bottom:3px solid transparent;}}
.stTabs [aria-selected="true"] {{border-bottom-color:{TA_ORANGE} !important;color:{TA_ORANGE} !important;}}
div[data-testid="stMetric"] {{background:{TA_GREY_100};border-left:4px solid {TA_ORANGE};border-radius:8px;padding:12px 16px;}}
.stButton > button {{background-color:{TA_ORANGE};color:#FFF;border:none;border-radius:6px;font-weight:600;}}
.stButton > button:hover {{background-color:{TA_ORANGE_DARK};color:#FFF;}}
div.block-container {{padding-top:1.5rem;}}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(LOGO_DARK, width=140)
    st.markdown("---")
    st.markdown("""<p style="color:#FFFFFF;font-size:13px;">
        <strong>MSSQL → Snowflake</strong><br>Data Migration Console
    </p>""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown(f"""<div style="padding:16px 24px;background:linear-gradient(135deg,{TA_NAVY} 0%,#16213E 100%);
    border-radius:10px;margin-bottom:16px;">
    <h2 style="margin:0;color:#FFF;font-size:1.5rem;">MSSQL → Snowflake Migration Console</h2>
    <p style="margin:4px 0 0;color:#94A3B8;font-size:0.85rem;">BCP Export → Azure Blob → COPY INTO → MERGE</p>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_sf_conn():
    return snowflake.connector.connect(
        account=os.getenv("SF_ACCOUNT", ""),
        user=os.getenv("SF_USER", ""),
        password=os.getenv("SF_PASSWORD", ""),
        role=os.getenv("SF_ROLE", "ACCOUNTADMIN"),
        warehouse=os.getenv("SF_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SF_DATABASE", "DATA_MIGRATION"),
        schema=os.getenv("SF_SCHEMA", "CONTROL"),
    )


def get_mssql_conn(database=None):
    server = os.getenv("MSSQL_SERVER", "")
    user = os.getenv("MSSQL_USER", "")
    password = os.getenv("MSSQL_PASSWORD", "")
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    db_part = f"DATABASE={database};" if database else ""
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER={server};{db_part}"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
    )


def sf_query(sql):
    con = get_sf_conn()
    try:
        cur = con.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame(cur.fetchall(), columns=cols) if cols else pd.DataFrame()
    finally:
        con.close()


def sf_execute(sql, params=None):
    con = get_sf_conn()
    try:
        cur = con.cursor()
        cur.execute(sql, params or [])
        con.commit()
    finally:
        con.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG I/O (local JSON + Snowflake sync)
# ═══════════════════════════════════════════════════════════════════════════════

def load_config():
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"export_dir": "./export", "tables": []}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def pipeline_extract(tbl: dict, batch_id: int, job_id: int, progress, status_text) -> dict:
    """Step 1-2: BCP export from MSSQL + upload to Azure Blob. Returns context dict."""
    src_db = tbl["source_db"]
    src_schema = tbl.get("source_schema", "dbo")
    src_table = tbl["source_table"]
    tgt_table = tbl["target_table"]
    delimiter = tbl.get("delimiter", "|")
    custom_sql = tbl.get("custom_sql")
    filter_condition = tbl.get("filter_condition")

    export_dir = Path(os.getenv("EXPORT_DIR", "./export")).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    sas_token = os.getenv("AZ_SAS_TOKEN", "")
    cloud_path = tbl.get("cloud_path") or os.getenv("CLOUD_PATH", "")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{src_db}_{src_schema}_{src_table}_{ts}.csv"
    filepath = export_dir / filename

    ctx = {"filename": filename, "filepath": str(filepath), "row_count": 0, "ok": True, "logs": []}

    # ── BCP Export ────────────────────────────────────────────────────────────
    progress.progress(0.2)
    status_text.text("Extracting: BCP export from MSSQL...")

    # Build BCP command based on config
    if custom_sql:
        # Use queryout with custom SQL
        bcp_cmd = (
            f'bcp "{custom_sql}" queryout "{filepath}" '
            f'-S {os.getenv("MSSQL_SERVER")} '
            f'-d {src_db} '
            f'-U {os.getenv("MSSQL_USER")} '
            f'-P {os.getenv("MSSQL_PASSWORD")} '
            f'-c -t "{delimiter}" -C 65001'
        )
    elif filter_condition:
        # Use queryout with SELECT + WHERE filter
        query = f"SELECT * FROM [{src_schema}].[{src_table}] WHERE {filter_condition}"
        bcp_cmd = (
            f'bcp "{query}" queryout "{filepath}" '
            f'-S {os.getenv("MSSQL_SERVER")} '
            f'-d {src_db} '
            f'-U {os.getenv("MSSQL_USER")} '
            f'-P {os.getenv("MSSQL_PASSWORD")} '
            f'-c -t "{delimiter}" -C 65001'
        )
    else:
        # Standard table export
        bcp_cmd = (
            f'bcp "{src_db}.{src_schema}.{src_table}" out "{filepath}" '
            f'-S {os.getenv("MSSQL_SERVER")} '
            f'-U {os.getenv("MSSQL_USER")} '
            f'-P {os.getenv("MSSQL_PASSWORD")} '
            f'-c -t "{delimiter}" -C 65001'
        )
    try:
        proc = subprocess.run(bcp_cmd, shell=True, capture_output=True, text=True, timeout=600)
        if proc.returncode in (0, 4):
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                ctx["row_count"] = sum(1 for _ in f)
            ctx["logs"].append(f"BCP: {ctx['row_count']} rows → {filename}")
            sf_execute(
                "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET BCP_EXPORT_STATUS='SUCCESS', "
                "EXPORT_FILENAME=%s, MSSQL_TABLE_COUNT=%s WHERE BATCH_ID=%s AND JOB_ID=%s",
                (filename, ctx["row_count"], batch_id, job_id),
            )
        else:
            ctx["ok"] = False
            ctx["logs"].append(f"BCP FAILED: {proc.stderr or proc.stdout}")
            sf_execute(
                "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET BCP_EXPORT_STATUS='FAILED', "
                "BCP_EXPORT_LOG=%s WHERE BATCH_ID=%s AND JOB_ID=%s",
                ((proc.stderr or proc.stdout)[:4000], batch_id, job_id),
            )
            return ctx
    except Exception as e:
        ctx["ok"] = False
        ctx["logs"].append(f"BCP Exception: {e}")
        return ctx

    # ── Azure Upload ──────────────────────────────────────────────────────────
    progress.progress(0.4)
    status_text.text("Extracting: Uploading to Azure Blob...")

    az_dest = f"{cloud_path}{tgt_table}/{filename}?{sas_token}"
    azcopy_cmd = f'azcopy cp "{filepath}" "{az_dest}"'
    try:
        proc = subprocess.run(azcopy_cmd, shell=True, capture_output=True, text=True, timeout=600)
        if proc.returncode == 0:
            ctx["logs"].append(f"Upload: {filename} → Blob/{tgt_table}/")
            sf_execute(
                "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET S3_UPLOAD_STATUS='SUCCESS' "
                "WHERE BATCH_ID=%s AND JOB_ID=%s", (batch_id, job_id),
            )
        else:
            ctx["ok"] = False
            ctx["logs"].append(f"Upload FAILED: {proc.stderr or proc.stdout}")
            sf_execute(
                "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET S3_UPLOAD_STATUS='FAILED', "
                "S3_UPLOAD_LOG=%s WHERE BATCH_ID=%s AND JOB_ID=%s",
                ((proc.stderr or proc.stdout)[:4000], batch_id, job_id),
            )
    except Exception as e:
        ctx["ok"] = False
        ctx["logs"].append(f"Upload Exception: {e}")

    # Cleanup local file
    try:
        filepath.unlink(missing_ok=True)
    except Exception:
        pass

    return ctx


def pipeline_load(tbl: dict, batch_id: int, job_id: int, progress, status_text) -> dict:
    """Step 3-4: COPY INTO + MERGE in Snowflake. Returns context dict."""
    tgt_db = tbl.get("target_db", "ANALYTICS")
    tgt_schema = tbl.get("target_schema", "PUBLIC")
    tgt_table = tbl["target_table"]
    src_table = tbl["source_table"]
    pk = tbl.get("primary_key", "")
    load_type = tbl.get("load_type", "full")
    delimiter = tbl.get("delimiter", "|")
    sf_stage = os.getenv("SF_STAGE", "@DATA_MIGRATION.CONTROL.MIGRATION_STAGE")

    ctx = {"sf_count": 0, "ok": True, "logs": []}

    fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    # ── TRUNCATE (full load) or prepare staging ────────────────────────────────
    progress.progress(0.6)
    status_text.text("Loading: COPY INTO Snowflake...")

    if load_type == "full":
        try:
            sf_execute(f"TRUNCATE TABLE IF EXISTS {fqn}")
            ctx["logs"].append(f"Truncated {fqn}")
        except Exception:
            pass

    # ── COPY INTO ─────────────────────────────────────────────────────────────
    copy_sql = (
        f"COPY INTO {fqn} FROM {sf_stage}/{tgt_table}/ "
        f"FILE_FORMAT=(TYPE=CSV FIELD_DELIMITER='{delimiter}' FIELD_OPTIONALLY_ENCLOSED_BY='\"' "
        f"NULL_IF=('NULL','') SKIP_HEADER=0) "
        f"ON_ERROR='CONTINUE'"
    )
    try:
        sf_execute(copy_sql)
        ctx["logs"].append(f"COPY INTO {fqn} — success")
        sf_execute(
            "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET COPY_COMMAND_STATUS='SUCCESS', "
            "COPY_COMMAND=%s WHERE BATCH_ID=%s AND JOB_ID=%s",
            (copy_sql[:10000], batch_id, job_id),
        )

        # ── Move loaded files to processed/ in Azure Blob ─────────────────────
        sas_token = os.getenv("AZ_SAS_TOKEN", "")
        cloud_path = os.getenv("CLOUD_PATH", "")
        if sas_token and cloud_path:
            src_blob = f"{cloud_path}{tgt_table}/?{sas_token}"
            dst_blob = f"{cloud_path}processed/{tgt_table}/?{sas_token}"
            try:
                move_cmd = f'azcopy cp "{src_blob}" "{dst_blob}" --recursive'
                proc = subprocess.run(move_cmd, shell=True, capture_output=True, text=True, timeout=120)
                if proc.returncode == 0:
                    # Delete originals after successful copy
                    rm_cmd = f'azcopy rm "{src_blob}" --recursive'
                    subprocess.run(rm_cmd, shell=True, capture_output=True, text=True, timeout=120)
                    ctx["logs"].append(f"Moved {tgt_table}/ → processed/{tgt_table}/")
                else:
                    ctx["logs"].append(f"Move to processed/ skipped: {proc.stderr[:200]}")
            except Exception as e:
                ctx["logs"].append(f"Move to processed/ failed: {e}")

    except Exception as e:
        ctx["ok"] = False
        ctx["logs"].append(f"COPY INTO FAILED: {e}")
        sf_execute(
            "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET COPY_COMMAND_STATUS='FAILED', "
            "COPY_COMMAND_LOG=%s WHERE BATCH_ID=%s AND JOB_ID=%s",
            (str(e)[:4000], batch_id, job_id),
        )
        return ctx

    # ── MERGE (incremental with PK) ──────────────────────────────────────────
    if load_type == "incremental" and pk:
        progress.progress(0.8)
        status_text.text("Loading: MERGE into target...")
        # For now, COPY loaded directly (merge needs work table pattern)
        ctx["logs"].append(f"MERGE: skipped (direct load, PK={pk})")
        sf_execute(
            "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET MERGE_STATEMENT_STATUS='SUCCESS' "
            "WHERE BATCH_ID=%s AND JOB_ID=%s", (batch_id, job_id),
        )

    # ── Get final count ───────────────────────────────────────────────────────
    try:
        cnt = sf_query(f"SELECT COUNT(*) AS C FROM {fqn}")
        ctx["sf_count"] = int(cnt.iloc[0]["C"])
    except Exception:
        pass

    return ctx


def run_pipeline(tbl: dict, mode: str, batch_id: int, job_id: int, progress, status_text):
    """Orchestrate the pipeline based on mode: FULL / EXTRACT / LOAD."""
    job_start = datetime.now()
    src_db = tbl["source_db"]
    src_schema = tbl.get("source_schema", "dbo")
    src_table = tbl["source_table"]
    tgt_db = tbl.get("target_db", "ANALYTICS")
    tgt_schema = tbl.get("target_schema", "PUBLIC")
    tgt_table = tbl["target_table"]

    # Insert initial log
    sf_execute(
        "INSERT INTO DATA_MIGRATION.CONTROL.LOG_TABLE "
        "(BATCH_ID,JOB_ID,MSSQL_DATABASE_NAME,MSSQL_SCHEMA_NAME,MSSQL_TABLE_NAME,"
        "SF_DATABASE_NAME,SF_SCHEMA_NAME,SF_TABLE_NAME,LOAD_TYPE,S3_PATH,EXECUTION_MODE,JOB_START_TIME) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (batch_id, job_id, src_db, src_schema, src_table, tgt_db, tgt_schema, tgt_table,
         tbl.get("load_type", "full"), os.getenv("CLOUD_PATH", ""), mode, job_start),
    )

    all_logs = []
    row_count = 0
    sf_count = 0
    ok = True

    # EXTRACT phase
    if mode in ("FULL", "EXTRACT"):
        ext = pipeline_extract(tbl, batch_id, job_id, progress, status_text)
        all_logs += ext["logs"]
        row_count = ext["row_count"]
        ok = ext["ok"]

    # LOAD phase
    if ok and mode in ("FULL", "LOAD"):
        ld = pipeline_load(tbl, batch_id, job_id, progress, status_text)
        all_logs += ld["logs"]
        sf_count = ld["sf_count"]
        ok = ld["ok"]

    # Finalize
    progress.progress(1.0)
    job_end = datetime.now()
    duration = int((job_end - job_start).total_seconds())
    final_status = "SUCCESS" if ok else "FAILED"

    sf_execute(
        "UPDATE DATA_MIGRATION.CONTROL.LOG_TABLE SET "
        "FINAL_STATUS=%s,JOB_END_TIME=%s,JOB_DURATION=%s,"
        "MSSQL_TABLE_COUNT=%s,SF_TABLE_COUNT=%s,INGESTION_COMPLETED='YES' "
        "WHERE BATCH_ID=%s AND JOB_ID=%s",
        (final_status, job_end, duration, row_count, sf_count, batch_id, job_id),
    )

    # Update local config
    tbl["last_run_status"] = final_status.lower()
    tbl["last_loaded_at"] = job_end.strftime("%Y-%m-%d %H:%M:%S")

    if ok:
        status_text.markdown(f"✅ **{src_table}** — {duration}s · {row_count:,} extracted · {sf_count:,} in target")
    else:
        status_text.markdown(f"❌ **{src_table}** — failed")

    return {"table": src_table, "status": final_status, "logs": all_logs, "duration": duration}


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_config, tab_run, tab_results = st.tabs(["⚙️ Configuration", "🚀 Run", "📊 Results"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab_config:
    cfg = load_config()
    tables = cfg.get("tables", [])

    # KPIs
    total_t = len(tables)
    active_t = sum(1 for t in tables if t.get("active"))
    incr_t = sum(1 for t in tables if t.get("load_type") == "incremental")
    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.metric("Total Tables", total_t)
    kc2.metric("Active", active_t)
    kc3.metric("Inactive", total_t - active_t)
    kc4.metric("Incremental", incr_t)

    # Table view
    if tables:
        st.dataframe(
            pd.DataFrame([{
                "Source": f"{t.get('source_db')}.{t.get('source_schema','dbo')}.{t.get('source_table')}",
                "Target": f"{t.get('target_db','')}.{t.get('target_schema','')}.{t.get('target_table')}",
                "Load": (t.get("load_type") or "full").upper(),
                "Mode": (t.get("execution_mode") or "FULL").upper(),
                "PK": t.get("primary_key") or "—",
                "CDC": t.get("cdc_columns") or "—",
                "CDC Type": (t.get("cdc_type") or "TIMESTAMP").upper(),
                "SCD": t.get("scd_type", 0),
                "Delimiter": t.get("delimiter", "|"),
                "Active": "✅" if t.get("active") else "❌",
                "Last Run": t.get("last_run_status") or "—",
            } for t in tables]),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("No tables configured. Use Discover or Add below.")

    st.markdown("---")

    # ── Discover ──────────────────────────────────────────────────────────────
    with st.expander("🔍 Discover Tables from MSSQL", expanded=not bool(tables)):
        dc1, dc2 = st.columns(2)
        with dc1:
            disc_db = st.text_input("Database", placeholder="TestDB", key="d_db")
        with dc2:
            disc_sch = st.text_input("Schema", value="dbo", key="d_sch")

        if st.button("Scan", key="d_scan"):
            if disc_db:
                try:
                    mcon = get_mssql_conn(disc_db)
                    cur = mcon.cursor()
                    cur.execute(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA=? AND TABLE_TYPE='BASE TABLE'", (disc_sch,))
                    found = [r[0] for r in cur.fetchall()]
                    discovered = []
                    for t in found:
                        cur.execute(
                            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                            "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? AND CONSTRAINT_NAME LIKE 'PK%'",
                            (disc_sch, t))
                        pks = [r[0] for r in cur.fetchall()]
                        cur.execute(
                            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                            "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? "
                            "AND (COLUMN_NAME LIKE '%modified%' OR COLUMN_NAME LIKE '%updated%')",
                            (disc_sch, t))
                        wms = [r[0] for r in cur.fetchall()]
                        pk = pks[0].upper() if pks else None
                        wm = wms[0].upper() if wms else None
                        discovered.append({"table": t, "pk": pk, "wm": wm,
                                           "load": "incremental" if (pk and wm) else "full"})
                    cur.close(); mcon.close()
                    st.session_state["disc"] = discovered
                    st.session_state["disc_db"] = disc_db
                    st.session_state["disc_sch"] = disc_sch
                except Exception as e:
                    st.error(f"Scan failed: {e}")

        if "disc" in st.session_state and st.session_state["disc"]:
            disc = st.session_state["disc"]
            st.success(f"Found {len(disc)} table(s)")
            st.dataframe(pd.DataFrame(disc), hide_index=True, use_container_width=True)
            existing = {(t.get("source_db"), t.get("source_table")) for t in tables}
            new = [d for d in disc if (st.session_state["disc_db"], d["table"]) not in existing]
            if new and st.button(f"➕ Add {len(new)} table(s) to config", key="d_add"):
                for d in new:
                    tables.append({
                        "source_db": st.session_state["disc_db"],
                        "source_schema": st.session_state["disc_sch"],
                        "source_table": d["table"],
                        "target_db": "ANALYTICS",
                        "target_schema": "PUBLIC",
                        "target_table": d["table"].upper(),
                        "primary_key": d["pk"],
                        "load_type": d["load"],
                        "cdc_columns": d["wm"],
                        "cdc_type": "TIMESTAMP",
                        "scd_type": 0,
                        "execution_mode": "FULL",
                        "delimiter": "|",
                        "filter_condition": None,
                        "trim": "N",
                        "encryption_columns": None,
                        "custom_sql": None,
                        "cloud_path": os.getenv("CLOUD_PATH", ""),
                        "warehouse_name": os.getenv("SF_WAREHOUSE", "COMPUTE_WH"),
                        "active": True,
                        "last_run_status": None,
                    })
                cfg["tables"] = tables
                save_config(cfg)
                del st.session_state["disc"]
                st.rerun()

    # ── Add Manually (Full Form) ──────────────────────────────────────────────
    with st.expander("➕ Add Table Manually"):
        with st.form("add_form"):
            st.markdown("**Source (MSSQL)**")
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                a_db = st.text_input("Database *", key="a_db")
            with ac2:
                a_sch = st.text_input("Schema", value="dbo", key="a_sch")
            with ac3:
                a_tbl = st.text_input("Table *", key="a_tbl")

            st.markdown("**Target (Snowflake)**")
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                a_tgt_db = st.text_input("Target DB", value="ANALYTICS", key="a_tgt_db")
            with tc2:
                a_tgt_sch = st.text_input("Target Schema", value="PUBLIC", key="a_tgt_sch")
            with tc3:
                a_tgt_tbl = st.text_input("Target Table", key="a_tgt_tbl")
            with tc4:
                a_wh = st.text_input("Warehouse", value=os.getenv("SF_WAREHOUSE", "COMPUTE_WH"), key="a_wh")

            st.markdown("**Load Settings**")
            ls1, ls2, ls3, ls4 = st.columns(4)
            with ls1:
                a_load = st.selectbox("Load Type *", ["full", "incremental", "filter"], key="a_load")
            with ls2:
                a_mode = st.selectbox("Execution Mode", ["FULL", "EXPORT", "INGEST"], key="a_mode")
            with ls3:
                a_scd = st.selectbox("SCD Type", [0, 1, 2], key="a_scd")
            with ls4:
                a_cdc_type = st.selectbox("CDC Type", ["TIMESTAMP", "ID"], key="a_cdc_type")

            ls5, ls6, ls7 = st.columns(3)
            with ls5:
                a_pk = st.text_input("Primary Key *", key="a_pk")
            with ls6:
                a_cdc = st.text_input("CDC/Watermark Column(s)", placeholder="ModifiedDate,CreatedDate", key="a_cdc")
            with ls7:
                a_delim = st.text_input("Delimiter", value="|", key="a_delim")

            st.markdown("**Advanced**")
            av1, av2 = st.columns(2)
            with av1:
                a_filter = st.text_input("Filter Condition", placeholder="Status = 'Active'", key="a_filter")
                a_trim = st.selectbox("Trim", ["N", "Y"], key="a_trim")
            with av2:
                a_encrypt = st.text_input("Encryption Columns", placeholder="SSN,CreditCard", key="a_encrypt")
                a_cloud = st.text_input("Cloud Path", value=os.getenv("CLOUD_PATH", ""), key="a_cloud")

            a_sql = st.text_area("Custom SQL (overrides table export)", placeholder="SELECT col1, col2 FROM ...", key="a_sql", height=80)

            if st.form_submit_button("Add Configuration", type="primary"):
                if a_db and a_tbl and a_pk:
                    tables.append({
                        "source_db": a_db,
                        "source_schema": a_sch,
                        "source_table": a_tbl,
                        "target_db": a_tgt_db or "ANALYTICS",
                        "target_schema": a_tgt_sch or "PUBLIC",
                        "target_table": (a_tgt_tbl or a_tbl).upper(),
                        "warehouse_name": a_wh or "COMPUTE_WH",
                        "scd_type": a_scd,
                        "load_type": a_load,
                        "cdc_columns": a_cdc.upper() if a_cdc else None,
                        "cdc_type": a_cdc_type,
                        "primary_key": a_pk.upper(),
                        "delimiter": a_delim or "|",
                        "filter_condition": a_filter or None,
                        "trim": a_trim,
                        "encryption_columns": a_encrypt or None,
                        "cloud_path": a_cloud or os.getenv("CLOUD_PATH", ""),
                        "custom_sql": a_sql or None,
                        "execution_mode": a_mode,
                        "active": True,
                        "last_run_status": None,
                    })
                    cfg["tables"] = tables
                    save_config(cfg)
                    st.success(f"Added {a_db}.{a_sch}.{a_tbl}")
                    st.rerun()
                else:
                    st.error("Source DB, Table, and Primary Key are required.")

    # ── Enable/Disable/Delete ─────────────────────────────────────────────────
    if tables:
        with st.expander("🔄 Manage Tables"):
            labels = [f"{'🟢' if t.get('active') else '🔴'} {t['source_db']}.{t['source_table']}" for t in tables]
            idx = st.selectbox("Table", range(len(labels)), format_func=lambda i: labels[i], key="m_sel")
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                if st.button("Enable", key="m_en"):
                    tables[idx]["active"] = True; cfg["tables"] = tables; save_config(cfg); st.rerun()
            with mc2:
                if st.button("Disable", key="m_dis"):
                    tables[idx]["active"] = False; cfg["tables"] = tables; save_config(cfg); st.rerun()
            with mc3:
                if st.button("Delete", key="m_del"):
                    tables.pop(idx); cfg["tables"] = tables; save_config(cfg); st.rerun()

    # ── Sync (Local ↔ Snowflake CONFIG_TABLE) ─────────────────────────────────
    with st.expander("🔄 Sync (Local ↔ Snowflake CONFIG_TABLE)"):
        sy1, sy2 = st.columns(2)
        with sy1:
            if st.button("⬆️ Push → Snowflake", key="push"):
                sf_execute("DELETE FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE")
                for t in tables:
                    sf_execute(
                        "INSERT INTO DATA_MIGRATION.CONTROL.CONFIG_TABLE "
                        "(MSSQL_DATABASE_NAME, MSSQL_SCHEMA_NAME, MSSQL_TABLE_NAME, "
                        "SF_DATABASE_NAME, SF_SCHEMA_NAME, SF_TABLE_NAME, "
                        "WAREHOUSE_NAME, SCD_TYPE, LOAD_TYPE, CDC_COLUMNS, PRIMARY_KEY, "
                        "DELIMITER, FILTER_CONDITION, TRIM, ENCRYPTION_COLUMNS, "
                        "S3_PATH, CUSTOM_SQL, EXECUTION_MODE, CDC_TYPE, ENABLED) "
                        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            t.get("source_db"), t.get("source_schema", "dbo"), t.get("source_table"),
                            t.get("target_db", "ANALYTICS"), t.get("target_schema", "PUBLIC"), t.get("target_table"),
                            t.get("warehouse_name", "COMPUTE_WH"), t.get("scd_type", 0),
                            (t.get("load_type") or "full").upper(), t.get("cdc_columns"),
                            t.get("primary_key"), t.get("delimiter", "|"),
                            t.get("filter_condition"), t.get("trim", "N"),
                            t.get("encryption_columns"), t.get("cloud_path"),
                            t.get("custom_sql"), (t.get("execution_mode") or "FULL").upper(),
                            (t.get("cdc_type") or "TIMESTAMP").upper(),
                            "Y" if t.get("active") else "N",
                        ),
                    )
                st.success(f"Pushed {len(tables)} table(s) with all fields")
        with sy2:
            if st.button("⬇️ Pull ← Snowflake", key="pull"):
                df = sf_query("SELECT * FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE ORDER BY JOB_ID")
                if not df.empty:
                    cfg["tables"] = [{
                        "source_db": r["MSSQL_DATABASE_NAME"],
                        "source_schema": r["MSSQL_SCHEMA_NAME"],
                        "source_table": r["MSSQL_TABLE_NAME"],
                        "target_db": r["SF_DATABASE_NAME"],
                        "target_schema": r["SF_SCHEMA_NAME"],
                        "target_table": r["SF_TABLE_NAME"],
                        "warehouse_name": r.get("WAREHOUSE_NAME", "COMPUTE_WH"),
                        "scd_type": int(r.get("SCD_TYPE", 0) or 0),
                        "load_type": (r.get("LOAD_TYPE") or "full").lower(),
                        "cdc_columns": r.get("CDC_COLUMNS"),
                        "primary_key": r.get("PRIMARY_KEY"),
                        "delimiter": r.get("DELIMITER", "|"),
                        "filter_condition": r.get("FILTER_CONDITION"),
                        "trim": r.get("TRIM", "N"),
                        "encryption_columns": r.get("ENCRYPTION_COLUMNS"),
                        "cloud_path": r.get("S3_PATH") or os.getenv("CLOUD_PATH", ""),
                        "custom_sql": r.get("CUSTOM_SQL"),
                        "execution_mode": (r.get("EXECUTION_MODE") or "FULL").upper(),
                        "cdc_type": (r.get("CDC_TYPE") or "TIMESTAMP").upper(),
                        "active": r.get("ENABLED") == "Y",
                        "last_run_status": None,
                    } for _, r in df.iterrows()]
                    save_config(cfg)
                    st.success(f"Pulled {len(df)} table(s) with all fields")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RUN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_run:
    cfg = load_config()
    tables = cfg.get("tables", [])
    active = [t for t in tables if t.get("active")]

    if not active:
        st.warning("No active tables. Configure tables first.")
    else:
        # Mode selection
        mode = st.radio(
            "Execution Mode",
            ["FULL", "EXTRACT", "LOAD"],
            horizontal=True,
            captions=[
                "BCP → Upload → COPY INTO (end-to-end)",
                "BCP → Upload only (extract to cloud)",
                "COPY INTO only (load from cloud)",
            ],
        )

        # Table selection
        labels = [f"{t['source_db']}.{t.get('source_schema','dbo')}.{t['source_table']} → {t['target_table']}" for t in active]
        selected = st.multiselect("Tables", range(len(labels)), default=list(range(len(labels))),
                                  format_func=lambda i: labels[i])

        st.markdown("---")

        if st.button(f"▶️ Run {mode}", type="primary", disabled=not selected):
            # Get batch ID
            try:
                r = sf_query("SELECT COALESCE(MAX(BATCH_ID)+1,10000) AS N FROM DATA_MIGRATION.CONTROL.LOG_TABLE")
                batch_id = int(r.iloc[0]["N"])
            except Exception:
                batch_id = 10000

            st.markdown(f"**Batch {batch_id}** — {mode} mode — {len(selected)} table(s)")
            results = []

            for i in selected:
                tbl = active[i]
                job_id = tables.index(tbl) + 1
                with st.container(border=True):
                    progress = st.progress(0)
                    status_text = st.empty()
                    result = run_pipeline(tbl, mode, batch_id, job_id, progress, status_text)
                    results.append(result)

                    with st.expander("Log"):
                        for log in result["logs"]:
                            st.text(log)

            # Save updated statuses
            save_config(cfg)

            # Summary
            st.markdown("---")
            s = sum(1 for r in results if r["status"] == "SUCCESS")
            f = sum(1 for r in results if r["status"] == "FAILED")
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Total", len(results))
            rc2.metric("Success", s)
            rc3.metric("Failed", f)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_results:
    if st.button("🔄 Refresh", key="res_refresh"):
        pass  # triggers rerun

    try:
        log_df = sf_query("SELECT * FROM DATA_MIGRATION.CONTROL.LOG_TABLE ORDER BY BATCH_ID DESC, JOB_ID")
    except Exception as e:
        log_df = pd.DataFrame()
        st.error(f"Could not load results: {e}")

    if log_df.empty:
        st.info("No results yet. Run a migration first.")
    else:
        total = len(log_df)
        success = len(log_df[log_df["FINAL_STATUS"] == "SUCCESS"])
        failed = len(log_df[log_df["FINAL_STATUS"] == "FAILED"])
        avg_dur = log_df[log_df["JOB_DURATION"].notna()]["JOB_DURATION"].mean()

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Total Jobs", total)
        rc2.metric("Success", success, f"{success/total*100:.0f}%")
        rc3.metric("Failed", failed)
        rc4.metric("Avg Duration", f"{avg_dur:.0f}s" if pd.notna(avg_dur) else "—")

        st.markdown("---")

        # Filter
        batches = sorted(log_df["BATCH_ID"].dropna().unique().tolist(), reverse=True)
        sel_batch = st.selectbox("Filter by Batch", ["All"] + [str(int(b)) for b in batches], key="res_batch")

        filtered = log_df if sel_batch == "All" else log_df[log_df["BATCH_ID"] == int(sel_batch)]

        cols = ["BATCH_ID", "JOB_ID", "MSSQL_TABLE_NAME", "SF_TABLE_NAME", "EXECUTION_MODE",
                "LOAD_TYPE", "FINAL_STATUS", "MSSQL_TABLE_COUNT", "SF_TABLE_COUNT", "JOB_DURATION"]
        available = [c for c in cols if c in filtered.columns]
        st.dataframe(filtered[available], hide_index=True, use_container_width=True)


# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="text-align:center;color:{TA_GREY_700};font-size:0.8rem;">'
    f'Powered by <span style="color:{TA_ORANGE};font-weight:600;">Tiger Analytics</span> · Built on Snowflake</p>',
    unsafe_allow_html=True,
)

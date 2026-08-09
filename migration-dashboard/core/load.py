"""load.py — Snowflake load layer: COPY INTO work table + MERGE (SCD 0/1/2)."""
from __future__ import annotations

import os

from core.connections import sf_execute, sf_query


SF_STAGE = os.getenv("SF_STAGE", "@DATA_MIGRATION.CONTROL.MIGRATION_STAGE")


# ─── Work Table Management ────────────────────────────────────────────────────

def ensure_work_schema(tgt_db: str, tgt_schema: str):
    """Create the _WRK schema if it doesn't exist."""
    wrk_schema = f"{tgt_schema}_WRK"
    sf_execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_db}.{wrk_schema}")


def prepare_work_table(tgt_db: str, tgt_schema: str, tgt_table: str):
    """Create work table as clone of target (or truncate if exists)."""
    wrk_schema = f"{tgt_schema}_WRK"
    wrk_fqn = f"{tgt_db}.{wrk_schema}.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    ensure_work_schema(tgt_db, tgt_schema)
    sf_execute(f"CREATE TABLE IF NOT EXISTS {wrk_fqn} LIKE {tgt_fqn}")
    sf_execute(f"TRUNCATE TABLE {wrk_fqn}")
    return wrk_fqn


# ─── COPY INTO ────────────────────────────────────────────────────────────────

def check_files_in_stage(tgt_table: str) -> int:
    """Check if files exist in the stage path. Returns file count."""
    try:
        df = sf_query(f"LIST {SF_STAGE}/{tgt_table}/")
        return len(df) if df is not None and not df.empty else 0
    except Exception:
        return -1  # unknown (LIST failed)


def copy_into(target_fqn: str, tgt_table: str, delimiter: str = "|", compressed: bool = True) -> dict:
    """COPY INTO target from stage. Returns {returncode, sql, log}."""
    compression = "COMPRESSION='GZIP'" if compressed else ""
    copy_sql = (
        f"COPY INTO {target_fqn} FROM {SF_STAGE}/{tgt_table}/ "
        f"FILE_FORMAT=(TYPE=CSV FIELD_DELIMITER='{delimiter}' "
        f"FIELD_OPTIONALLY_ENCLOSED_BY='\"' NULL_IF=('NULL','') SKIP_HEADER=0 {compression}) "
        f"ON_ERROR='CONTINUE'"
    )
    try:
        sf_execute(copy_sql)
        return {"returncode": 0, "sql": copy_sql, "log": f"COPY INTO {target_fqn} — success"}
    except Exception as e:
        return {"returncode": 1, "sql": copy_sql, "log": f"COPY INTO FAILED: {e}"}


# ─── MERGE Logic (SCD 0/1/2) ─────────────────────────────────────────────────

def _get_columns(tgt_db: str, tgt_schema: str, tgt_table: str) -> list[str]:
    """Get column names from Snowflake target table."""
    df = sf_query(
        f"SELECT COLUMN_NAME FROM {tgt_db}.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA='{tgt_schema}' AND TABLE_NAME='{tgt_table}' AND TABLE_CATALOG='{tgt_db}' "
        f"ORDER BY ORDINAL_POSITION"
    )
    return df["COLUMN_NAME"].tolist() if not df.empty else []


def merge_scd0(tgt_db: str, tgt_schema: str, tgt_table: str) -> dict:
    """SCD Type 0: INSERT only (append new rows from work table)."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(sql)
        return {"returncode": 0, "sql": sql, "log": "SCD0: INSERT from work table"}
    except Exception as e:
        return {"returncode": 1, "sql": sql, "log": f"SCD0 FAILED: {e}"}


def merge_scd1(tgt_db: str, tgt_schema: str, tgt_table: str, primary_keys: list[str]) -> dict:
    """SCD Type 1: MERGE — update existing rows + insert new rows."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"
    columns = _get_columns(tgt_db, tgt_schema, tgt_table)

    if not columns or not primary_keys:
        return {"returncode": 1, "sql": "", "log": "No columns or PKs found"}

    # ON condition
    on_clause = " AND ".join(f"TARGET.{pk}=SOURCE.{pk}" for pk in primary_keys)
    # UPDATE SET
    update_set = ", ".join(f"TARGET.{c}=SOURCE.{c}" for c in columns)
    # INSERT columns + values
    insert_cols = ", ".join(columns)
    insert_vals = ", ".join(f"SOURCE.{c}" for c in columns)

    merge_sql = (
        f"MERGE INTO {tgt_fqn} AS TARGET "
        f"USING {wrk_fqn} AS SOURCE ON {on_clause} "
        f"WHEN MATCHED THEN UPDATE SET {update_set} "
        f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
    )
    try:
        sf_execute(merge_sql)
        return {"returncode": 0, "sql": merge_sql, "log": "SCD1: MERGE (update + insert)"}
    except Exception as e:
        return {"returncode": 1, "sql": merge_sql, "log": f"SCD1 MERGE FAILED: {e}"}


def merge_scd2(tgt_db: str, tgt_schema: str, tgt_table: str, primary_keys: list[str]) -> dict:
    """SCD Type 2: Same MERGE as SCD1 (original code had identical logic)."""
    return merge_scd1(tgt_db, tgt_schema, tgt_table, primary_keys)


def full_load(tgt_db: str, tgt_schema: str, tgt_table: str) -> dict:
    """FULL load: DELETE target + INSERT from work table."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    del_sql = f"DELETE FROM {tgt_fqn}"
    ins_sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(del_sql)
        sf_execute(ins_sql)
        return {"returncode": 0, "sql": f"{del_sql}; {ins_sql}", "log": "FULL: DELETE+INSERT from WRK"}
    except Exception as e:
        return {"returncode": 1, "sql": f"{del_sql}; {ins_sql}", "log": f"FULL load FAILED: {e}"}


def filter_load(tgt_db: str, tgt_schema: str, tgt_table: str, filter_condition: str) -> dict:
    """FILTER load: DELETE WHERE condition + INSERT from work table."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"
    condition = filter_condition or "1=1"

    del_sql = f"DELETE FROM {tgt_fqn} WHERE {condition}"
    ins_sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(del_sql)
        sf_execute(ins_sql)
        return {"returncode": 0, "sql": f"{del_sql}; {ins_sql}", "log": f"FILTER: DELETE WHERE + INSERT"}
    except Exception as e:
        return {"returncode": 1, "sql": f"{del_sql}; {ins_sql}", "log": f"FILTER load FAILED: {e}"}


# ─── Load Dispatcher ──────────────────────────────────────────────────────────

def execute_load(tbl: dict) -> dict:
    """Execute the full load sequence: check files → COPY INTO WRK → MERGE/INSERT to target."""
    tgt_db = tbl.get("target_db", "ANALYTICS")
    tgt_schema = tbl.get("target_schema", "PUBLIC")
    tgt_table = tbl["target_table"]
    delimiter = tbl.get("delimiter", "|")
    load_type = tbl.get("load_type", "full")
    scd_type = tbl.get("scd_type", 0)
    primary_key = tbl.get("primary_key", "")
    filter_condition = tbl.get("filter_condition")
    pk_list = [pk.strip() for pk in primary_key.split(",")] if primary_key else []

    logs = []

    # 1. Check files exist
    file_count = check_files_in_stage(tgt_table)
    if file_count == 0:
        return {"returncode": 1, "logs": ["No files found in stage — nothing to load"], "sf_count": 0}
    logs.append(f"Found {file_count} file(s) in stage")

    # 2. Prepare work table
    try:
        wrk_fqn = prepare_work_table(tgt_db, tgt_schema, tgt_table)
        logs.append(f"Work table ready: {wrk_fqn}")
    except Exception as e:
        return {"returncode": 1, "logs": [f"Work table creation failed: {e}"], "sf_count": 0}

    # 3. COPY INTO work table
    result = copy_into(wrk_fqn, tgt_table, delimiter, compressed=True)
    logs.append(result["log"])
    if result["returncode"] != 0:
        return {"returncode": 1, "logs": logs, "sf_count": 0}

    # 4. MERGE / INSERT based on load type + SCD type
    if load_type == "full":
        merge_result = full_load(tgt_db, tgt_schema, tgt_table)
    elif load_type == "filter":
        merge_result = filter_load(tgt_db, tgt_schema, tgt_table, filter_condition)
    elif load_type == "incremental":
        if scd_type == 0:
            merge_result = merge_scd0(tgt_db, tgt_schema, tgt_table)
        elif scd_type == 1:
            merge_result = merge_scd1(tgt_db, tgt_schema, tgt_table, pk_list)
        elif scd_type == 2:
            merge_result = merge_scd2(tgt_db, tgt_schema, tgt_table, pk_list)
        else:
            merge_result = merge_scd1(tgt_db, tgt_schema, tgt_table, pk_list)
    else:
        merge_result = full_load(tgt_db, tgt_schema, tgt_table)

    logs.append(merge_result["log"])

    # 5. Get final count
    sf_count = 0
    try:
        cnt = sf_query(f"SELECT COUNT(*) AS C FROM {tgt_db}.{tgt_schema}.{tgt_table}")
        sf_count = int(cnt.iloc[0]["C"])
    except Exception:
        pass

    return {
        "returncode": merge_result["returncode"],
        "logs": logs,
        "sf_count": sf_count,
        "merge_sql": merge_result.get("sql", ""),
    }

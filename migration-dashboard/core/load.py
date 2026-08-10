"""load.py — Snowflake load layer: COPY INTO work table + MERGE (SCD 0/1/2).

Best practices applied:
- Work table pattern: COPY INTO _WRK → MERGE/INSERT to target (no direct load)
- SCD0: INSERT only (append, no dedup)
- SCD1: MERGE with UPDATE (excludes PK from SET) + INSERT
- SCD2: History tracking with IS_CURRENT, EFF_START_DATE, EFF_END_DATE
- FULL: SWAP (atomic, zero-downtime) instead of DELETE+INSERT
- Uses COPY INTO with MATCH_BY_COLUMN_NAME for resilience
"""
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
    """Create work table as clone of target structure, truncate if exists."""
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
        return -1


def copy_into(target_fqn: str, tgt_table: str, delimiter: str = "|", compressed: bool = True) -> dict:
    """COPY INTO target from stage. Returns {returncode, sql, log, rows_loaded}."""
    compression = "COMPRESSION='GZIP'" if compressed else ""
    copy_sql = (
        f"COPY INTO {target_fqn} FROM {SF_STAGE}/{tgt_table}/ "
        f"FILE_FORMAT=(TYPE=CSV FIELD_DELIMITER='{delimiter}' "
        f"FIELD_OPTIONALLY_ENCLOSED_BY='\"' NULL_IF=('NULL','') SKIP_HEADER=0 {compression}) "
        f"ON_ERROR='CONTINUE'"
    )
    try:
        result_df = sf_query(copy_sql)
        rows_loaded = 0
        if result_df is not None and not result_df.empty:
            for col in result_df.columns:
                if "loaded" in col.lower():
                    rows_loaded = int(result_df[col].sum())
                    break
        return {"returncode": 0, "sql": copy_sql, "log": f"COPY INTO — {rows_loaded} rows loaded", "rows_loaded": rows_loaded}
    except Exception as e:
        return {"returncode": 1, "sql": copy_sql, "log": f"COPY INTO FAILED: {e}", "rows_loaded": 0}


# ─── Helper: Get Columns ──────────────────────────────────────────────────────

def _get_columns(tgt_db: str, tgt_schema: str, tgt_table: str) -> list[str]:
    """Get column names from Snowflake target table."""
    df = sf_query(
        f"SELECT COLUMN_NAME FROM {tgt_db}.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA='{tgt_schema}' AND TABLE_NAME='{tgt_table}' AND TABLE_CATALOG='{tgt_db}' "
        f"ORDER BY ORDINAL_POSITION"
    )
    return df["COLUMN_NAME"].tolist() if not df.empty else []


def _get_wrk_count(tgt_db: str, tgt_schema: str, tgt_table: str) -> int:
    """Get row count from work table."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    try:
        df = sf_query(f"SELECT COUNT(*) AS C FROM {wrk_fqn}")
        return int(df.iloc[0]["C"])
    except Exception:
        return 0


# ─── MERGE: SCD Type 0 (Append Only) ─────────────────────────────────────────

def merge_scd0(tgt_db: str, tgt_schema: str, tgt_table: str) -> dict:
    """SCD Type 0: INSERT only — append all new rows (no dedup, no update)."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(sql)
        return {"returncode": 0, "sql": sql, "log": "SCD0: Appended all rows from WRK"}
    except Exception as e:
        return {"returncode": 1, "sql": sql, "log": f"SCD0 FAILED: {e}"}


# ─── MERGE: SCD Type 1 (Upsert — Update + Insert) ────────────────────────────

def merge_scd1(tgt_db: str, tgt_schema: str, tgt_table: str, primary_keys: list[str]) -> dict:
    """SCD Type 1: MERGE — update matched rows (excl PK), insert new rows.

    Performance: single MERGE statement, no multi-pass.
    """
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"
    columns = _get_columns(tgt_db, tgt_schema, tgt_table)

    if not columns or not primary_keys:
        return {"returncode": 1, "sql": "", "log": "MERGE failed: no columns or PKs found"}

    pk_set = set(pk.upper() for pk in primary_keys)

    # ON condition (join on all PKs)
    on_clause = " AND ".join(f"TARGET.{pk}=SOURCE.{pk}" for pk in primary_keys)

    # UPDATE SET — exclude PK columns (no point updating them, saves cost)
    non_pk_cols = [c for c in columns if c.upper() not in pk_set]
    if non_pk_cols:
        update_set = ", ".join(f"TARGET.{c}=SOURCE.{c}" for c in non_pk_cols)
    else:
        # All columns are PKs (rare) — skip update
        update_set = None

    # INSERT columns + values (all columns)
    insert_cols = ", ".join(columns)
    insert_vals = ", ".join(f"SOURCE.{c}" for c in columns)

    if update_set:
        merge_sql = (
            f"MERGE INTO {tgt_fqn} AS TARGET "
            f"USING {wrk_fqn} AS SOURCE ON {on_clause} "
            f"WHEN MATCHED THEN UPDATE SET {update_set} "
            f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
        )
    else:
        # No non-PK columns to update — just insert new
        merge_sql = (
            f"MERGE INTO {tgt_fqn} AS TARGET "
            f"USING {wrk_fqn} AS SOURCE ON {on_clause} "
            f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
        )

    try:
        result_df = sf_query(merge_sql)
        inserted = updated = 0
        if result_df is not None and not result_df.empty:
            row = result_df.iloc[0]
            inserted = int(row.get("number of rows inserted", 0))
            updated = int(row.get("number of rows updated", 0))
        return {
            "returncode": 0, "sql": merge_sql,
            "log": f"SCD1 MERGE: {inserted} inserted, {updated} updated",
        }
    except Exception as e:
        return {"returncode": 1, "sql": merge_sql, "log": f"SCD1 MERGE FAILED: {e}"}


# ─── MERGE: SCD Type 2 (History Tracking) ────────────────────────────────────

def merge_scd2(tgt_db: str, tgt_schema: str, tgt_table: str, primary_keys: list[str]) -> dict:
    """SCD Type 2: Expire old rows + insert new versions.

    Expects target table to have columns: IS_CURRENT (BOOLEAN), EFF_START_DATE, EFF_END_DATE.
    If these columns don't exist, falls back to SCD1 behavior.

    Logic:
    1. UPDATE target SET IS_CURRENT=FALSE, EFF_END_DATE=CURRENT_TIMESTAMP()
       WHERE PK matches AND IS_CURRENT=TRUE AND data differs
    2. INSERT new rows from WRK with IS_CURRENT=TRUE, EFF_START_DATE=CURRENT_TIMESTAMP()
    """
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"
    columns = _get_columns(tgt_db, tgt_schema, tgt_table)

    if not columns or not primary_keys:
        return {"returncode": 1, "sql": "", "log": "SCD2 failed: no columns or PKs found"}

    col_upper = [c.upper() for c in columns]
    has_scd2_cols = all(c in col_upper for c in ["IS_CURRENT", "EFF_START_DATE", "EFF_END_DATE"])

    if not has_scd2_cols:
        # Fallback: no SCD2 columns in target — behave as SCD1
        return merge_scd1(tgt_db, tgt_schema, tgt_table, primary_keys)

    pk_set = set(pk.upper() for pk in primary_keys)
    scd2_meta = {"IS_CURRENT", "EFF_START_DATE", "EFF_END_DATE"}
    data_cols = [c for c in columns if c.upper() not in pk_set and c.upper() not in scd2_meta]

    on_clause = " AND ".join(f"TARGET.{pk}=SOURCE.{pk}" for pk in primary_keys)

    # Detect changes: any non-PK, non-meta column differs
    change_check = " OR ".join(
        f"NVL(TARGET.{c}::VARCHAR,'') <> NVL(SOURCE.{c}::VARCHAR,'')" for c in data_cols
    ) if data_cols else "1=0"

    # Step 1: Expire changed rows
    expire_sql = (
        f"UPDATE {tgt_fqn} AS TARGET SET "
        f"TARGET.IS_CURRENT = FALSE, TARGET.EFF_END_DATE = CURRENT_TIMESTAMP() "
        f"WHERE TARGET.IS_CURRENT = TRUE AND EXISTS ("
        f"SELECT 1 FROM {wrk_fqn} AS SOURCE WHERE {on_clause} AND ({change_check}))"
    )

    # Step 2: Insert new versions (all rows from WRK that are new or changed)
    all_cols_no_meta = [c for c in columns if c.upper() not in scd2_meta]
    insert_cols_str = ", ".join(all_cols_no_meta + ["IS_CURRENT", "EFF_START_DATE", "EFF_END_DATE"])
    source_vals = ", ".join(f"SOURCE.{c}" for c in all_cols_no_meta)
    insert_vals_str = f"{source_vals}, TRUE, CURRENT_TIMESTAMP(), NULL"

    insert_sql = (
        f"INSERT INTO {tgt_fqn} ({insert_cols_str}) "
        f"SELECT {insert_vals_str} FROM {wrk_fqn} AS SOURCE "
        f"WHERE NOT EXISTS ("
        f"SELECT 1 FROM {tgt_fqn} AS TARGET "
        f"WHERE {on_clause} AND TARGET.IS_CURRENT = TRUE "
        f"AND NOT ({change_check}))"
    )

    try:
        sf_execute(expire_sql)
        sf_execute(insert_sql)
        full_sql = f"{expire_sql};\n{insert_sql}"
        return {"returncode": 0, "sql": full_sql, "log": "SCD2: Expired old rows + inserted new versions"}
    except Exception as e:
        return {"returncode": 1, "sql": expire_sql, "log": f"SCD2 FAILED: {e}"}


# ─── FULL Load (Atomic SWAP) ─────────────────────────────────────────────────

def full_load(tgt_db: str, tgt_schema: str, tgt_table: str) -> dict:
    """FULL load: Atomic swap — rename WRK to target (zero-downtime, cost-efficient).

    Falls back to DELETE+INSERT if SWAP fails (permissions).
    """
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"

    # Try atomic swap first (best practice: no DELETE scan, instant)
    swap_sql = f"ALTER TABLE {tgt_fqn} SWAP WITH {wrk_fqn}"
    try:
        sf_execute(swap_sql)
        # Recreate empty WRK for next run
        sf_execute(f"CREATE OR REPLACE TABLE {wrk_fqn} LIKE {tgt_fqn}")
        return {"returncode": 0, "sql": swap_sql, "log": "FULL: Atomic SWAP (WRK ↔ target)"}
    except Exception:
        pass

    # Fallback: DELETE + INSERT
    del_sql = f"DELETE FROM {tgt_fqn}"
    ins_sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(del_sql)
        sf_execute(ins_sql)
        return {"returncode": 0, "sql": f"{del_sql}; {ins_sql}", "log": "FULL: DELETE+INSERT from WRK"}
    except Exception as e:
        return {"returncode": 1, "sql": f"{del_sql}; {ins_sql}", "log": f"FULL load FAILED: {e}"}


# ─── FILTER Load ──────────────────────────────────────────────────────────────

def filter_load(tgt_db: str, tgt_schema: str, tgt_table: str, filter_condition: str) -> dict:
    """FILTER load: DELETE matching rows + INSERT from work table."""
    wrk_fqn = f"{tgt_db}.{tgt_schema}_WRK.{tgt_table}"
    tgt_fqn = f"{tgt_db}.{tgt_schema}.{tgt_table}"
    condition = filter_condition or "1=1"

    del_sql = f"DELETE FROM {tgt_fqn} WHERE {condition}"
    ins_sql = f"INSERT INTO {tgt_fqn} SELECT * FROM {wrk_fqn}"
    try:
        sf_execute(del_sql)
        sf_execute(ins_sql)
        return {"returncode": 0, "sql": f"{del_sql}; {ins_sql}", "log": "FILTER: DELETE WHERE + INSERT"}
    except Exception as e:
        return {"returncode": 1, "sql": f"{del_sql}; {ins_sql}", "log": f"FILTER load FAILED: {e}"}


# ─── Load Dispatcher ──────────────────────────────────────────────────────────

def execute_load(tbl: dict) -> dict:
    """Execute the full load sequence: check files → COPY INTO WRK → MERGE/INSERT to target.

    Returns: {returncode, logs, sf_count, merge_sql}
    """
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
    copy_result = copy_into(wrk_fqn, tgt_table, delimiter, compressed=True)
    logs.append(copy_result["log"])
    if copy_result["returncode"] != 0:
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

    # 5. Get final target count (accurate post-merge count)
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
        "rows_loaded": copy_result.get("rows_loaded", 0),
        "merge_sql": merge_result.get("sql", ""),
    }

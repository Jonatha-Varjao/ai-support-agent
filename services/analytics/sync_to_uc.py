"""Sync PostgreSQL tables to Unity Catalog Delta tables.

Modes (env var UC_SYNC_MODE):
  - snapshot:     DELETE + full rewrite of the target UC tables
  - incremental:  upsert rows where updated_at > last watermark (stored in
                  <catalog>.<schema>._sync_state)

Requirements:
  - DATABASE_URL            (PostgreSQL, same as the API)
  - DATABRICKS_HOST         (workspace URL)
  - DATABRICKS_CLIENT_ID    (service principal application ID)
  - DATABRICKS_CLIENT_SECRET (service principal OAuth secret)
  - DATABRICKS_UC_CATALOG   (e.g. main)
  - DATABRICKS_UC_SCHEMA    (e.g. mission)
  - UC_SYNC_MODE            (snapshot | incremental, default snapshot)

Usage:
  uv run python services/analytics/sync_to_uc.py
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from databricks.sdk import WorkspaceClient
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Table registry: postgres table -> (uc table, list of column names)
# ---------------------------------------------------------------------------
TABLES: dict[str, tuple[str, list[str]]] = {
    "threads": (
        "threads",
        ["id", "user_id", "title", "archived", "updated_at"],
    ),
    "messages": (
        "messages",
        ["id", "thread_id", "role", "content", "created_at"],
    ),
    "unanswered_questions": (
        "unanswered_questions",
        ["id", "thread_id", "message_id", "query", "top_sim", "reason", "resolved", "created_at"],
    ),
    "human_requests": (
        "human_requests",
        ["id", "user_id", "thread_id", "status", "created_at"],
    ),
    "kb_entries": (
        "kb_entries",
        ["id", "category", "title", "content", "updated_at"],
    ),
}

WATERMARK_COLUMN = "updated_at"
STATE_TABLE = "_sync_state"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pg_engine():
    url = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg")
    return create_engine(url)


def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime,)):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return f"TIMESTAMP '{value.isoformat()}'"
    return "'" + str(value).replace("'", "''") + "'"


def _ddl(table: str, columns: list[str]) -> str:
    col_defs = ", ".join(f"{c} STRING" for c in columns)
    return f"CREATE TABLE IF NOT EXISTS {table} ({col_defs}) USING DELTA"


def _sql_client(ws: WorkspaceClient, warehouse_id: str):
    def run(sql: str):
        res = ws.statement_execution.execute_statement(
            statement=sql,
            warehouse_id=warehouse_id,
        )
        if res.status.state.value != "SUCCEEDED":
            raise RuntimeError(f"SQL failed: {sql}\n{res.status.error}")
        return res
    return run


def _get_warehouse_id(ws: WorkspaceClient) -> str:
    warehouses = list(ws.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouse available in the workspace.")
    return warehouses[0].id


def _ensure_state_table(run, catalog_schema: str) -> None:
    state_table = f"{catalog_schema}.{STATE_TABLE}"
    run(
        f"CREATE TABLE IF NOT EXISTS {state_table} "
        f"(table_name STRING, last_sync TIMESTAMP) USING DELTA"
    )


def _get_watermark(run, catalog_schema: str, table_name: str):
    state_table = f"{catalog_schema}.{STATE_TABLE}"
    # Statement execution API does not support bind parameters; literals are escaped.
    res = run(f"SELECT last_sync FROM {state_table} WHERE table_name = '{table_name}'")
    rows = res.to_pandas()
    if rows.empty:
        return None
    return rows.iloc[0]["last_sync"]


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync_table(pg_conn, run, catalog_schema: str, pg_table: str, uc_table: str, columns: list[str], mode: str) -> int:
    run(_ddl(uc_table, columns))

    if mode == "snapshot":
        run(f"DELETE FROM {uc_table}")
        where_sql = ""
    else:
        watermark = _get_watermark(run, catalog_schema, uc_table)
        if watermark is None:
            where_sql = ""
        else:
            where_sql = f" WHERE {WATERMARK_COLUMN} > TIMESTAMP '{watermark.isoformat()}'"

    col_sql = ", ".join(columns)
    result = pg_conn.execute(text(f"SELECT {col_sql} FROM {pg_table}{where_sql}"))
    rows = result.fetchall()

    if not rows:
        return 0

    values = ", ".join(
        "(" + ", ".join(_sql_literal(v) for v in row) + ")" for row in rows
    )
    run(f"INSERT INTO {uc_table} ({col_sql}) VALUES {values}")

    if mode == "incremental" and rows:
        last_sync = datetime.now(timezone.utc)
        state_table = f"{catalog_schema}.{STATE_TABLE}"
        run(
            f"DELETE FROM {state_table} WHERE table_name = '{uc_table}'; "
            f"INSERT INTO {state_table} VALUES ('{uc_table}', TIMESTAMP '{last_sync.isoformat()}')"
        )
    return len(rows)


def main() -> None:
    mode = os.environ.get("UC_SYNC_MODE", "snapshot")
    if mode not in ("snapshot", "incremental"):
        raise ValueError(f"UC_SYNC_MODE must be snapshot or incremental, got {mode!r}")

    ws = WorkspaceClient()  # unified auth: reads DATABRICKS_* env vars
    warehouse_id = _get_warehouse_id(ws)
    run = _sql_client(ws, warehouse_id)

    catalog = os.environ["DATABRICKS_UC_CATALOG"]
    schema = os.environ["DATABRICKS_UC_SCHEMA"]
    catalog_schema = f"{catalog}.{schema}"

    if mode == "incremental":
        _ensure_state_table(run, catalog_schema)

    pg_engine = _pg_engine()
    total = 0
    with pg_engine.connect() as conn:
        for pg_table, (uc_table, columns) in TABLES.items():
            count = sync_table(conn, run, catalog_schema, pg_table, uc_table, columns, mode)
            total += count
            print(f"[{mode}] {pg_table} -> {catalog_schema}.{uc_table}: {count} rows")

    print(f"Done. Total rows synced: {total}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
import os
import re
from typing import Any

import psycopg
from mcp.server.fastmcp import FastMCP
from psycopg.rows import dict_row

LOGGER = logging.getLogger("postgres-mcp")

DATABASE_URL_ENV = "POSTGRES_MCP_DSN"
DEFAULT_LIMIT = 100
READ_ONLY_PREFIXES = ("select", "with", "explain")
FORBIDDEN_PATTERNS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcomment\b",
    r"\bcopy\b",
    r"\brefresh\b",
    r"\bcall\b",
)

mcp = FastMCP("postgres-mcp", json_response=True)


def _dsn() -> str:
    dsn = os.getenv(DATABASE_URL_ENV)
    if not dsn:
        raise ValueError(
            f"{DATABASE_URL_ENV} is not set. Configure a Postgres DSN before using postgres-mcp."
        )
    return dsn


def _connect() -> psycopg.Connection[Any]:
    return psycopg.connect(_dsn(), row_factory=dict_row)


def _validate_limit(limit: int) -> int:
    if limit < 1:
        return 1
    return min(limit, 1000)


def _ensure_read_only_sql(sql: str) -> str:
    normalized = sql.strip().lstrip("(").strip().lower()
    if not normalized.startswith(READ_ONLY_PREFIXES):
        raise ValueError("Only read-only SELECT/WITH/EXPLAIN queries are allowed.")
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, normalized):
            raise ValueError("Query contains a forbidden non-read-only statement.")
    return sql


def _fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def db_healthcheck() -> dict[str, Any]:
    """Check whether postgres-mcp can connect to the configured database."""
    rows = _fetch_all("select current_database() as database, current_user as current_user")
    return rows[0]


@mcp.tool()
def list_tables(schema: str = "public") -> list[dict[str, Any]]:
    """List tables in a given schema."""
    sql = """
        select table_schema, table_name
        from information_schema.tables
        where table_schema = %s
          and table_type = 'BASE TABLE'
        order by table_name
    """
    return _fetch_all(sql, (schema,))


@mcp.tool()
def describe_table(table_name: str, schema: str = "public") -> list[dict[str, Any]]:
    """Describe the columns of a table."""
    sql = """
        select
            table_schema,
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        from information_schema.columns
        where table_schema = %s
          and table_name = %s
        order by ordinal_position
    """
    return _fetch_all(sql, (schema, table_name))


@mcp.tool()
def run_readonly_query(sql: str, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """Run a read-only SQL query. Only SELECT/WITH/EXPLAIN are allowed."""
    validated_sql = _ensure_read_only_sql(sql)
    capped_limit = _validate_limit(limit)
    wrapped_sql = f"select * from ({validated_sql}) as readonly_query limit {capped_limit}"
    rows = _fetch_all(wrapped_sql)
    return {"row_count": len(rows), "limit": capped_limit, "rows": rows}


@mcp.tool()
def list_expected_domain_tables() -> list[dict[str, str]]:
    """Return the expected core project tables for later implementation alignment."""
    return [
        {"table": "users", "domain": "accounts"},
        {"table": "wallets", "domain": "accounts"},
        {"table": "deposits", "domain": "money-movement"},
        {"table": "withdrawals", "domain": "money-movement"},
        {"table": "pool_positions", "domain": "portfolio"},
        {"table": "ledger_entries", "domain": "ledger"},
        {"table": "markets", "domain": "trading"},
        {"table": "orders", "domain": "trading"},
        {"table": "fills", "domain": "trading"},
        {"table": "trades", "domain": "trading"},
        {"table": "strategy_runs", "domain": "trading"},
        {"table": "risk_events", "domain": "risk"},
        {"table": "fee_events", "domain": "fees"},
        {"table": "referrals", "domain": "growth"},
        {"table": "notifications", "domain": "messaging"},
    ]


@mcp.tool()
def get_recent_rows(table_name: str, order_by: str = "id", limit: int = 20) -> dict[str, Any]:
    """Fetch recent rows from a single table using a simple ordered SELECT."""
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", table_name):
        raise ValueError("Invalid table_name.")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", order_by):
        raise ValueError("Invalid order_by column.")
    capped_limit = _validate_limit(limit)
    sql = f'select * from "{table_name}" order by "{order_by}" desc limit {capped_limit}'
    rows = _fetch_all(sql)
    return {"table": table_name, "row_count": len(rows), "rows": rows}


@mcp.tool()
def get_table_counts(schema: str = "public") -> list[dict[str, Any]]:
    """Return estimated row counts for tables from pg_stat_user_tables."""
    sql = """
        select
            schemaname,
            relname as table_name,
            n_live_tup as estimated_rows
        from pg_stat_user_tables
        where schemaname = %s
        order by relname
    """
    return _fetch_all(sql, (schema,))


@mcp.prompt()
def postgres_investigation_prompt(goal: str) -> str:
    """Generate a prompt for investigating the project's Postgres state safely."""
    return f"""You are investigating Postgres state for this project.

Goal: {goal}

Rules:
- Use only read-only inspection.
- Prefer schema discovery first, then targeted queries.
- Treat Postgres as the source of truth for balances, ledger, trades, and fees.
- Avoid making assumptions about missing tables; inspect first.
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    LOGGER.info("Starting postgres-mcp with transport=%s", transport)
    mcp.run(transport=transport)

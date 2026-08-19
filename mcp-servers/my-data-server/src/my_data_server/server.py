"""Self-hosted MCP server starter for custom A-share data.

Replace the sample tools with calls to your database, REST API, or factor library.
Run locally:
  uv sync && uv run my-data-server

Then point Cursor at http://127.0.0.1:9000/mcp (see .cursor/mcp.json.example).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

DB_PATH = Path(os.getenv("MY_DATA_DB_PATH", "./data/factors.db"))
HTTP_HOST = os.getenv("MY_DATA_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("MY_DATA_PORT", "9000"))

mcp = FastMCP(
    name="my-a-share-data",
    instructions=(
        "Private A-share data service. Use for custom factors, cleaned bars, "
        "and internal research datasets. Public market MCPs are preferred for "
        "standard quotes unless the user explicitly asks for internal data."
    ),
)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factors (
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                factor_value REAL NOT NULL,
                PRIMARY KEY (symbol, trade_date, factor_name)
            )
            """
        )
        conn.commit()


@mcp.tool
def health_check() -> dict[str, Any]:
    """Check whether the self-hosted data service is reachable."""
    return {
        "status": "ok",
        "service": "my-a-share-data",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_path": str(DB_PATH.resolve()),
    }


@mcp.tool
def get_factor(
    symbol: Annotated[str, Field(description="A-share code, e.g. 600519 or 600519.SH")],
    trade_date: Annotated[str, Field(description="Trade date in YYYY-MM-DD")],
    factor_name: Annotated[str, Field(description="Custom factor name, e.g. momentum_20d")],
) -> dict[str, Any]:
    """Read one custom factor value from the internal database."""
    symbol = symbol.split(".")[0]
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT symbol, trade_date, factor_name, factor_value
            FROM factors
            WHERE symbol = ? AND trade_date = ? AND factor_name = ?
            """,
            (symbol, trade_date, factor_name),
        ).fetchone()
    if row is None:
        return {
            "found": False,
            "symbol": symbol,
            "trade_date": trade_date,
            "factor_name": factor_name,
        }
    return {"found": True, **dict(row)}


@mcp.tool
def list_factors(
    symbol: Annotated[str, Field(description="A-share code")],
    factor_name: Annotated[str, Field(description="Custom factor name")],
    start_date: Annotated[str, Field(description="Start date YYYY-MM-DD")],
    end_date: Annotated[str, Field(description="End date YYYY-MM-DD")],
    limit: Annotated[int, Field(default=100, description="Max rows to return")] = 100,
) -> dict[str, Any]:
    """List a factor time series from the internal database."""
    symbol = symbol.split(".")[0]
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT symbol, trade_date, factor_name, factor_value
            FROM factors
            WHERE symbol = ?
              AND factor_name = ?
              AND trade_date >= ?
              AND trade_date <= ?
            ORDER BY trade_date ASC
            LIMIT ?
            """,
            (symbol, factor_name, start_date, end_date, limit),
        ).fetchall()
    return {"count": len(rows), "rows": [dict(r) for r in rows]}


@mcp.tool
def upsert_factor(
    symbol: str,
    trade_date: str,
    factor_name: str,
    factor_value: float,
) -> dict[str, Any]:
    """Insert or update one factor row. Wire this to your ETL pipeline later."""
    symbol = symbol.split(".")[0]
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO factors (symbol, trade_date, factor_name, factor_value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date, factor_name)
            DO UPDATE SET factor_value = excluded.factor_value
            """,
            (symbol, trade_date, factor_name, factor_value),
        )
        conn.commit()
    return {
        "updated": True,
        "symbol": symbol,
        "trade_date": trade_date,
        "factor_name": factor_name,
        "factor_value": factor_value,
    }


@mcp.tool
def proxy_internal_api(
    path: Annotated[str, Field(description="Relative API path, e.g. /v1/signals/latest")],
    method: Annotated[str, Field(description="HTTP method")] = "GET",
) -> dict[str, Any]:
    """Proxy an existing internal REST endpoint.

    Set MY_DATA_API_BASE, e.g. http://127.0.0.1:8080
    """
    base = os.getenv("MY_DATA_API_BASE", "").rstrip("/")
    if not base:
        return {
            "error": "MY_DATA_API_BASE is not configured",
            "hint": "export MY_DATA_API_BASE=http://127.0.0.1:8080",
        }

    import httpx

    url = f"{base}{path}"
    headers: dict[str, str] = {}
    api_key = os.getenv("MY_DATA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with httpx.Client(timeout=30.0) as client:
        response = client.request(method.upper(), url, headers=headers)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return {"url": url, "data": response.json()}
        return {"url": url, "text": response.text}


def main() -> None:
    _init_db()
    mcp.run(transport="streamable-http", host=HTTP_HOST, port=HTTP_PORT)


if __name__ == "__main__":
    main()

"""ClickHouse Cloud connection layer.

Reads configuration from environment variables and exposes a small
client API. No business / investigation logic lives here.
"""

from __future__ import annotations

import os
import threading
from functools import lru_cache
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from dotenv import load_dotenv

# Load repo-root .env when running from backend/ or scripts/
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))
load_dotenv()


class ClickHouseConfigError(RuntimeError):
    """Raised when required ClickHouse env vars are missing."""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    host = os.getenv("CLICKHOUSE_HOST", "").strip()
    username = os.getenv("CLICKHOUSE_USERNAME", "").strip()
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    database = os.getenv("CLICKHOUSE_DATABASE", "on_set_war_room").strip()
    port_raw = os.getenv("CLICKHOUSE_PORT", "8443").strip()
    secure = _env_bool("CLICKHOUSE_SECURE", True)

    missing = [
        key
        for key, value in {
            "CLICKHOUSE_HOST": host,
            "CLICKHOUSE_USERNAME": username,
            "CLICKHOUSE_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        raise ClickHouseConfigError(
            f"Missing required ClickHouse environment variables: {', '.join(missing)}"
        )

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ClickHouseConfigError(
            f"CLICKHOUSE_PORT must be an integer, got {port_raw!r}"
        ) from exc

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database": database,
        "secure": secure,
    }


# clickhouse-connect sessions are not safe for concurrent queries; keep one client per thread.
_thread_state = threading.local()


def get_client(*, database: str | None = None) -> Client:
    """Return a thread-local ClickHouse Cloud client (HTTPS/TLS)."""
    cfg = get_config()
    db = database if database is not None else cfg["database"]

    clients: dict[str, Client] = getattr(_thread_state, "clients", None) or {}
    _thread_state.clients = clients

    client = clients.get(db)
    if client is None:
        client = clickhouse_connect.get_client(
            host=cfg["host"],
            port=cfg["port"],
            username=cfg["username"],
            password=cfg["password"],
            database=db,
            secure=cfg["secure"],
            verify=True,
        )
        clients[db] = client
    return client


def close_client() -> None:
    clients: dict[str, Client] = getattr(_thread_state, "clients", None) or {}
    for client in clients.values():
        client.close()
    _thread_state.clients = {}
    get_config.cache_clear()


def ping() -> dict[str, Any]:
    """Run SELECT 1 and return timing metadata."""
    import time

    client = get_client()
    started = time.perf_counter()
    result = client.query("SELECT 1 AS ok")
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    ok = bool(result.result_rows and result.result_rows[0][0] == 1)
    return {"ok": ok, "latency_ms": latency_ms}


def query(sql: str, parameters: dict[str, Any] | None = None):
    """Execute a read query and return the clickhouse-connect result."""
    return get_client().query(sql, parameters=parameters or {})


def command(sql: str, parameters: dict[str, Any] | None = None):
    """Execute a DDL/DML command."""
    return get_client().command(sql, parameters=parameters or {})


def insert(
    table: str,
    rows: list[list[Any]] | list[tuple[Any, ...]],
    column_names: list[str],
    *,
    database: str | None = None,
) -> None:
    """Insert rows into a ClickHouse table via the native insert API."""
    if not rows:
        return
    client = get_client(database=database)
    client.insert(table, rows, column_names=column_names)

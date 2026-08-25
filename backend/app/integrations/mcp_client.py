"""Future ClickHouse MCP bridge.

ADK FunctionTools currently use `app.integrations.clickhouse_client` directly.
When a ClickHouse MCP server is available, wrap the same query functions here
so ADK can call them as MCP tools without changing deterministic engines.
"""

from __future__ import annotations

MCP_STATUS = "stub"


def is_configured() -> bool:
    return False


def describe() -> dict[str, str]:
    return {
        "status": MCP_STATUS,
        "note": "ADK tools use clickhouse-connect directly; MCP wiring deferred.",
    }

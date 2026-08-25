"""Future ClickHouse MCP bridge (optional).

MVP investigation tools use `app.integrations.clickhouse_client` directly.
When a ClickHouse MCP server is available, wrap the same query functions here
so Gemini/ADK can call them as MCP tools without changing deterministic engines.
"""

from __future__ import annotations

MCP_STATUS = "stub"


def is_configured() -> bool:
    return False


def describe() -> dict[str, str]:
    return {
        "status": MCP_STATUS,
        "note": "Direct clickhouse-connect is used for MVP tools; MCP wiring deferred.",
    }

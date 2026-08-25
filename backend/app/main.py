"""FastAPI entrypoint — health checks only for ClickHouse Cloud milestone."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.integrations import clickhouse_client

app = FastAPI(
    title="On-Set War Room",
    version="0.1.0",
    description="Production incident command center backend",
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/health/clickhouse")
def health_clickhouse():
    try:
        result = clickhouse_client.ping()
        if not result.get("ok"):
            return JSONResponse(status_code=503, content=result)
        return result
    except clickhouse_client.ClickHouseConfigError as exc:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001 — surface connectivity failures cleanly
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc)},
        )

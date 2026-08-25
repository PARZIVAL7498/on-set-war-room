"""FastAPI entrypoint — health, events, incidents, agent, simulate."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.agent import router as agent_router
from app.api.events import router as events_router
from app.api.incidents import router as incidents_router
from app.api.simulate import router as simulate_router
from app.integrations import clickhouse_client, gemini
from app.services import event_service

app = FastAPI(
    title="On-Set War Room",
    version="0.2.0",
    description="Production incident command center — Agentic Cinema / ClickHouse partner track",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(incidents_router)
app.include_router(agent_router)
app.include_router(simulate_router)


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
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc)},
        )


@app.get("/health/gemini")
def health_gemini():
    return {"ok": True, "available": gemini.gemini_available()}


@app.get("/api/production/health")
def production_health(
    production_id: str = Query(default="prod-midnight-protocol"),
):
    try:
        return event_service.production_health(production_id)
    except clickhouse_client.ClickHouseConfigError as exc:
        return JSONResponse(status_code=503, content={"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"ok": False, "error": str(exc)})

"""FastAPI entrypoint — health, events, incidents, agent, simulate, SPA."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.agent import router as agent_router
from app.api.events import router as events_router
from app.api.incidents import router as incidents_router
from app.api.simulate import router as simulate_router
from app.agents import runner as adk_runner
from app.integrations import clickhouse_client
from app.services import event_service

app = FastAPI(
    title="On-Set War Room",
    version="0.3.0",
    description="Production incident command center — Agentic Cinema / ClickHouse partner track",
)

_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = (
    ["*"]
    if _cors_raw == "*"
    else [o.strip() for o in _cors_raw.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
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


@app.get("/health/adk")
def health_adk():
    result = adk_runner.health()
    if not result.get("ok"):
        return JSONResponse(status_code=503, content=result)
    return result


@app.get("/health/gemini")
def health_gemini_compat():
    """Deprecated alias — use /health/adk."""
    return health_adk()


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


def _static_dir() -> Path | None:
    """Optional SPA bundle — API-only deploys (Render backend) skip this safely."""
    raw = os.getenv("STATIC_DIR", "").strip()
    candidates: list[Path] = []
    if raw:
        candidates.append(Path(raw))

    here = Path(__file__).resolve()
    # .../backend/app/main.py → repo root is parents[2]; backend root is parents[1]
    if len(here.parents) > 2:
        repo_root = here.parents[2]
        candidates.append(repo_root / "frontend" / "dist")
        candidates.append(repo_root / "static")
    if len(here.parents) > 1:
        candidates.append(here.parents[1] / "static")

    for path in candidates:
        try:
            if path.is_dir() and (path / "index.html").is_file():
                return path
        except OSError:
            continue
    return None


_STATIC = _static_dir()
if _STATIC is not None:
    assets = _STATIC / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/")
    def spa_index():
        return FileResponse(_STATIC / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "health", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (_STATIC / full_path).resolve()
        try:
            candidate.relative_to(_STATIC.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC / "index.html")

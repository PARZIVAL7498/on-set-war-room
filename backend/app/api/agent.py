"""Agent investigate + action observability endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents import orchestrator
from app.agents.orchestrator import AdkUnavailableError
from app.integrations import clickhouse_client
from app.schemas.incidents import InvestigateRequest, InvestigateResponse
from app.services import event_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(payload: InvestigateRequest) -> InvestigateResponse:
    try:
        incident = orchestrator.run_for_ingested_event(payload.event_id)
    except AdkUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except event_service.EventIngestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except event_service.IncidentStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except clickhouse_client.ClickHouseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {exc}",
        ) from exc

    if incident is None:
        return InvestigateResponse(
            incident_id="",
            skipped=True,
            reason="Monitor agent skipped — event not classified as risky",
        )
    return InvestigateResponse(incident_id=incident.incident_id, skipped=False)


@router.get("/actions/{incident_id}")
def agent_actions(incident_id: str):
    try:
        return event_service.list_agent_actions(incident_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.get("/gemini-status")
@router.get("/adk-status")
def adk_status():
    from app.agents import runner as adk_runner

    health = adk_runner.health()
    return {"available": bool(health.get("ok")), **health}

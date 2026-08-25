"""Incident list/detail APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.integrations import clickhouse_client
from app.schemas.incidents import Incident, IncidentSummary
from app.services import event_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentSummary])
@router.get("/", response_model=list[IncidentSummary], include_in_schema=False)
def list_incidents(
    production_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[IncidentSummary]:
    try:
        return event_service.list_incidents(production_id=production_id, limit=limit)
    except clickhouse_client.ClickHouseConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list incidents: {exc}",
        ) from exc


@router.get("/{incident_id}", response_model=Incident)
def get_incident(incident_id: str) -> Incident:
    try:
        incident = event_service.get_incident(incident_id)
    except clickhouse_client.ClickHouseConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to load incident: {exc}",
        ) from exc

    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.get("/{incident_id}/timeline")
def get_timeline(incident_id: str):
    incident = event_service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident.timeline

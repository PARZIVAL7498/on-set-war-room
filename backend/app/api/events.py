"""Operational event ingestion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.agents import orchestrator
from app.schemas.events import (
    EquipmentEventIn,
    EventIngestResponse,
    EventStatus,
    ResourceEventIn,
)
from app.services import event_service

router = APIRouter(prefix="/api/events", tags=["events"])


def _ingest(payload: ResourceEventIn, *, auto_investigate: bool) -> EventIngestResponse:
    try:
        event_id = event_service.ingest_resource_event(payload)
    except event_service.ProductionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except event_service.EventIngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    incident_id = None
    should_run = auto_investigate and payload.status in {
        EventStatus.DOWN,
        EventStatus.DEGRADED,
    }
    if should_run:
        try:
            incident = orchestrator.run_for_ingested_event(event_id, payload)
            if incident is not None:
                incident_id = incident.incident_id
        except event_service.IncidentStoreError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    return EventIngestResponse(event_id=event_id, stored=True, incident_id=incident_id)


@router.post(
    "",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_resource_event(
    payload: ResourceEventIn,
    investigate: bool = Query(
        default=True,
        description="Auto-run agent pipeline for DOWN/DEGRADED events",
    ),
) -> EventIngestResponse:
    """Ingest a resource status event into ClickHouse Cloud."""
    return _ingest(payload, auto_investigate=investigate)


@router.post(
    "/equipment",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment_event(
    payload: EquipmentEventIn,
    investigate: bool = Query(default=True),
) -> EventIngestResponse:
    """Plan-compatible equipment-only ingest alias."""
    return _ingest(payload.to_resource_event(), auto_investigate=investigate)

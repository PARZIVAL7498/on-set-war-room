"""Scenario simulation endpoints — load canned JSON and ingest (+ investigate)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.agents import orchestrator
from app.schemas.events import EquipmentEventIn, ResourceEventIn
from app.schemas.incidents import Incident
from app.services import event_service

router = APIRouter(prefix="/api/simulate", tags=["simulate"])

# backend/app/api/simulate.py → repo root is parents[3]
_SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "simulator" / "scenarios"


def _scenario_path(name: str) -> Path:
    safe = name.replace("-", "_").strip()
    path = _SCENARIOS_DIR / f"{safe}.json"
    if not path.exists():
        alt = _SCENARIOS_DIR / f"{name}.json"
        if alt.exists():
            return alt
        raise FileNotFoundError(name)
    return path


def _load_payload(raw: dict) -> ResourceEventIn:
    if "equipment_id" in raw and "resource_id" not in raw:
        return EquipmentEventIn.model_validate(raw).to_resource_event()
    return ResourceEventIn.model_validate(raw)


@router.get("/scenarios")
def list_scenarios():
    items = []
    for path in sorted(_SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            payload = _load_payload(data)
            items.append(
                {
                    "name": path.stem,
                    "description": payload.notes
                    or f"{payload.resource_type.value} {payload.resource_id} → {payload.status.value}",
                    "resource_type": payload.resource_type.value,
                    "resource_id": payload.resource_id,
                    "status": payload.status.value,
                }
            )
        except Exception:  # noqa: BLE001
            items.append(
                {
                    "name": path.stem,
                    "description": "unparsed scenario",
                    "resource_type": None,
                    "resource_id": None,
                    "status": None,
                }
            )
    return items


@router.post("/{scenario_name}")
def run_scenario(scenario_name: str, investigate: bool = True):
    try:
        path = _scenario_path(scenario_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario: {scenario_name}",
        ) from None

    raw = json.loads(path.read_text(encoding="utf-8"))
    payload = _load_payload(raw)

    try:
        event_id = event_service.ingest_resource_event(payload)
    except event_service.ProductionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except event_service.EventIngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    incident: Incident | None = None
    if investigate:
        incident = orchestrator.run_for_ingested_event(event_id, payload)

    return {
        "scenario": path.stem,
        "event_id": str(event_id),
        "stored": True,
        "incident": incident.model_dump(mode="json") if incident else None,
    }

"""Investigator agent — runs deterministic ClickHouse investigation tools."""

from __future__ import annotations

from datetime import datetime

from app.schemas.incidents import InvestigationFindings
from app.services import event_service


def investigate_event(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str | None = None,
    event_time: datetime | None = None,
    notes: str = "",
) -> InvestigationFindings:
    """Delegate to event_service.investigate (ClickHouse-backed tools)."""
    return event_service.investigate(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        event_time=event_time,
        notes=notes,
    )

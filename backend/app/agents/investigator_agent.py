"""Investigator — ADK LlmAgent definition + deterministic investigate helper."""

from __future__ import annotations

from datetime import datetime

from app.agents.adk_app import investigator_agent as adk_investigator_agent
from app.schemas.incidents import InvestigationFindings
from app.services import event_service

# Exported for ADK app / tests
agent = adk_investigator_agent


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
    """Authoritative ClickHouse investigation (also used post-ADK for persistence)."""
    return event_service.investigate(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        event_time=event_time,
        notes=notes,
    )

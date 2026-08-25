"""Monitor — rule check used by ADK tool evaluate_event_risk."""

from __future__ import annotations

from app.agents.tools import evaluate_event_risk
from app.schemas.events import ResourceEventIn


def is_risky(event: ResourceEventIn | dict) -> tuple[bool, str]:
    """Return (should_investigate, reason)."""
    if isinstance(event, ResourceEventIn):
        result = evaluate_event_risk(
            production_id=event.production_id,
            resource_type=event.resource_type.value,
            resource_id=event.resource_id,
            status=event.status.value,
        )
    else:
        result = evaluate_event_risk(
            production_id=str(event.get("production_id", "")),
            resource_type=str(event.get("resource_type", "")),
            resource_id=str(event.get("resource_id", "")),
            status=str(event.get("status", "")),
        )
    return bool(result.get("investigate")), str(result.get("reason", ""))

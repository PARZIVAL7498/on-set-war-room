"""Monitor agent — rule check: is this event worth investigating?"""

from __future__ import annotations

from app.schemas.events import EventStatus, ResourceEventIn


def is_risky(event: ResourceEventIn | dict) -> tuple[bool, str]:
    """Return (should_investigate, reason).

    MVP rule: DOWN (or DEGRADED equipment) triggers investigation.
    """
    if isinstance(event, ResourceEventIn):
        status = event.status
        resource_type = event.resource_type.value
        resource_id = event.resource_id
    else:
        status_raw = str(event.get("status", "")).upper()
        status = EventStatus(status_raw) if status_raw in EventStatus.__members__ else None
        resource_type = str(event.get("resource_type", ""))
        resource_id = str(event.get("resource_id", ""))

    if status == EventStatus.DOWN:
        return True, f"{resource_type} {resource_id} is DOWN — investigate impact"
    if status == EventStatus.DEGRADED and resource_type == "equipment":
        return True, f"Equipment {resource_id} is DEGRADED — investigate impact"
    return False, f"Status {status} does not require investigation"

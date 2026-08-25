"""ADK FunctionTools — ClickHouse + deterministic engines (JSON-serializable).

These plain functions are registered on LlmAgents. They never invent scenes or scores.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.schemas.events import EventStatus
from app.schemas.incidents import InvestigationFindings
from app.services import event_service, pivot_engine, risk_engine

# In-process trace buffer for the current pipeline run (orchestrator clears/reads).
_TOOL_TRACES: list[dict[str, Any]] = []


def clear_tool_traces() -> None:
    _TOOL_TRACES.clear()


def get_tool_traces() -> list[dict[str, Any]]:
    return list(_TOOL_TRACES)


def _record(tool: str, summary: str, *, latency_ms: float = 0, row_count: int = 0) -> None:
    _TOOL_TRACES.append(
        {
            "tool": tool,
            "summary": summary,
            "latency_ms": latency_ms,
            "row_count": row_count,
        }
    )


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def evaluate_event_risk(
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
) -> dict[str, Any]:
    """Return whether this event should trigger a full investigation.

    Args:
        production_id: Production id (e.g. prod-midnight-protocol).
        resource_type: equipment | crew | location | schedule.
        resource_id: Resource identifier (e.g. CAMERA-02).
        status: UP | DOWN | DEGRADED | DELAYED | CANCELLED.
    """
    status_u = (status or "").upper()
    investigate = False
    reason = f"Status {status_u} does not require investigation"
    if status_u == EventStatus.DOWN.value:
        investigate = True
        reason = f"{resource_type} {resource_id} is DOWN — investigate impact"
    elif status_u == EventStatus.DEGRADED.value and resource_type == "equipment":
        investigate = True
        reason = f"Equipment {resource_id} is DEGRADED — investigate impact"

    result = {
        "investigate": investigate,
        "reason": reason,
        "production_id": production_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status_u,
    }
    _record("evaluate_event_risk", reason, row_count=1 if investigate else 0)
    return result


def get_scenes_requiring_resource(
    production_id: str,
    resource_type: str,
    resource_id: str,
) -> dict[str, Any]:
    """List upcoming scheduled scenes that require the given resource.

    Args:
        production_id: Production id.
        resource_type: Requirement type (usually equipment).
        resource_id: Requirement id (e.g. CAMERA-02).
    """
    scenes, trace = event_service.get_scenes_requiring_resource(
        production_id, resource_type, resource_id, scheduled_only=True
    )
    _record(trace.tool, trace.query_summary, latency_ms=trace.latency_ms, row_count=trace.row_count)
    return {
        "scenes": _serialize(scenes),
        "scene_numbers": [s.scene_number for s in scenes],
        "count": len(scenes),
    }


def get_scene_requirements(
    production_id: str,
    scene_numbers_csv: str,
) -> dict[str, Any]:
    """Fetch requirement rows for comma-separated scene numbers.

    Args:
        production_id: Production id.
        scene_numbers_csv: e.g. \"43,48\".
    """
    nums: list[int] = []
    for part in (scene_numbers_csv or "").split(","):
        part = part.strip()
        if part.isdigit():
            nums.append(int(part))
    by_scene, trace = event_service.get_scene_requirements(production_id, nums)
    _record(trace.tool, trace.query_summary, latency_ms=trace.latency_ms, row_count=trace.row_count)
    return {
        "by_scene": {str(k): _serialize(v) for k, v in by_scene.items()},
        "scene_numbers": nums,
    }


def investigate_resource_event(
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Run the full ClickHouse investigation composition for an event.

    Args:
        production_id: Production id.
        resource_type: Resource type.
        resource_id: Failed resource id.
        status: Event status.
        event_id: Optional ingested event UUID string.
        notes: Optional operator notes.
    """
    findings = event_service.investigate(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id or None,
        notes=notes or "",
    )
    for t in findings.tool_trace:
        _record(t.tool, t.query_summary, latency_ms=t.latency_ms, row_count=t.row_count)
    _record(
        "investigate_resource_event",
        f"affected={[s.scene_number for s in findings.affected_scenes]}",
        row_count=len(findings.affected_scenes),
    )
    return _serialize(findings)


def score_risk(findings_json: str) -> dict[str, Any]:
    """Score operational risk from InvestigationFindings JSON.

    Args:
        findings_json: JSON string of InvestigationFindings (from investigate_resource_event).
    """
    data = json.loads(findings_json) if isinstance(findings_json, str) else findings_json
    findings = InvestigationFindings.model_validate(data)
    risk = risk_engine.score(findings)
    payload = _serialize(risk)
    _record(
        "score_risk",
        f"{risk.level.value} ({risk.score}/100)",
        row_count=1,
    )
    return payload


def find_pivot_candidates(findings_json: str) -> dict[str, Any]:
    """Rank alternative scenes that do not need the failed resource.

    Args:
        findings_json: JSON string of InvestigationFindings.
    """
    data = json.loads(findings_json) if isinstance(findings_json, str) else findings_json
    findings = InvestigationFindings.model_validate(data)
    pivots = pivot_engine.find_candidates(findings)
    _record(
        "find_pivot_candidates",
        f"{len(pivots)} candidate(s); top={pivots[0].scene_number if pivots else None}",
        row_count=len(pivots),
    )
    return {
        "candidates": _serialize(pivots),
        "top_scene": pivots[0].scene_number if pivots else None,
        "count": len(pivots),
    }


# Explicit export list for ADK agent registration
ALL_TOOLS = [
    evaluate_event_risk,
    get_scenes_requiring_resource,
    get_scene_requirements,
    investigate_resource_event,
    score_risk,
    find_pivot_candidates,
]

"""Orchestrator — event → monitor → investigate → impact → pivot → store."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.agents import impact_agent, investigator_agent, monitor_agent, pivot_agent
from app.schemas.events import EventStatus, ResourceEventIn, ResourceType
from app.schemas.incidents import AgentTimelineStep, Incident
from app.services import event_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _step(
    *,
    step: str,
    agent: str,
    summary: str,
    status: str = "ok",
    tool: str | None = None,
    latency_ms: float | None = None,
    row_count: int | None = None,
) -> AgentTimelineStep:
    return AgentTimelineStep(
        step=step,
        agent=agent,
        status=status,
        summary=summary,
        tool=tool,
        latency_ms=latency_ms,
        row_count=row_count,
        timestamp=_now(),
    )


def run_pipeline(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str,
    event_time: datetime | None = None,
    notes: str = "",
) -> Incident | None:
    """Full investigation pipeline. Returns None if monitor skips."""
    timeline: list[AgentTimelineStep] = []

    event_dict = {
        "production_id": production_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
    }
    risky, reason = monitor_agent.is_risky(event_dict)
    timeline.append(
        _step(step="monitor", agent="monitor", summary=reason, status="ok" if risky else "skipped")
    )
    if not risky:
        return None

    t0 = time.perf_counter()
    findings = investigator_agent.investigate_event(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        event_time=event_time,
        notes=notes,
    )
    inv_ms = round((time.perf_counter() - t0) * 1000, 2)
    affected = [s.scene_number for s in findings.affected_scenes]
    timeline.append(
        _step(
            step="investigate",
            agent="investigator",
            summary=f"Affected scenes: {affected}",
            tool="investigate",
            latency_ms=inv_ms,
            row_count=len(affected),
        )
    )
    for trace in findings.tool_trace:
        timeline.append(
            _step(
                step=f"tool:{trace.tool}",
                agent="investigator",
                summary=trace.query_summary,
                tool=trace.tool,
                latency_ms=trace.latency_ms,
                row_count=trace.row_count,
            )
        )

    t1 = time.perf_counter()
    risk = impact_agent.score_impact(findings)
    risk_ms = round((time.perf_counter() - t1) * 1000, 2)
    timeline.append(
        _step(
            step="impact",
            agent="impact",
            summary=f"Risk {risk.level.value} ({risk.score}/100)",
            tool="risk_engine.score",
            latency_ms=risk_ms,
        )
    )

    t2 = time.perf_counter()
    pivots = pivot_agent.find_pivots(findings)
    pivot_ms = round((time.perf_counter() - t2) * 1000, 2)
    timeline.append(
        _step(
            step="pivot_search",
            agent="pivot",
            summary=f"{len(pivots)} candidate(s); top={pivots[0].scene_number if pivots else None}",
            tool="pivot_engine.find_candidates",
            latency_ms=pivot_ms,
            row_count=len(pivots),
        )
    )

    narrative, used_gemini, top = pivot_agent.narrate(findings, risk, pivots)
    timeline.append(
        _step(
            step="narrate",
            agent="pivot",
            summary=("Gemini narration" if used_gemini else "Deterministic narrative template"),
            tool="gemini.narrate_pivot" if used_gemini else "canned_narrative",
        )
    )

    incident_id = event_service.store_incident(
        production_id=production_id,
        event_id=event_id,
        risk=risk,
        findings=findings,
        pivot=top,
        narrative=narrative,
        timeline=timeline,
        status="open",
    )

    incident = event_service.get_incident(incident_id)
    if incident is None:
        # Fallback if MergeTree lag — assemble from memory
        return Incident(
            incident_id=incident_id,
            production_id=production_id,
            event_id=event_id,
            status="open",
            risk_level=risk.level,
            risk_score=risk.score,
            risk_factors=risk.factors,
            affected_scenes=affected,
            evidence=findings,
            recommended_pivot=top,
            narrative=narrative,
            timeline=timeline,
            created_at=_now().replace(tzinfo=None),
            gemini_used=used_gemini,
        )
    incident.gemini_used = used_gemini
    return incident


def run_for_ingested_event(
    event_id: UUID | str,
    payload: ResourceEventIn | None = None,
) -> Incident | None:
    """Load event (or use payload) and run the pipeline."""
    row = event_service.fetch_event_by_id(event_id)
    if row is None and payload is not None:
        return run_pipeline(
            production_id=payload.production_id,
            resource_type=payload.resource_type.value,
            resource_id=payload.resource_id,
            status=payload.status.value,
            event_id=str(event_id),
            event_time=payload.event_time,
            notes=payload.notes or "",
        )
    if row is None:
        raise event_service.EventIngestError(f"Event not found: {event_id}")

    return run_pipeline(
        production_id=row["production_id"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        status=row["status"],
        event_id=str(row["event_id"]),
        event_time=row.get("event_time"),
        notes=row.get("notes") or "",
    )


def run_from_dict(data: dict[str, Any]) -> Incident | None:
    """Convenience for simulate / manual investigate payloads."""
    payload = ResourceEventIn(
        production_id=data["production_id"],
        resource_type=ResourceType(data["resource_type"]),
        resource_id=data["resource_id"],
        status=EventStatus(data["status"]),
        event_time=data.get("event_time"),
        notes=data.get("notes") or "",
    )
    eid = event_service.ingest_resource_event(payload)
    return run_for_ingested_event(eid, payload)

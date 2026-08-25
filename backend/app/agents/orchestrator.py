"""Orchestrator — ADK SequentialAgent pipeline + authoritative tool persistence."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.agents import impact_agent, investigator_agent, monitor_agent, pivot_agent
from app.agents import runner as adk_runner
from app.agents import tools as war_tools
from app.schemas.events import EventStatus, ResourceEventIn, ResourceType
from app.schemas.incidents import AgentTimelineStep, Incident
from app.services import event_service


class AdkUnavailableError(RuntimeError):
    """Raised when GOOGLE_API_KEY / ADK is missing (pipeline fails closed)."""


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
    """ADK investigation pipeline. Returns None if monitor skips."""
    war_tools.clear_tool_traces()
    timeline: list[AgentTimelineStep] = []

    event_dict = {
        "production_id": production_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
    }
    risky, reason = monitor_agent.is_risky(event_dict)
    timeline.append(
        _step(
            step="monitor",
            agent="monitor_agent",
            summary=reason,
            status="ok" if risky else "skipped",
            tool="evaluate_event_risk",
        )
    )
    if not risky:
        return None

    if not adk_runner.adk_available():
        raise AdkUnavailableError(
            "Google ADK is mandatory: install google-adk "
            "(pip install -e backend) so the SequentialAgent pipeline can run."
        )

    t_adk = time.perf_counter()
    adk_result = adk_runner.run_war_room_pipeline(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        notes=notes,
    )
    adk_ms = round((time.perf_counter() - t_adk) * 1000, 2)
    timeline.append(
        _step(
            step="adk_sequential",
            agent="war_room_pipeline",
            summary=f"ADK SequentialAgent session={adk_result.session_id}",
            tool="google.adk.Runner",
            latency_ms=adk_ms,
            row_count=len(adk_result.events_summary),
        )
    )
    for ev in adk_result.events_summary:
        if ev.get("text_preview") or ev.get("author"):
            timeline.append(
                _step(
                    step=f"adk:{ev.get('author') or 'agent'}",
                    agent=str(ev.get("author") or "adk"),
                    summary=str(ev.get("text_preview") or "(tool/thought turn)"),
                    status="ok",
                )
            )

    # Authoritative post-run materialization from the same FunctionTools (demo-safe).
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
            agent="investigator_agent",
            summary=f"Affected scenes: {affected}",
            tool="investigate_resource_event",
            latency_ms=inv_ms,
            row_count=len(affected),
        )
    )

    t1 = time.perf_counter()
    risk = impact_agent.score_impact(findings)
    risk_ms = round((time.perf_counter() - t1) * 1000, 2)
    timeline.append(
        _step(
            step="impact",
            agent="impact_agent",
            summary=f"Risk {risk.level.value} ({risk.score}/100)",
            tool="score_risk",
            latency_ms=risk_ms,
        )
    )

    t2 = time.perf_counter()
    pivots = pivot_agent.find_pivots(findings)
    pivot_ms = round((time.perf_counter() - t2) * 1000, 2)
    top = pivots[0] if pivots else None
    timeline.append(
        _step(
            step="pivot_search",
            agent="narrator_agent",
            summary=f"{len(pivots)} candidate(s); top={top.scene_number if top else None}",
            tool="find_pivot_candidates",
            latency_ms=pivot_ms,
            row_count=len(pivots),
        )
    )

    narrative = (adk_result.narrative or "").strip()
    used_adk = bool(adk_result.used_adk)
    if not narrative:
        narrative = pivot_agent.canned_narrative(findings, risk, pivots)
    # Guardrail: recommended scene must appear when we have one.
    if top and str(top.scene_number) not in narrative:
        narrative = (
            f"{narrative}\n\nRecommended pivot remains Scene {top.scene_number} "
            "per deterministic ADK tool ranking."
        )

    timeline.append(
        _step(
            step="narrate",
            agent="narrator_agent",
            summary="ADK narrator" if adk_result.narrative else "Grounded narrative template",
            tool="adk.narrator_agent" if adk_result.narrative else "canned_narrative",
        )
    )

    for tr in war_tools.get_tool_traces():
        timeline.append(
            _step(
                step=f"tool:{tr['tool']}",
                agent="adk_tools",
                summary=str(tr.get("summary", "")),
                tool=str(tr.get("tool")),
                latency_ms=tr.get("latency_ms"),
                row_count=tr.get("row_count"),
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
            gemini_used=used_adk,
        )
    incident.gemini_used = used_adk
    return incident


def run_for_ingested_event(
    event_id: UUID | str,
    payload: ResourceEventIn | None = None,
) -> Incident | None:
    """Load event (or use payload) and run the ADK pipeline."""
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

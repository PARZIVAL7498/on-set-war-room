"""Event ingestion + deterministic investigation against ClickHouse Cloud."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.integrations import clickhouse_client
from app.schemas.events import ResourceEventIn
from app.schemas.incidents import (
    AgentTimelineStep,
    Incident,
    IncidentSummary,
    InvestigationFindings,
    PivotRecommendation,
    RequirementInfo,
    RiskLevel,
    RiskResult,
    SceneSummary,
    ToolTraceStep,
)


class ProductionNotFoundError(LookupError):
    """Raised when production_id is not present in ClickHouse."""


class EventIngestError(RuntimeError):
    """Raised when ClickHouse insert/query fails during ingestion."""


class IncidentStoreError(RuntimeError):
    """Raised when incident persistence fails."""


def _production_exists(production_id: str) -> bool:
    result = clickhouse_client.query(
        """
        SELECT count()
        FROM on_set_war_room.productions
        WHERE production_id = {production_id:String}
        """,
        {"production_id": production_id},
    )
    return bool(result.result_rows and result.result_rows[0][0] > 0)


def ingest_resource_event(payload: ResourceEventIn) -> UUID:
    """Validate production, insert one row into resource_status_events, return event_id."""
    try:
        if not _production_exists(payload.production_id):
            raise ProductionNotFoundError(
                f"Unknown production_id: {payload.production_id}"
            )

        event_id = uuid4()
        event_time = payload.event_time or datetime.now(timezone.utc)
        if event_time.tzinfo is not None:
            event_time = event_time.astimezone(timezone.utc).replace(tzinfo=None)

        clickhouse_client.insert(
            "resource_status_events",
            [
                [
                    str(event_id),
                    payload.production_id,
                    payload.resource_type.value,
                    payload.resource_id,
                    payload.status.value,
                    event_time,
                    payload.notes,
                ]
            ],
            column_names=[
                "event_id",
                "production_id",
                "resource_type",
                "resource_id",
                "status",
                "event_time",
                "notes",
            ],
        )
        return event_id
    except ProductionNotFoundError:
        raise
    except clickhouse_client.ClickHouseConfigError as exc:
        raise EventIngestError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise EventIngestError(f"Failed to ingest event: {exc}") from exc


def fetch_event_by_id(event_id: UUID | str, *, attempts: int = 5, delay_s: float = 0.4):
    """Poll for a freshly inserted event (MergeTree visibility can lag briefly)."""
    eid = str(event_id)
    for _ in range(attempts):
        result = clickhouse_client.query(
            """
            SELECT
                toString(event_id) AS event_id,
                production_id,
                resource_type,
                resource_id,
                status,
                event_time,
                notes
            FROM on_set_war_room.resource_status_events
            WHERE toString(event_id) = {eid:String}
            LIMIT 1
            """,
            {"eid": eid},
        )
        if result.result_rows:
            columns = list(result.column_names)
            return dict(zip(columns, result.result_rows[0], strict=True))
        time.sleep(delay_s)
    return None


def get_scenes_requiring_resource(
    production_id: str,
    resource_type: str,
    resource_id: str,
    *,
    scheduled_only: bool = True,
) -> tuple[list[SceneSummary], ToolTraceStep]:
    """Return upcoming scenes that require a given resource."""
    started = time.perf_counter()
    sql = """
        SELECT
            s.scene_number,
            s.title,
            s.location_id,
            s.scheduled_start,
            s.scheduled_end,
            s.status
        FROM on_set_war_room.scene_requirements AS r
        ANY INNER JOIN on_set_war_room.scenes AS s
            ON r.production_id = s.production_id
           AND r.scene_number = s.scene_number
        WHERE r.production_id = {production_id:String}
          AND r.requirement_type = {requirement_type:String}
          AND r.requirement_id = {requirement_id:String}
    """
    if scheduled_only:
        sql += " AND s.status = 'scheduled'"
    sql += " ORDER BY s.scheduled_start"

    result = clickhouse_client.query(
        sql,
        {
            "production_id": production_id,
            "requirement_type": resource_type,
            "requirement_id": resource_id,
        },
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    scenes = [
        SceneSummary(
            scene_number=int(row[0]),
            title=row[1],
            location_id=row[2],
            scheduled_start=row[3],
            scheduled_end=row[4],
            status=row[5],
            requirements=[],
        )
        for row in result.result_rows
    ]
    trace = ToolTraceStep(
        tool="get_scenes_requiring_resource",
        query_summary=f"{resource_type}/{resource_id} → {len(scenes)} scenes",
        latency_ms=latency_ms,
        row_count=len(scenes),
    )
    return scenes, trace


def get_scene_requirements(
    production_id: str,
    scene_numbers: list[int],
) -> tuple[dict[int, list[RequirementInfo]], ToolTraceStep]:
    """Fetch requirement rows for specific scenes."""
    if not scene_numbers:
        return {}, ToolTraceStep(
            tool="get_scene_requirements",
            query_summary="no scenes",
            latency_ms=0,
            row_count=0,
        )

    started = time.perf_counter()
    result = clickhouse_client.query(
        """
        SELECT
            scene_number,
            requirement_type,
            requirement_id,
            requirement_name
        FROM on_set_war_room.scene_requirements
        WHERE production_id = {production_id:String}
          AND scene_number IN {scene_numbers:Array(UInt16)}
        ORDER BY scene_number, requirement_type, requirement_id
        """,
        {"production_id": production_id, "scene_numbers": scene_numbers},
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    by_scene: dict[int, list[RequirementInfo]] = {}
    for row in result.result_rows:
        num = int(row[0])
        by_scene.setdefault(num, []).append(
            RequirementInfo(
                requirement_type=row[1],
                requirement_id=row[2],
                requirement_name=row[3] or "",
            )
        )
    trace = ToolTraceStep(
        tool="get_scene_requirements",
        query_summary=f"requirements for scenes {scene_numbers}",
        latency_ms=latency_ms,
        row_count=len(result.result_rows),
    )
    return by_scene, trace


def investigate(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str | None = None,
    event_time: datetime | None = None,
    notes: str = "",
) -> InvestigationFindings:
    """Compose ClickHouse investigation tools into structured findings."""
    scenes, trace_scenes = get_scenes_requiring_resource(
        production_id, resource_type, resource_id, scheduled_only=True
    )
    nums = [s.scene_number for s in scenes]
    reqs, trace_reqs = get_scene_requirements(production_id, nums)
    for scene in scenes:
        scene.requirements = reqs.get(scene.scene_number, [])

    return InvestigationFindings(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        event_time=event_time,
        notes=notes or "",
        affected_scenes=scenes,
        tool_trace=[trace_scenes, trace_reqs],
    )


def store_incident(
    *,
    production_id: str,
    event_id: str,
    risk: RiskResult,
    findings: InvestigationFindings,
    pivot: PivotRecommendation | None,
    narrative: str,
    timeline: list[AgentTimelineStep],
    status: str = "open",
) -> str:
    """Persist an incident (+ optional agent_actions) to ClickHouse."""
    incident_id = f"inc-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    affected = [s.scene_number for s in findings.affected_scenes]
    evidence_json = findings.model_dump_json()
    timeline_json = json.dumps([t.model_dump(mode="json") for t in timeline])
    risk_factors = json.dumps(risk.factors)
    pivot_reasons = json.dumps(pivot.reasons if pivot else [])
    recommended_scene = pivot.scene_number if pivot else 0

    try:
        clickhouse_client.insert(
            "incidents",
            [
                [
                    incident_id,
                    production_id,
                    event_id,
                    status,
                    risk.level.value,
                    risk.score,
                    risk_factors,
                    affected,
                    evidence_json,
                    recommended_scene,
                    pivot_reasons,
                    narrative,
                    timeline_json,
                    created_at,
                ]
            ],
            column_names=[
                "incident_id",
                "production_id",
                "event_id",
                "status",
                "risk_level",
                "risk_score",
                "risk_factors",
                "affected_scenes",
                "evidence_json",
                "recommended_scene",
                "pivot_reasons",
                "narrative",
                "timeline_json",
                "created_at",
            ],
        )

        action_rows: list[list[Any]] = []
        for step in timeline:
            action_rows.append(
                [
                    f"act-{uuid4().hex[:12]}",
                    incident_id,
                    step.step,
                    step.agent,
                    step.tool or "",
                    step.summary,
                    float(step.latency_ms or 0),
                    int(step.row_count or 0),
                    step.status,
                    "",
                    step.timestamp.replace(tzinfo=None)
                    if step.timestamp and step.timestamp.tzinfo
                    else (step.timestamp or created_at),
                ]
            )
        if action_rows:
            clickhouse_client.insert(
                "agent_actions",
                action_rows,
                column_names=[
                    "action_id",
                    "incident_id",
                    "step_name",
                    "agent_name",
                    "tool_name",
                    "query_summary",
                    "latency_ms",
                    "row_count",
                    "status",
                    "detail",
                    "created_at",
                ],
            )
    except clickhouse_client.ClickHouseConfigError as exc:
        raise IncidentStoreError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise IncidentStoreError(f"Failed to store incident: {exc}") from exc

    return incident_id


def _parse_incident_row(row: dict[str, Any]) -> Incident:
    factors_raw = row.get("risk_factors") or "[]"
    pivot_reasons_raw = row.get("pivot_reasons") or "[]"
    timeline_raw = row.get("timeline_json") or "[]"
    evidence_raw = row.get("evidence_json") or "{}"

    factors = json.loads(factors_raw) if isinstance(factors_raw, str) else list(factors_raw)
    pivot_reasons = (
        json.loads(pivot_reasons_raw)
        if isinstance(pivot_reasons_raw, str)
        else list(pivot_reasons_raw)
    )
    timeline_data = (
        json.loads(timeline_raw) if isinstance(timeline_raw, str) else list(timeline_raw)
    )
    evidence_data = (
        json.loads(evidence_raw) if isinstance(evidence_raw, str) else evidence_raw
    )

    evidence = None
    if evidence_data:
        try:
            evidence = InvestigationFindings.model_validate(evidence_data)
        except Exception:  # noqa: BLE001
            evidence = None

    recommended = None
    rec_scene = int(row.get("recommended_scene") or 0)
    if rec_scene:
        title = ""
        location_id = ""
        scheduled_start = None
        if evidence:
            for s in evidence.affected_scenes:
                pass
            # Prefer title from pivot narrative storage — look up from evidence tool
            # by re-querying is heavy; use stored reasons + optional evidence scan.
        # Best-effort: pull title from ClickHouse if needed later; use placeholder from reasons.
        recommended = PivotRecommendation(
            scene_number=rec_scene,
            title=f"Scene {rec_scene}",
            location_id=location_id,
            scheduled_start=scheduled_start,
            reasons=list(pivot_reasons),
            rank_score=0,
        )
        # Enrich title/location from scenes table when possible
        try:
            enrich = clickhouse_client.query(
                """
                SELECT title, location_id, scheduled_start
                FROM on_set_war_room.scenes
                WHERE production_id = {production_id:String}
                  AND scene_number = {scene_number:UInt16}
                LIMIT 1
                """,
                {
                    "production_id": row["production_id"],
                    "scene_number": rec_scene,
                },
            )
            if enrich.result_rows:
                recommended.title = enrich.result_rows[0][0]
                recommended.location_id = enrich.result_rows[0][1]
                recommended.scheduled_start = enrich.result_rows[0][2]
        except Exception:  # noqa: BLE001
            pass

    timeline = [AgentTimelineStep.model_validate(t) for t in timeline_data]

    return Incident(
        incident_id=row["incident_id"],
        production_id=row["production_id"],
        event_id=row["event_id"],
        status=row["status"],
        risk_level=RiskLevel(row["risk_level"]),
        risk_score=int(row["risk_score"]),
        risk_factors=list(factors),
        affected_scenes=list(row.get("affected_scenes") or []),
        evidence=evidence,
        recommended_pivot=recommended,
        narrative=row.get("narrative") or "",
        timeline=timeline,
        created_at=row["created_at"],
        gemini_used=any(
            (t.agent or "").endswith("_agent")
            or (t.tool or "") == "google.adk.Runner"
            or "ADK" in (t.summary or "")
            for t in timeline
        ),
    )


def list_incidents(
    *,
    production_id: str | None = None,
    limit: int = 50,
) -> list[IncidentSummary]:
    where = ""
    params: dict[str, Any] = {"limit": limit}
    if production_id:
        where = "WHERE production_id = {production_id:String}"
        params["production_id"] = production_id

    result = clickhouse_client.query(
        f"""
        SELECT
            incident_id,
            production_id,
            event_id,
            status,
            risk_level,
            risk_score,
            affected_scenes,
            recommended_scene,
            created_at
        FROM on_set_war_room.incidents
        {where}
        ORDER BY created_at DESC
        LIMIT {{limit:UInt32}}
        """,
        params,
    )
    out: list[IncidentSummary] = []
    for row in result.result_rows:
        rec = int(row[7] or 0)
        out.append(
            IncidentSummary(
                incident_id=row[0],
                production_id=row[1],
                event_id=row[2],
                status=row[3],
                risk_level=RiskLevel(row[4]),
                risk_score=int(row[5]),
                affected_scenes=list(row[6] or []),
                recommended_scene=rec or None,
                created_at=row[8],
            )
        )
    return out


def get_incident(incident_id: str, *, attempts: int = 5, delay_s: float = 0.35) -> Incident | None:
    for _ in range(attempts):
        result = clickhouse_client.query(
            """
            SELECT
                incident_id,
                production_id,
                event_id,
                status,
                risk_level,
                risk_score,
                risk_factors,
                affected_scenes,
                evidence_json,
                recommended_scene,
                pivot_reasons,
                narrative,
                timeline_json,
                created_at
            FROM on_set_war_room.incidents
            WHERE incident_id = {incident_id:String}
            LIMIT 1
            """,
            {"incident_id": incident_id},
        )
        if result.result_rows:
            columns = list(result.column_names)
            row = dict(zip(columns, result.result_rows[0], strict=True))
            return _parse_incident_row(row)
        time.sleep(delay_s)
    return None


def list_agent_actions(incident_id: str) -> list[dict[str, Any]]:
    result = clickhouse_client.query(
        """
        SELECT
            action_id,
            incident_id,
            step_name,
            agent_name,
            tool_name,
            query_summary,
            latency_ms,
            row_count,
            status,
            created_at
        FROM on_set_war_room.agent_actions
        WHERE incident_id = {incident_id:String}
        ORDER BY created_at ASC
        """,
        {"incident_id": incident_id},
    )
    columns = list(result.column_names)
    return [dict(zip(columns, row, strict=True)) for row in result.result_rows]


def production_health(production_id: str = "prod-midnight-protocol") -> dict[str, Any]:
    """Aggregate production health for the dashboard."""
    prod = clickhouse_client.query(
        """
        SELECT production_id, name, shoot_date
        FROM on_set_war_room.productions
        WHERE production_id = {production_id:String}
        LIMIT 1
        """,
        {"production_id": production_id},
    )
    scenes = clickhouse_client.query(
        """
        SELECT status, count()
        FROM on_set_war_room.scenes
        WHERE production_id = {production_id:String}
        GROUP BY status
        """,
        {"production_id": production_id},
    )
    open_incidents = clickhouse_client.query(
        """
        SELECT count()
        FROM on_set_war_room.incidents
        WHERE production_id = {production_id:String}
          AND status = 'open'
        """,
        {"production_id": production_id},
    )
    latest_events = clickhouse_client.query(
        """
        SELECT
            toString(event_id),
            resource_type,
            resource_id,
            status,
            event_time,
            notes
        FROM on_set_war_room.resource_status_events
        WHERE production_id = {production_id:String}
        ORDER BY event_time DESC
        LIMIT 8
        """,
        {"production_id": production_id},
    )

    status_counts = {row[0]: int(row[1]) for row in scenes.result_rows}
    production = None
    if prod.result_rows:
        production = {
            "production_id": prod.result_rows[0][0],
            "name": prod.result_rows[0][1],
            "shoot_date": str(prod.result_rows[0][2]),
        }

    return {
        "production": production,
        "scene_status_counts": status_counts,
        "open_incidents": int(open_incidents.result_rows[0][0])
        if open_incidents.result_rows
        else 0,
        "recent_events": [
            {
                "event_id": r[0],
                "resource_type": r[1],
                "resource_id": r[2],
                "status": r[3],
                "event_time": r[4],
                "notes": r[5],
            }
            for r in latest_events.result_rows
        ],
    }

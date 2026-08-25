"""Deterministic pivot / alternative-scene engine — no LLM."""

from __future__ import annotations

from datetime import datetime

from app.integrations import clickhouse_client
from app.schemas.incidents import (
    InvestigationFindings,
    PivotRecommendation,
    SceneSummary,
)


def _fetch_scheduled_scenes(production_id: str) -> list[SceneSummary]:
    result = clickhouse_client.query(
        """
        SELECT
            scene_number,
            title,
            location_id,
            scheduled_start,
            scheduled_end,
            status
        FROM on_set_war_room.scenes
        WHERE production_id = {production_id:String}
          AND status = 'scheduled'
        ORDER BY scheduled_start
        """,
        {"production_id": production_id},
    )
    scenes: list[SceneSummary] = []
    for row in result.result_rows:
        scenes.append(
            SceneSummary(
                scene_number=int(row[0]),
                title=row[1],
                location_id=row[2],
                scheduled_start=row[3],
                scheduled_end=row[4],
                status=row[5],
                requirements=[],
            )
        )
    return scenes


def _scenes_requiring_resource(
    production_id: str,
    resource_type: str,
    resource_id: str,
) -> set[int]:
    result = clickhouse_client.query(
        """
        SELECT DISTINCT scene_number
        FROM on_set_war_room.scene_requirements
        WHERE production_id = {production_id:String}
          AND requirement_type = {requirement_type:String}
          AND requirement_id = {requirement_id:String}
        """,
        {
            "production_id": production_id,
            "requirement_type": resource_type,
            "requirement_id": resource_id,
        },
    )
    return {int(r[0]) for r in result.result_rows}


def find_candidates(
    findings: InvestigationFindings,
    *,
    limit: int = 5,
) -> list[PivotRecommendation]:
    """Rank alternative scenes that do not need the failed resource.

    Hard filters:
    - status == scheduled (not completed)
    - does not require the failed resource
    Ranking preferences:
    - same location as soonest affected scene
    - earlier scheduled_start
    - not in the affected set
    """
    affected_nums = {s.scene_number for s in findings.affected_scenes}
    preferred_location: str | None = None
    if findings.affected_scenes:
        preferred_location = findings.affected_scenes[0].location_id

    blocked = _scenes_requiring_resource(
        findings.production_id,
        findings.resource_type,
        findings.resource_id,
    )
    pool = _fetch_scheduled_scenes(findings.production_id)

    ranked: list[PivotRecommendation] = []
    for scene in pool:
        if scene.scene_number in affected_nums:
            continue
        if scene.scene_number in blocked:
            continue

        reasons: list[str] = [
            f"Does not require failed {findings.resource_type} {findings.resource_id}",
            "Status is scheduled (not completed)",
        ]
        rank = 50.0

        if preferred_location and scene.location_id == preferred_location:
            rank += 40.0
            reasons.append(f"Same location preference ({scene.location_id})")
        else:
            reasons.append(f"Location {scene.location_id} is available")

        # Prefer sooner scenes so the day stays productive.
        if isinstance(scene.scheduled_start, datetime):
            # Earlier in the day → slightly higher rank within same location.
            hour = scene.scheduled_start.hour + scene.scheduled_start.minute / 60.0
            rank += max(0.0, 20.0 - hour)

        ranked.append(
            PivotRecommendation(
                scene_number=scene.scene_number,
                title=scene.title,
                location_id=scene.location_id,
                scheduled_start=scene.scheduled_start,
                reasons=reasons,
                rank_score=rank,
            )
        )

    ranked.sort(key=lambda p: (-p.rank_score, p.scene_number))
    return ranked[:limit]

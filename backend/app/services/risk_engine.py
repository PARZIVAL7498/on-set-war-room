"""Deterministic risk scoring — table-driven, no LLM."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.incidents import InvestigationFindings, RiskLevel, RiskResult

# (min_affected, max_affected) → base score / level
_AFFECTED_SCENE_TABLE: list[tuple[int, int, int, RiskLevel]] = [
    (0, 0, 10, RiskLevel.LOW),
    (1, 1, 45, RiskLevel.MEDIUM),
    (2, 2, 72, RiskLevel.HIGH),
    (3, 99, 88, RiskLevel.CRITICAL),
]

_CRITICAL_EQUIPMENT_PREFIXES = ("CAMERA", "CRANE", "LED-WALL", "VFX")


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _hours_until(event_time: datetime | None, scene_start: datetime) -> float | None:
    et = _as_aware(event_time)
    st = _as_aware(scene_start)
    if et is None or st is None:
        return None
    return (st - et).total_seconds() / 3600.0


def score(findings: InvestigationFindings) -> RiskResult:
    """Score operational risk from investigation findings.

    Factors (documented, reproducible):
    - Number of affected upcoming scenes (table-driven base)
    - Time pressure to nearest affected scene
    - Equipment criticality (camera / major kit)
    - Actor / location resource types bump severity
    """
    factors: list[str] = []
    n = len(findings.affected_scenes)

    base_score = 10
    level = RiskLevel.LOW
    for lo, hi, pts, lvl in _AFFECTED_SCENE_TABLE:
        if lo <= n <= hi:
            base_score = pts
            level = lvl
            break

    if n == 0:
        factors.append("No upcoming scenes depend on this resource")
    else:
        factors.append(f"{n} upcoming scene(s) require {findings.resource_id}")

    bump = 0
    soonest_hours: float | None = None
    for scene in findings.affected_scenes:
        hours = _hours_until(findings.event_time, scene.scheduled_start)
        if hours is None:
            continue
        if soonest_hours is None or hours < soonest_hours:
            soonest_hours = hours

    if soonest_hours is not None:
        if soonest_hours <= 1:
            bump += 15
            factors.append(f"Imminent call sheet pressure ({soonest_hours:.1f}h to next scene)")
        elif soonest_hours <= 3:
            bump += 8
            factors.append(f"Near-term schedule impact ({soonest_hours:.1f}h to next scene)")
        else:
            factors.append(f"Next affected scene in {soonest_hours:.1f}h")

    rid = findings.resource_id.upper()
    if findings.resource_type == "equipment":
        if any(rid.startswith(p) for p in _CRITICAL_EQUIPMENT_PREFIXES):
            bump += 8
            factors.append(f"Critical equipment class ({findings.resource_id})")
    elif findings.resource_type == "actor":
        bump += 6
        factors.append("Principal / cast availability impact")
    elif findings.resource_type == "location":
        bump += 10
        factors.append("Location / weather constraint on shootable units")

    if findings.status == "DOWN":
        factors.append("Resource status DOWN")
    elif findings.status == "DEGRADED":
        bump -= 5
        factors.append("Resource status DEGRADED (partial capability)")

    score_val = max(0, min(100, base_score + bump))

    # Re-map level from final score (still deterministic).
    if score_val >= 85:
        level = RiskLevel.CRITICAL
    elif score_val >= 65:
        level = RiskLevel.HIGH
    elif score_val >= 35:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return RiskResult(score=score_val, level=level, factors=factors)

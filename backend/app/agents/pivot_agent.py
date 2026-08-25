"""Pivot agent — deterministic candidates + optional Gemini narration."""

from __future__ import annotations

from app.integrations import gemini
from app.schemas.incidents import InvestigationFindings, PivotRecommendation, RiskResult
from app.services import pivot_engine


def find_pivots(findings: InvestigationFindings) -> list[PivotRecommendation]:
    return pivot_engine.find_candidates(findings)


def narrate(
    findings: InvestigationFindings,
    risk: RiskResult,
    pivots: list[PivotRecommendation],
) -> tuple[str, bool, PivotRecommendation | None]:
    """Pick top deterministic pivot; narrate with Gemini if available."""
    top = pivots[0] if pivots else None
    narrative, used = gemini.narrate_pivot(
        resource_id=findings.resource_id,
        risk_level=risk.level.value,
        risk_score=risk.score,
        affected_scenes=[s.scene_number for s in findings.affected_scenes],
        pivot_scene=top.scene_number if top else None,
        pivot_title=top.title if top else None,
        factors=risk.factors,
        reasons=top.reasons if top else [],
    )
    return narrative, used, top

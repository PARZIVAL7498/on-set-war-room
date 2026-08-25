"""Pivot / narrator — ADK LlmAgent + deterministic candidates."""

from __future__ import annotations

from app.agents.adk_app import narrator_agent as adk_narrator_agent
from app.schemas.incidents import InvestigationFindings, PivotRecommendation, RiskResult
from app.services import pivot_engine

agent = adk_narrator_agent


def find_pivots(findings: InvestigationFindings) -> list[PivotRecommendation]:
    return pivot_engine.find_candidates(findings)


def canned_narrative(
    findings: InvestigationFindings,
    risk: RiskResult,
    pivots: list[PivotRecommendation],
) -> str:
    top = pivots[0] if pivots else None
    scenes = ", ".join(f"Scene {s.scene_number}" for s in findings.affected_scenes) or "none"
    pivot_line = (
        f"Recommend moving Scene {top.scene_number}"
        + (f" ({top.title})" if top else "")
        + " ahead to keep the day productive."
        if top
        else "No valid pivot candidate passed hard constraints."
    )
    return (
        f"{findings.resource_id} is unavailable. ADK investigation found impact on {scenes}. "
        f"Risk assessed at {risk.level.value} (score {risk.score}/100). "
        f"Drivers: {'; '.join(risk.factors) or 'n/a'}. "
        f"{pivot_line} "
        f"Pivot rationale: {'; '.join(top.reasons) if top else 'n/a'}."
    )

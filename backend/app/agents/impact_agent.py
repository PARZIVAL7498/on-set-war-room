"""Impact — ADK LlmAgent + score_risk tool wrapper."""

from __future__ import annotations

from app.agents.adk_app import impact_agent as adk_impact_agent
from app.schemas.incidents import InvestigationFindings, RiskResult
from app.services import risk_engine

agent = adk_impact_agent


def score_impact(findings: InvestigationFindings) -> RiskResult:
    """Authoritative deterministic score (ADK must call score_risk tool)."""
    return risk_engine.score(findings)

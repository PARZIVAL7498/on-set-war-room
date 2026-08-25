"""Impact agent — thin wrapper over deterministic risk_engine."""

from __future__ import annotations

from app.schemas.incidents import InvestigationFindings, RiskResult
from app.services import risk_engine


def score_impact(findings: InvestigationFindings) -> RiskResult:
    return risk_engine.score(findings)

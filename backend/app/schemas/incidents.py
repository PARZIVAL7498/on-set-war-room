"""Pydantic models for incidents, investigation, risk, and pivots."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequirementInfo(BaseModel):
    requirement_type: str
    requirement_id: str
    requirement_name: str = ""


class SceneSummary(BaseModel):
    scene_number: int
    title: str
    location_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    requirements: list[RequirementInfo] = Field(default_factory=list)


class ToolTraceStep(BaseModel):
    tool: str
    query_summary: str = ""
    latency_ms: float = 0
    row_count: int = 0


class InvestigationFindings(BaseModel):
    production_id: str
    resource_type: str
    resource_id: str
    status: str
    event_id: str | None = None
    event_time: datetime | None = None
    notes: str = ""
    affected_scenes: list[SceneSummary] = Field(default_factory=list)
    tool_trace: list[ToolTraceStep] = Field(default_factory=list)


class RiskResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: RiskLevel
    factors: list[str] = Field(default_factory=list)


class PivotRecommendation(BaseModel):
    scene_number: int
    title: str
    location_id: str
    scheduled_start: datetime | None = None
    reasons: list[str] = Field(default_factory=list)
    rank_score: float = 0.0


class AgentTimelineStep(BaseModel):
    step: str
    agent: str
    status: str = "ok"
    summary: str
    tool: str | None = None
    latency_ms: float | None = None
    row_count: int | None = None
    timestamp: datetime | None = None


class IncidentSummary(BaseModel):
    incident_id: str
    production_id: str
    event_id: str
    status: str
    risk_level: RiskLevel
    risk_score: int
    affected_scenes: list[int]
    recommended_scene: int | None = None
    created_at: datetime
    title: str = ""
    resource_id: str | None = None
    resource_status: str | None = None


class Incident(BaseModel):
    incident_id: str
    production_id: str
    event_id: str
    status: str
    risk_level: RiskLevel
    risk_score: int
    risk_factors: list[str] = Field(default_factory=list)
    affected_scenes: list[int] = Field(default_factory=list)
    evidence: InvestigationFindings | None = None
    recommended_pivot: PivotRecommendation | None = None
    narrative: str = ""
    timeline: list[AgentTimelineStep] = Field(default_factory=list)
    created_at: datetime
    gemini_used: bool = False
    title: str = ""


class InvestigateRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    production_id: str | None = None


class InvestigateResponse(BaseModel):
    incident_id: str
    skipped: bool = False
    reason: str | None = None

"""Google ADK root agent — SequentialAgent war-room pipeline."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))
load_dotenv()

from app.agents import tools as war_tools

GEMINI_MODEL = (
    os.getenv("GEMINI_MODEL", "").strip()
    or os.getenv("GOOGLE_GENAI_MODEL", "").strip()
    or "gemini-3.6-flash"
)

monitor_agent = LlmAgent(
    name="monitor_agent",
    model=GEMINI_MODEL,
    description="Decides whether an on-set resource event warrants investigation.",
    instruction="""You are the On-Set War Room monitor.
Call evaluate_event_risk exactly once with the production_id, resource_type, resource_id, and status from the user message.
Summarize the tool result briefly.
If investigate is false, say SKIP.
If investigate is true, say INVESTIGATE and repeat the reason.
Do not invent equipment or scene numbers.""",
    tools=[war_tools.evaluate_event_risk],
    output_key="monitor_result",
)

investigator_agent = LlmAgent(
    name="investigator_agent",
    model=GEMINI_MODEL,
    description="Gathers ClickHouse evidence for a failed production resource.",
    instruction="""You are the On-Set War Room investigator.
Use tools to gather evidence. Preferred sequence:
1) get_scenes_requiring_resource
2) get_scene_requirements with the returned scene numbers as a CSV
3) investigate_resource_event for the full structured findings

Pass production_id, resource_type, resource_id, status, and event_id from the user message.
Return a short summary of affected scene numbers only from tool output.
Never invent scene numbers.""",
    tools=[
        war_tools.get_scenes_requiring_resource,
        war_tools.get_scene_requirements,
        war_tools.investigate_resource_event,
    ],
    output_key="investigation_findings",
)

impact_agent = LlmAgent(
    name="impact_agent",
    model=GEMINI_MODEL,
    description="Scores operational risk via the deterministic score_risk tool.",
    instruction="""You are the On-Set War Room impact analyst.
You MUST call score_risk with findings_json set to the JSON object returned by investigate_resource_event
(or reconstruct that JSON from session context / prior tool results — never invent scores).
Report only the tool's level and score.
Do not change the numeric score.""",
    tools=[war_tools.score_risk],
    output_key="risk_result",
)

narrator_agent = LlmAgent(
    name="narrator_agent",
    model=GEMINI_MODEL,
    description="Ranks pivot candidates via tools and narrates the recommendation.",
    instruction="""You are the On-Set War Room narrator.
1) Call find_pivot_candidates with findings_json from the investigation (never invent candidates).
2) Write 2-4 short operational paragraphs for producers using ONLY tool facts:
   - failed resource
   - affected scenes from investigation
   - risk level/score from score_risk
   - top pivot scene from find_pivot_candidates
Do not invent scene numbers. If top_scene is null, say no valid pivot passed hard constraints.
End with an explicit recommended pivot line when a top_scene exists.""",
    tools=[war_tools.find_pivot_candidates],
    output_key="narrative",
)

root_agent = SequentialAgent(
    name="war_room_pipeline",
    description="Monitor → Investigate → Impact → Narrate for on-set incidents.",
    sub_agents=[monitor_agent, investigator_agent, impact_agent, narrator_agent],
)

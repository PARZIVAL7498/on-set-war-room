# On-Set War Room — ADK-Mandatory Implementation Plan

Team of two. Backend-first, incremental delivery — a working system at every major milestone. Core MVP scenario: CAMERA-02 failure, end to end.

**Non-negotiable:** Google Agent Development Kit (`google-adk`) is the agent runtime. Investigation is not a hand-rolled Python chain with optional Gemini — it is an in-process ADK `SequentialAgent` whose tools wrap ClickHouse + deterministic engines.

---

## 1. Project Implementation Phases

### Phase 0 — Project Setup & ADK Foundations
- **Goal:** Repo both devs can run with ClickHouse Cloud, FastAPI, and `google-adk` installed.
- **Building:** `.env.example` (ClickHouse + **required** `GOOGLE_API_KEY` / `GEMINI_API_KEY`), `backend/pyproject.toml` with `google-adk`, FastAPI skeleton, `/health`, `/health/adk`.
- **Why here:** ADK auth and imports must work before any agent code.
- **Files:** `.env.example`, `backend/app/main.py`, `backend/pyproject.toml`.
- **Output:** `uvicorn` boots; `/health/adk` → `{ok: true}` when key + ADK import succeed.
- **Test:** `curl /health`, `curl /health/adk`.
- **Depends on:** nothing.

### Phase 1 — ClickHouse Schema & Data Model
- **Goal:** Minimal schema for the camera-failure narrative.
- **Building:** `clickhouse/schema/*.sql` (productions, scenes, scene_requirements, resource_status_events, incidents, agent_actions).
- **Why here:** Tools need real tables.
- **Output:** Tables exist on ClickHouse Cloud.
- **Test:** `SHOW TABLES` matches expectations.
- **Depends on:** Phase 0.

### Phase 2 — Seed Data
- **Goal:** CAMERA-02 → Scenes 43 & 48; Scene 47 is a valid pivot.
- **Building:** `clickhouse/seed/*.sql`, `clickhouse/sample_queries.sql`.
- **Why here:** Demo credibility depends on deliberate data.
- **Output:** Seed queries return expected rows.
- **Test:** Sample queries confirm 43/48/47 narrative.
- **Depends on:** Phase 1.

### Phase 3 — ClickHouse Client & ADK Tool Contract Freeze
- **Goal:** Typed ClickHouse boundary + frozen FunctionTool signatures.
- **Building:** `integrations/clickhouse_client.py`, `agents/tools.py` signatures (even if stubbed early).
- **Why here:** Dev B builds ADK agents against the tool contract while Dev A finishes query bodies.
- **Tools (JSON-serializable):**
  - `evaluate_event_risk`
  - `get_scenes_requiring_resource`
  - `get_scene_details` / `get_scene_requirements`
  - `investigate_resource_event`
  - `score_risk`
  - `find_pivot_candidates`
- **Output:** Contract signed off; tools return structured dicts (never full-table dumps).
- **Test:** Direct tool-function tests (no LLM).
- **Depends on:** Phase 2.

### Phase 4 — Event Ingestion Pipeline
- **Goal:** `CAMERA-02 DOWN` lands in ClickHouse.
- **Building:** `POST /api/events`, `event_service.ingest_resource_event`, simulator scenarios.
- **Output:** HTTP 201 + row in `resource_status_events`.
- **Test:** POST scenario, query ClickHouse.
- **Depends on:** Phase 3.

### Phase 5 — ADK Investigator Agent
- **Goal:** `LlmAgent` that plans tool calls to reproduce investigation findings.
- **Building:** `agents/adk_app.py` investigator + real ClickHouse-backed tools.
- **Why here:** This is the core agentic evidence gatherer.
- **Output:** Given the event, agent calls tools and session/state holds findings equivalent to deterministic investigate.
- **Test:** Content assertions — Scenes 43/48 appear (not exact narrative text).
- **Depends on:** Phase 3–4.

### Phase 6 — Risk Scoring as an ADK Tool
- **Goal:** Reproducible risk via `score_risk` FunctionTool wrapping `risk_engine.score`.
- **Building:** `services/risk_engine.py` + tool wrapper; `impact_agent` LlmAgent that **must** call the tool.
- **Guardrail:** LLM never invents the numeric score — tool output is authoritative.
- **Test:** Fixed findings → fixed HIGH score for camera scenario.
- **Depends on:** Phase 5 findings shape.

### Phase 7 — Pivot Candidates as an ADK Tool
- **Goal:** Hard-constraint pivots via `find_pivot_candidates` wrapping `pivot_engine`.
- **Building:** `services/pivot_engine.py` + tool; narrator agent consumes tool JSON only.
- **Output:** Scene 47 among candidates for CAMERA-02.
- **Test:** Unit test + negative empty-candidate case.
- **Depends on:** Phase 5.

### Phase 8 — ADK SequentialAgent Orchestration ⭐
- **Goal:** One `SequentialAgent` (`war_room_pipeline`): Monitor → Investigator → Impact → Narrator.
- **Building:** `agents/adk_app.py` root agent, `agents/runner.py` (`Runner` + `InMemorySessionService`), `agents/orchestrator.py` thin FastAPI bridge.
- **Flow:** ingest → create session → `runner.run_async` → post-run validator prefers tool payloads → store incident.
- **Output:** POSTing camera-failure alone produces a complete ADK-enriched incident.
- **Test:** End-to-end scenario test (Section 8).
- **Depends on:** Phases 4–7.

### Phase 9 — Incident APIs & agent_actions
- **Goal:** Persist and expose incidents + ADK tool traces.
- **Building:** `api/incidents.py`, `api/agent.py`, insert into `incidents` / `agent_actions` from runner events.
- **Output:** `GET /api/incidents/{id}` includes timeline with ADK tool names; `GET /api/agent/actions/{id}` queryable.
- **Test:** HTTP round-trip after Phase 8 run.
- **Depends on:** Phase 8.

### Phase 10 — Observability & Hardening
- **Goal:** Visible ADK behavior; clear failure if ADK/key unavailable (no silent non-ADK agent path).
- **Building:** Tool latency/row_count logging; `/health/adk`; SSE stretch if time.
- **Depends on:** Phase 9.

### Phase 11 — Frontend
- Dashboard + landing consume Phase 9 API shapes (already in repo).

### Phase 12 — Deployment
- ClickHouse Cloud + Cloud Run FastAPI with Secret Manager for `GOOGLE_API_KEY`.
- ADK runs **in-process** on Cloud Run (not managed Agent Engine for MVP).

---

## 2. Team Division

| Phase | Developer A (ClickHouse / engines / API) | Developer B (ADK / agents) | Shared |
|---|---|---|---|
| 0 | Env, FastAPI health | `google-adk` install, `/health/adk` | Repo conventions |
| 1–2 | Schema + seed | Review query feasibility | Demo narrative rows |
| 3 | Client + query implementations | Stub tools matching contract | **Freeze FunctionTool signatures** |
| 4 | Ingestion + simulator | — | — |
| 5 | Debug query issues | Investigator `LlmAgent` | Findings schema |
| 6–7 | `risk_engine` / `pivot_engine` | Impact + Narrator agents calling tools | Guardrail: tools own numbers/scenes |
| 8 | Wire ingest → orchestrator | `SequentialAgent` + Runner | End-to-end test |
| 9–10 | Incident APIs, `agent_actions` | Event→timeline mapping | Observability |
| 12 | Cloud ClickHouse | Secrets / Cloud Run ADK | Deploy rehearsal |

**Parallelization:** Freeze tool signatures at end of Phase 3 so Dev B builds ADK against stubs while Dev A finishes Phases 4–7 backends.

---

## 3. Dependency Graph

```
ClickHouse schema (P1)
   │
Seed data (P2)
   │
ClickHouse client + ADK tool contract (P3) ──┬── ADK agent scaffolding (stubs)
   │                                         │
Event ingestion (P4)                         │
   │                                         │
   └──────── real tools ─────────────────────┘
                      │
            Investigator LlmAgent (P5)
                      │
         score_risk + find_pivot tools (P6–P7)
                      │
         SequentialAgent + Runner (P8) ⭐
                      │
         Incidents + agent_actions (P9)
                      │
         Observability (P10) → Deploy (P12)
```

---

## 4. Milestones

**M1 — Realistic data.** CAMERA-02 dependents → 43/48; 47 valid pivot.

**M2 — Event ingestion.** Simulator → `resource_status_events`.

**M3 — Tool contract live.** FunctionTools against ClickHouse return correct scenes without LLM.

**M4 — Risk tool.** Fixed evidence → HIGH for camera scenario.

**M5 — Pivot tool.** Scene 47 returned.

**M6 — ADK tools + Investigator.** Agent gathers evidence via tools; structured findings match M3 (content assertions).

**M7 — Full SequentialAgent pipeline.** ⭐ Monitor → Investigator → Impact → Narrator via ADK Runner; POST event → GET incident.

**M8 — Observability.** `agent_actions` / timeline show ADK tool names.

**M9 — Deployed.** M7 passes against public URL.

---

## 5. API Plan

Unchanged surface from MVP, with health rename:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/events` | Ingest + trigger ADK pipeline when risky |
| GET | `/api/incidents`, `/api/incidents/{id}` | List / detail |
| POST | `/api/agent/investigate` | Re-run ADK pipeline for `event_id` |
| GET | `/api/agent/actions/{incident_id}` | Tool traces |
| POST | `/api/simulate/{scenario}` | Canned scenario |
| GET | `/health` | Liveness |
| GET | `/health/clickhouse` | ClickHouse |
| GET | `/health/adk` | ADK import + API key present |

---

## 6. ClickHouse Implementation Plan

Essential tables: `productions`, `scenes`, `scene_requirements`, `resource_status_events`, `incidents`, `agent_actions`.

Crew/location as static fields on scenes/requirements for MVP (not full event streams).

---

## 7. Agent Implementation Plan (ADK)

**Root:** `SequentialAgent` named `war_room_pipeline`.

| Order | `LlmAgent` | Tools | `output_key` |
|---|---|---|---|
| 1 | `monitor_agent` | `evaluate_event_risk` | `monitor_result` |
| 2 | `investigator_agent` | `get_scenes_requiring_resource`, `get_scene_requirements`, `investigate_resource_event` | `investigation_findings` |
| 3 | `impact_agent` | `score_risk` | `risk_result` |
| 4 | `narrator_agent` | `find_pivot_candidates` | `narrative` |

- **Runtime:** `google.adk.runners.Runner` + `InMemorySessionService`, reused across requests; unique `session_id` per incident run.
- **Determinism:** Risk score and pivot ranking come only from tool return values. Post-run validator in orchestrator prefers tool JSON over free text (CAMERA-02 → [43,48] / HIGH / 47).
- **Narration:** Narrator phrases only facts from tools; must not invent scene numbers.
- **MCP:** Deferred stub; tools use `clickhouse-connect` directly.

---

## 8. Testing Plan

- Tool-unit tests (no LLM) for each FunctionTool against seed data.
- Engine table tests for risk/pivot.
- ADK smoke: live key → SequentialAgent run → content assertions.
- **E2E never-break test:** `scripts/verify_mvp.py` — POST `camera_failure` → `affected_scenes == [43, 48]`, `risk_level == HIGH`, `recommended_pivot.scene_number == 47`, timeline includes ADK tool steps.
- `/health/adk` fails closed without key.

---

## 9. Suggested Development Order

1. Env + `google-adk` + `/health/adk`
2. Schema + seed
3. ClickHouse client
4. Freeze `agents/tools.py` contract
5. Ingestion + simulator
6. Implement real tool bodies
7. Investigator `LlmAgent`
8. Risk + pivot tools + Impact/Narrator agents
9. `SequentialAgent` + Runner + orchestrator wire-up
10. Incident APIs + `agent_actions`
11. `verify_mvp.py` green
12. Deploy

---

## 10. Risks and Simplifications

- **ADK/Gemini outage during demo:** Rehearse with recorded run; `/health/adk` gate before demo; tools still unit-testable offline.
- **LLM inventing scenes:** Forbidden by instructions + orchestrator post-run validator using tool payloads.
- **MergeTree read-after-write:** Poll/retry on event fetch.
- **Avoid:** Agent Engine for MVP; ClickHouse MCP until tools are solid; splitting into unmanaged multi-service agents outside SequentialAgent.

---

## Summary

### Recommended MVP architecture
FastAPI + ClickHouse Cloud + **mandatory Google ADK** `SequentialAgent` (Monitor → Investigator → Impact → Narrator). FunctionTools wrap ClickHouse queries and deterministic `risk_engine` / `pivot_engine`. Runner in-process on the API. Incidents + `agent_actions` for observability. Frontend consumes the same incident contract.

### Decisions (locked)
1. ADK in-process on Cloud Run (not Agent Engine)
2. Direct `clickhouse-connect` tools (MCP later)
3. Static crew/location fields for MVP
4. SSE preferred over WebSockets if streaming added
5. Unified requirements model (type + id)
6. **ADK SequentialAgent multi-agent pipeline is mandatory**
7. Live Gemini LLM turns when `GOOGLE_API_KEY` is set; otherwise ADK **tools choreography** (same SequentialAgent tool order) against ClickHouse

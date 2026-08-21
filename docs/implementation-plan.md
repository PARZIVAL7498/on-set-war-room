# On-Set War Room — Backend Implementation Plan (Camera-02 Failure MVP)

Team of two. Backend-first, incremental delivery — a working system at every major milestone. Core MVP scenario: CAMERA-02 failure, end to end.

---

## 1. Project Implementation Phases

### Phase 0 — Project Setup & Foundations
- **Goal:** A repo both devs can run locally with zero ambiguity.
- **Building:** `docker-compose.yml` for local ClickHouse, `.env.example`, Python project config (`pyproject.toml`/`requirements.txt`), FastAPI app skeleton that boots and returns `/health`.
- **Why here:** Everything else needs a running ClickHouse and a running FastAPI process to test against.
- **Files:** `docker-compose.yml`, `.env.example`, `backend/app/main.py`, `backend/pyproject.toml`.
- **Output:** `docker compose up` gives a working ClickHouse; `uvicorn app.main:app` gives a working FastAPI with `/health` → 200.
- **Test:** `curl localhost:8000/health` returns 200. `curl` to ClickHouse HTTP port succeeds.
- **Depends on:** nothing.

### Phase 1 — ClickHouse Schema & Data Model
- **Goal:** Minimal schema that can represent the camera-failure narrative truthfully.
- **Building:** `clickhouse/schema.sql` with essential tables only (see Section 6 for the exact list).
- **Why here:** Nothing above the DB layer can be built without a settled schema.
- **Files:** `clickhouse/schema.sql`.
- **Output:** Tables exist in a fresh ClickHouse instance.
- **Test:** Run schema against a clean ClickHouse, `SHOW TABLES` matches expectations.
- **Depends on:** Phase 0.

### Phase 2 — Seed Data
- **Goal:** A small, hand-crafted dataset where Scene 43 genuinely depends on CAMERA-02 + Actor B + Location X with tight windows, and Scene 47 is a genuinely valid alternative.
- **Building:** `clickhouse/seed.sql` — one production, ~10–15 scenes, ~6 equipment items, ~8 crew/actors, `scene_requirements` rows.
- **Why here:** The demo's credibility depends entirely on this data being deliberately constructed, not random.
- **Files:** `clickhouse/seed.sql`.
- **Output:** Querying `scene_requirements` for CAMERA-02 returns Scene 43 (and one more, e.g. Scene 48, to make the "2 affected scenes" narrative real).
- **Test:** `clickhouse/sample_queries.sql` run manually confirms the exact rows the demo needs exist.
- **Depends on:** Phase 1.

### Phase 3 — ClickHouse Connection Layer & Core Query Service
- **Goal:** One clean, typed boundary between the app and ClickHouse.
- **Building:** `integrations/clickhouse.py` (client factory, config from env), first read functions in a query-service module.
- **Why here:** Everything downstream (ingestion, investigation, agent tools) calls through this layer — it must exist and be stable before those are built.
- **Files:** `backend/app/integrations/clickhouse.py`, `backend/app/services/event_service.py` (read half).
- **Output:** A Python function `get_scenes_requiring_equipment("CAMERA-02")` returns Scene 43/48 from seed data.
- **Test:** Unit test against the running ClickHouse container.
- **Depends on:** Phase 2.

**→ This is also the point where Developer B's tool-contract work can start (see Sections 2/3) — the function signatures defined here are what get wrapped as agent tools later.**

### Phase 4 — Event Ingestion Pipeline
- **Goal:** A real event (`CAMERA-02 DOWN`) can enter the system and land in ClickHouse.
- **Building:** `POST /api/events/equipment`, insert half of `event_service.py`, `simulator/event_generator.py` + `scenarios/camera_failure.json` posting to that endpoint.
- **Why here:** We need real ingested data (not just seed data) flowing before deterministic investigation has something live to react to.
- **Files:** `api/events.py`, `services/event_service.py`, `simulator/event_generator.py`, `simulator/scenarios/camera_failure.json`, `schemas/events.py`.
- **Output:** Running the simulator inserts a row into `equipment_events`; the API returns 201.
- **Test:** POST the scenario, then query ClickHouse directly and confirm the row.
- **Depends on:** Phase 3.

### Phase 5 — Deterministic Investigation Logic
- **Goal:** Given an event, deterministically produce the *evidence* a human investigator would gather — no LLM involved yet.
- **Building:** A pure-Python investigation function chaining: affected scenes → scene requirements → crew/actor availability → location constraints.
- **Why here:** This is the deterministic backbone the agent will later call as tools — build and prove it standalone first.
- **Files:** `services/event_service.py` (investigation composition), `schemas/incidents.py` (evidence shape).
- **Output:** `investigate(event)` returns a structured `InvestigationFindings` object referencing Scene 43/48, their requirements, and constraint data.
- **Test:** Unit test: feed the CAMERA-02 event, assert findings contain exactly the expected scenes/actors/location.
- **Depends on:** Phase 4 (event exists), Phase 2 (data exists).

### Phase 6 — Deterministic Risk Scoring Engine
- **Goal:** A reproducible, explainable risk score.
- **Building:** `services/risk_engine.py` — pure function `score(findings) -> RiskResult` using factors from the brief (# affected scenes, time-to-scene, actor/location deadlines, equipment criticality).
- **Why here:** Must exist before any recommendation logic, and must be provably independent of Gemini.
- **Files:** `services/risk_engine.py`.
- **Output:** Given Phase 5's findings, returns `HIGH` with a numeric score and the contributing factors.
- **Test:** Table-driven unit tests: fixed input → fixed score, across HIGH/MEDIUM/LOW cases.
- **Depends on:** Phase 5.

### Phase 7 — Deterministic Pivot / Alternative Engine
- **Goal:** Find and rank valid alternative scenes using hard constraints only.
- **Building:** `services/pivot_engine.py` — filters all candidate scenes by: same location, crew/actor available, doesn't need the failed equipment, not already shot, fits the time window.
- **Why here:** This must be provably deterministic before Gemini touches it — Gemini will only narrate/rank among *already-valid* outputs, never invent a candidate.
- **Files:** `services/pivot_engine.py`.
- **Output:** Given the CAMERA-02 scenario, Scene 47 is returned as the (or a) valid candidate.
- **Test:** Unit test with the seed data; also a negative test where no valid alternative exists.
- **Depends on:** Phase 5 (needs candidate scene pool + constraints), Phase 1/2 (schema/data).

### Phase 8 — Deterministic Backend APIs  ⭐ *(first fully working milestone, zero AI)*
- **Goal:** Expose the entire deterministic pipeline over HTTP so it's independently demoable even with Gemini switched off.
- **Building:** `GET /api/incidents`, `GET /api/incidents/{id}`, incident-store insert wired to Phases 5–7 output.
- **Why here:** Per the "always have a working system" requirement — this is the point where a full camera-failure "report" can be produced with no AI involvement at all, as a fallback and as a base for the agent layer to enrich.
- **Files:** `api/incidents.py`, `schemas/incidents.py`, incident-store insert in `event_service.py`.
- **Output:** POST the camera-failure event → GET the incident → see risk score + evidence + recommended scene 47, no narrative text yet.
- **Test:** Full HTTP round-trip test (this becomes the skeleton of the end-to-end test in Section 8).
- **Depends on:** Phases 4–7.

### Phase 9 — Gemini + ADK Tool Layer
- **Goal:** Wrap the Phase 3/5 query functions as ADK-callable tools, backed by real ClickHouse (via MCP or direct client — decision pending, see "Decisions" below).
- **Building:** ADK tool definitions, Gemini/ADK auth and config, `integrations/mcp_client.py` if MCP is chosen.
- **Why here:** Tools must exist before an agent can call them — the agent must retrieve evidence through tools, never a data dump.
- **Files:** `agents/investigator_agent.py` (tool defs live here or in a shared `agents/tools.py`), `integrations/mcp_client.py`.
- **Output:** Each tool, called directly (no LLM), returns the same structured data Phase 5's functions return.
- **Test:** Direct tool-function tests (no LLM in the loop).
- **Depends on:** Phase 3 (real query functions) — but can be *started* in parallel earlier against stubs (see Sections 2/3).

### Phase 10 — Investigation Agent
- **Goal:** A real Gemini/ADK agent that plans and executes the tool-calling sequence to reproduce Phase 5's findings on its own.
- **Building:** `agents/investigator_agent.py` orchestration loop.
- **Why here:** This is the one genuinely agentic component — build it in isolation before wiring it into anything else.
- **Files:** `agents/investigator_agent.py`.
- **Output:** Given the raw event, the agent calls tools in a sensible order and returns findings structurally equivalent to Phase 5's deterministic output.
- **Test:** Run against the camera-failure event, assert Scene 43/48 and the right crew/location facts appear in the agent's findings (content assertions, not exact-text assertions).
- **Depends on:** Phase 9.

### Phase 11 — Explanation / Decision Layer
- **Goal:** Turn deterministic risk score + deterministic pivot candidates into the human-readable recommendation, via one Gemini call.
- **Building:** A single Gemini prompt/call that takes `RiskResult` + ranked pivot candidates + evidence, and produces narrative text and final candidate selection *among only the pre-filtered options*.
- **Why here:** Keeps Gemini strictly in the "explain/compare/phrase" role per the architectural principle — needs Phases 6 and 7 finished first.
- **Files:** `agents/impact_agent.py`, `agents/pivot_agent.py` (thin — mostly prompt + call, no independent logic).
- **Output:** The full "Move Scene 47 ahead of Scene 43, because…" text.
- **Test:** Assert the narrative references the correct scene number and doesn't contradict the deterministic score/candidate.
- **Depends on:** Phases 6, 7, 10.

### Phase 12 — Agent Orchestration & Pipeline Wiring
- **Goal:** One orchestrator function triggered by ingestion that runs Monitor(rule) → Investigator(agent) → Risk(deterministic) → Pivot(deterministic) → Explanation(Gemini) → incident store.
- **Building:** `agents/orchestrator.py`, `agents/monitor_agent.py` (simple rule check).
- **Why here:** This is where "multi-agent pipeline" becomes real and automatic instead of manually invoked phase-by-phase.
- **Files:** `agents/orchestrator.py`, `agents/monitor_agent.py`.
- **Output:** POSTing the camera-failure event alone (no manual API calls) produces a complete, agent-enriched incident.
- **Test:** This *is* the end-to-end scenario test (Section 8).
- **Depends on:** Phases 4, 8, 11.

### Phase 13 — Observability, Streaming, Hardening
- **Goal:** Make agent behavior visible and the system resilient to Gemini failures.
- **Building:** `agent_actions` ClickHouse table logging every tool call (query, latency, row count); `GET /api/agent/actions/{incident_id}`; SSE endpoint (`api/stream.py`) pushing incident updates; fallback path so incidents remain readable if Gemini errors (Phase 8's output stands in).
- **Why here:** Directly serves the "reliability" and "observability" production-level requirements, and doubles as ClickHouse-track evidence.
- **Files:** `api/stream.py`, additions to `clickhouse/schema.sql`, logging hooks in Phase 10/11 code.
- **Output:** Every agent run leaves a queryable trace in ClickHouse; dashboard (later) can subscribe via SSE.
- **Test:** Trigger the scenario, query `agent_actions`, confirm expected tool-call rows exist.
- **Depends on:** Phase 12.

### Phase 14 — Frontend (deferred, not started now)
Out of scope for current priority — noted only to preserve the "end with deployment" ordering. Backend API shapes from Phase 8/12/13 are the contract the frontend will consume later.

### Phase 15 — Deployment
- **Goal:** Public hosted URL, satisfying the submission requirement.
- **Building:** ClickHouse Cloud instance, Secret Manager entries, Cloud Run deploy of the FastAPI app.
- **Why last:** Only worth doing once the local end-to-end demo (Phase 12/13) is solid — deploying broken infra wastes hackathon time.
- **Files:** `deployment/` (Dockerfile, Cloud Run config), none of the app code.
- **Output:** A public URL serving the same incident produced locally.
- **Test:** Re-run the end-to-end scenario test against the deployed URL.
- **Depends on:** Phase 13.

---

## 2. Team Division

| Phase | Developer A (ClickHouse/backend/deterministic) | Developer B (Gemini/ADK/agents) | Shared |
|---|---|---|---|
| 0 | Docker/env setup | Gemini API key/ADK install check | Repo conventions |
| 1–2 | Schema + seed data | — (reviews schema for query feasibility) | Agree on data shapes needed for the demo narrative |
| 3 | Connection layer, first query functions | Starts ADK scaffolding against **stub** tool functions | **Freeze tool-function signatures** — this is the key unlock for parallel work |
| 4 | Ingestion API + simulator | — | — |
| 5–7 | Investigation/risk/pivot engines | Continues ADK/agent scaffolding with stubs, drafts prompts | Evidence/output schema (`InvestigationFindings`, `RiskResult`) |
| 8 | Deterministic incident API | Prompt design for Phase 11 explanation call | Incident response shape (frontend contract) |
| 9 | Swaps Dev B's stub tools for real Phase 3/5 functions | Finalizes tool wrappers, MCP integration if chosen | Tool contract validation |
| 10 | Available to debug query issues surfaced by agent | Builds investigation agent | — |
| 11 | — | Builds explanation/decision layer | Reviewing that Gemini never overrides deterministic numbers |
| 12 | Wires ingestion → orchestrator | Wires agent → orchestrator | Orchestrator itself, end-to-end test |
| 13 | `agent_actions` schema, SSE endpoint | Instrumentation of tool calls | — |
| 15 | ClickHouse Cloud provisioning | Cloud Run / Secret Manager for Gemini keys | Deployment run-through |

**Biggest parallelization win:** freeze the tool-function contract at the end of Phase 3 (just the Python function signatures + return schemas, not implementations). Dev B then builds the entire ADK/agent stack against **stubbed** versions of those functions from day 2 onward, in parallel with Dev A building Phases 4–8. Without this, Dev B is blocked until Phase 5 finishes.

---

## 3. Dependency Graph

```
ClickHouse schema (P1)
   │
Seed data (P2)
   │
Connection layer / query service (P3) ──────────────┐
   │                                                 │ (contract frozen here)
Event ingestion (P4)                      ADK scaffolding + stub tools (P9-early, Dev B)
   │                                                 │
Deterministic investigation (P5)                     │
   │                                                 │
   ├── Risk engine (P6)                              │
   └── Pivot engine (P7)                             │
   │                                                 │
Deterministic incident API (P8) ⭐                    │
   │                                                 │
   └──────────── real tools replace stubs ───────────┘
                              │
                    Investigation agent (P10)
                              │
                    Explanation layer (P11) ←── needs P6 + P7 outputs
                              │
                    Orchestration (P12)
                              │
                    Observability + SSE (P13)
                              │
                    Deployment (P15)
```

Parallel-safe from day 1: **schema design (Dev A)** and **ADK/Gemini environment setup + stub-based agent skeleton (Dev B)**. Everything under Dev B's real integration is blocked on P3/P5 only insofar as *real* tool implementations are needed — the agent *architecture* itself is not blocked at all.

---

## 4. Milestones

**M1 — Realistic data exists.** ClickHouse has schema + seed data; querying CAMERA-02's dependents returns Scene 43/48 with correct requirements.
*DoD: sample_queries.sql all return expected rows.*

**M2 — Event ingestion works.** Simulator posts CAMERA-02 DOWN → row lands in `equipment_events`.
*DoD: HTTP 201 + row visible in ClickHouse within the test's polling window.*

**M3 — Deterministic investigation works.** Given the stored event, the backend (no LLM) returns the correct affected scenes, requirements, and constraints.
*DoD: unit test passes against seed data.*

**M4 — Deterministic risk scoring works.**
*DoD: fixed evidence → fixed, documented score; HIGH for the camera scenario.*

**M5 — Deterministic pivot search works.**
*DoD: Scene 47 returned as a valid candidate; a negative-case test with no valid candidate also passes.*

**M6 — Fully working non-AI backend.** ⭐ End-to-end via API: POST event → GET incident with score + evidence + candidate, zero Gemini calls.
*DoD: this is the safety-net demo if AI integration runs late — it must always work.*

**M7 — Agent reproduces the investigation.** Real Gemini/ADK agent calls real ClickHouse-backed tools and returns findings matching M3.
*DoD: content-based assertions pass (right scenes, right people) — not exact text.*

**M8 — Recommendation is narrated.** Gemini explanation layer produces the "Move Scene 47…" text, grounded strictly in M4/M5 outputs.
*DoD: narrative never contradicts the deterministic score or picks a candidate M5 didn't produce.*

**M9 — Full end-to-end agentic pipeline.** ⭐ POST the raw event only → orchestrator runs the whole chain automatically → GET incident shows agent-enriched result.
*DoD: this is the actual demo script, automated as a repeatable test.*

**M10 — Observability visible.** `agent_actions` table populated per run; endpoint exposes it.
*DoD: after M9's test run, the tool-call trace is queryable.*

**M11 — Deployed.**
*DoD: M9's test passes again against the public Cloud Run URL.*

(Frontend milestones deferred to when that work starts.)

---

## 5. API Plan

### Event ingestion
| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| POST | `/api/events/equipment` | Ingest equipment status change | `{production_id, equipment_id, status, timestamp}` | `{event_id, stored: true}` |
| POST | `/api/events/schedule` | Ingest schedule change | `{production_id, scene_id, new_start_time, timestamp}` | `{event_id, stored: true}` |

*(Crew/location ingestion endpoints deferred — see Section 6 on treating those as static reference data for MVP.)*

### Simulation
| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| GET | `/api/simulate/scenarios` | List available canned scenarios | — | `[{name, description}]` |
| POST | `/api/simulate/{scenario_name}` | Trigger a canned scenario (e.g. `camera-failure`) | `{}` | `{event_ids: [...]}` |
| POST | `/api/simulate/reset` | Clear demo data / reset virtual clock (dev only) | `{}` | `{ok: true}` |

### Incidents
| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| GET | `/api/incidents` | List incidents | query: `production_id`, `status` | `[{incident_id, status, risk_level, created_at}]` |
| GET | `/api/incidents/{id}` | Full incident detail | — | `{event, risk, evidence, affected_scenes, recommended_pivot, narrative, agent_timeline}` |
| POST | `/api/incidents/{id}/approve` | Human-in-the-loop approval | `{approved_by}` | `{incident_id, status: "approved"}` |
| GET | `/api/incidents/{id}/timeline` | Step-by-step investigation timeline for UI | — | `[{step, status, summary}]` |

### Agent
| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| POST | `/api/agent/investigate` | Manually trigger investigation for an existing event (testing/demo control) | `{event_id}` | `{incident_id}` |
| GET | `/api/agent/actions/{incident_id}` | Retrieve logged tool calls for an incident | — | `[{tool, query, latency_ms, row_count, timestamp}]` |

### Health / debug
| Method | Path | Purpose | Response |
|---|---|---|---|
| GET | `/health` | Liveness | `{ok: true}` |
| GET | `/health/clickhouse` | ClickHouse connectivity | `{ok: true, latency_ms}` |
| GET | `/health/gemini` | Gemini/ADK reachability | `{ok: true}` |
| GET | `/debug/query` *(dev-only, read-only, guarded)* | Ad-hoc ClickHouse query for debugging | `{rows: [...]}` |

---

## 6. ClickHouse Implementation Plan

**Essential MVP tables only:**
- `productions` — id, name, shoot_date (virtual clock anchor)
- `scenes` — id, production_id, scheduled_start, scheduled_end, location_id, status
- `equipment` — id, name, type, criticality
- `crew` — id, name, role, **available_until** (static field, not an event stream, for MVP)
- `scene_requirements` — scene_id, requirement_type (equipment/crew), requirement_id
- `equipment_events` — production_id, equipment_id, status, timestamp
- `incidents` — id, event_ref, risk_score, risk_level, evidence (JSON), recommended_scene_id, narrative, status, created_at

**Deferred / simplified for MVP:**
- `schedule_events`, `crew_events`, `location_events` as full streams — **collapse into static fields** (`scenes.scheduled_start`, `crew.available_until`, a `location_booking_end` field) instead of event-sourcing them. Real event streams are only strictly needed for the thing that's actually failing (equipment). Revisit as a stretch goal once M9 passes.
- `agent_actions` — added in Phase 13, not needed before the agent exists.

**Phased build:** setup (P0) → schema (P1) → seed (P2) → connection layer (P3) → insert ops (P4) → read/query service (P3/P5) → investigation-specific composed queries (P5) → `agent_actions` (P13).

---

## 7. Agent Implementation Plan

**Recommendation: Option A — one tool-using Investigation Agent — with deterministic engines handling Impact and Pivot, and a single Gemini call for narration.**

Why not Option B (two full agents): a separate "Decision/Pivot Agent" would either (a) duplicate the deterministic filtering already committed to staying out of the LLM, or (b) just be a second prompt wrapping the same risk/pivot engine outputs — which is architecturally just one agent's job. One real tool-calling agent is easier to debug, cheaper to run, and matches the project's own principle better than two.

- **Agent inputs:** the triggering event (`equipment_id`, `status`, `timestamp`, `production_id`).
- **Tools (all backed by real ClickHouse queries):**
  - `get_scenes_requiring_equipment(equipment_id)`
  - `get_scene_details(scene_id)`
  - `get_crew_availability(crew_ids)`
  - `get_location_constraints(location_id)`
  - `get_candidate_alternative_scenes(constraints)`
- **Tool outputs:** scoped, structured JSON rows — never a full-table dump.
- **Orchestration flow:** event → agent plans and calls tools in sequence → structured `InvestigationFindings` → `risk_engine.score()` (deterministic) → `pivot_engine.find_candidates()` (deterministic) → one Gemini call given `{risk, candidates, evidence}` to produce narrative + final pick among candidates.
- **Final structured output:** `Incident{event, risk_score, risk_level, affected_scenes, evidence, recommended_pivot: {scene_id, reasons[]}, narrative_text}`.

The agent is never asked to compute a number or invent a scene — only to decide *which evidence to gather* and *how to phrase* what deterministic code already decided.

---

## 8. Testing Plan

- **ClickHouse:** schema-apply test; seed-data integrity test (expected relationships exist); query-service unit tests against a live test container.
- **FastAPI:** `TestClient` tests per endpoint — ingestion round-trip, incident retrieval shape, health checks.
- **Deterministic logic:** table-driven unit tests for `risk_engine.py` (fixed evidence → fixed score) and `pivot_engine.py` (correct filtering, including the no-valid-candidate edge case).
- **Agent tools:** each tool function tested directly (no LLM) against seed data; then one smoke test where the agent is given the real event and asserted to surface Scene 43/48 (content-based assertions, since LLM phrasing isn't deterministic).
- **End-to-end scenario test (the one that must never break):** reset test data → POST the camera-failure event → call orchestrator → assert `affected_scenes == [43, 48]`, `risk_level == HIGH`, `recommended_pivot.scene_id == 47`. This doubles as the demo rehearsal script.

---

## 9. Suggested Development Order

**Task 1**
Goal: Local environment running.
Files: `docker-compose.yml`, `.env.example`, `backend/pyproject.toml`, `backend/app/main.py`
Developer: A (shared review)
Steps: docker-compose for ClickHouse; FastAPI skeleton; `/health` route.
Verify: `docker compose up` + `curl /health` → 200.

**Task 2**
Goal: Minimal schema exists.
Files: `clickhouse/schema.sql`
Developer: A
Steps: Write the 7 essential tables from Section 6; apply to local ClickHouse.
Verify: `SHOW TABLES` matches the list.

**Task 3**
Goal: Seed data supports the exact demo narrative.
Files: `clickhouse/seed.sql`, `clickhouse/sample_queries.sql`
Developer: A
Steps: Hand-craft production/scenes/equipment/crew/scene_requirements so CAMERA-02 → Scenes 43 & 48, Scene 47 is a valid alternative.
Verify: sample queries return exactly the expected rows.

**Task 4**
Goal: Connection layer works.
Files: `backend/app/integrations/clickhouse.py`
Developer: A
Steps: Client factory from env config; a trivial `SELECT 1` health check function.
Verify: `/health/clickhouse` returns ok.

**Task 5**
Goal: First real query function proven.
Files: `backend/app/services/event_service.py`
Developer: A
Steps: Implement `get_scenes_requiring_equipment(equipment_id)`.
Verify: unit test — calling with `CAMERA-02` returns Scenes 43 & 48.

**Task 6 — freeze the tool contract**
Goal: Dev B unblocked.
Files: a short contract doc/`agents/tools.py` interface stubs
Developer: Shared
Steps: Write function signatures + return schemas for all 5 investigation tools (even before all are implemented for real).
Verify: Both devs sign off; Dev B starts building against stubs matching this.

**Task 7**
Goal: Event ingestion works end-to-end into ClickHouse.
Files: `api/events.py`, `services/event_service.py` (insert half), `schemas/events.py`
Developer: A
Steps: POST endpoint → insert into `equipment_events`.
Verify: POST a camera-down payload, confirm row in ClickHouse.

**Task 8**
Goal: Simulator can trigger the scenario via the real API.
Files: `simulator/event_generator.py`, `simulator/scenarios/camera_failure.json`
Developer: A (or shared)
Steps: Load scenario JSON, POST to Task 7's endpoint.
Verify: running the script produces the same DB row as a manual `curl`.

**Task 9**
Goal: Full deterministic investigation.
Files: `services/event_service.py` (investigation composition), `schemas/incidents.py`
Developer: A
Steps: Chain Task 5 + remaining query functions (crew availability, location constraints) into `investigate(event) -> InvestigationFindings`.
Verify: unit test on the camera event returns correct scenes/people/location facts.

**Task 10**
Goal: Deterministic risk score.
Files: `services/risk_engine.py`
Developer: A
Steps: Implement scoring function per the documented factors.
Verify: table-driven tests, camera scenario scores HIGH.

**Task 11**
Goal: Deterministic pivot candidates.
Files: `services/pivot_engine.py`
Developer: A
Steps: Implement hard-constraint filtering + ranking.
Verify: camera scenario returns Scene 47; a crafted no-alternative case returns empty.

**Task 12 — Milestone 6**
Goal: Fully working non-AI backend.
Files: `api/incidents.py`, incident-store insert
Developer: A
Steps: Wire Tasks 9–11 outputs into an incident record; expose GET endpoints.
Verify: POST event → GET incident shows real score + candidate, no Gemini involved.

**Task 13**
Goal: ADK/Gemini environment ready, tools stubbed.
Files: `agents/investigator_agent.py`, `integrations/mcp_client.py` (if MCP chosen)
Developer: B
Steps: Auth/config for Gemini + ADK; implement Task 6's tool contract against stub data first.
Verify: agent runs against stubs and produces a plausible (if fake) findings object.

**Task 14**
Goal: Real tool-calling investigation agent.
Files: `agents/investigator_agent.py`
Developer: B
Steps: Swap stubs for the real Task 9 functions; run against the real camera event.
Verify: agent's findings contain Scenes 43/48 and correct people/location facts (content assertions).

**Task 15**
Goal: Grounded narrative recommendation.
Files: `agents/impact_agent.py`, `agents/pivot_agent.py`
Developer: B
Steps: One Gemini call consuming Task 10/11 outputs, producing narrative + final phrasing.
Verify: narrative references Scene 47 and doesn't contradict the deterministic score/candidate.

**Task 16 — Milestone 9**
Goal: Full automatic end-to-end pipeline.
Files: `agents/orchestrator.py`, `agents/monitor_agent.py`
Developer: Shared
Steps: Wire ingestion trigger → monitor rule → Task 14 agent → Task 10/11 engines → Task 15 narration → Task 12's incident store.
Verify: POST the raw event only, no manual calls, GET incident shows the fully enriched result. Automate as the permanent regression test.

**Task 17**
Goal: Observability.
Files: schema addition for `agent_actions`, logging hooks, `GET /api/agent/actions/{id}`
Developer: Shared
Steps: Log every tool call's query/latency/row-count during Task 16's run.
Verify: after a run, the trace is queryable and matches what actually happened.

**Task 18**
Goal: Live-updating capability for the (later) frontend.
Files: `api/stream.py`
Developer: A
Steps: SSE endpoint pushing incident state changes.
Verify: `curl -N` the SSE endpoint while triggering the scenario, see events stream in.

This completes the MVP backend. Deployment (Phase 15) follows once Task 16's test is reliably green.

---

## 10. Risks and Simplifications

**Likely technical blockers**
- ClickHouse insert-then-immediate-read timing under MergeTree — verify this doesn't introduce flakiness in the end-to-end test; add a small retry/poll if needed rather than assuming instant visibility.
- ADK/Gemini auth setup eating unplanned time — start Task 13 on day 1, not after Dev A finishes.
- If ClickHouse MCP server is chosen, its own setup/auth is an extra moving part — budget time for it or fall back to a direct client wrapper.

**Unnecessary complexity to avoid**
- Full event-sourcing for crew/location/schedule — static fields are enough for one scenario.
- Building the actor-delay/weather scenarios before camera-failure is airtight.
- WebSockets (SSE is sufficient and simpler), auth, Kafka, k8s, multiple services — none needed.
- Splitting Impact/Pivot into fully independent tool-calling agents when they're deterministic-plus-one-explanation-call.

**Hackathon-specific risks**
- Live Gemini calls during the actual recorded demo are a single point of failure (latency/quota/flaky output). Plan to either record a known-good run, or ensure Phase 8's deterministic output is a safe fallback narration path.
- Dev A's chain (Phases 1–8) is the critical path for Dev B's real integration — mitigate by freezing the tool contract (Task 6) immediately so Dev B is never blocked on Dev A finishing.

**Definitely postpone**
- Multiple scenarios, human-approval UI, full Cloud Logging integration, authentication, automatic schedule mutation, frontend work, and deployment — all after Task 16 is green.

---

## Summary

### Recommended final MVP architecture
Single production, single virtual shooting day, one scenario (CAMERA-02 failure). FastAPI + ClickHouse (local via docker-compose, later ClickHouse Cloud). Deterministic `risk_engine.py`/`pivot_engine.py` as the trusted core; one real ADK/Gemini tool-calling Investigation Agent backed by real ClickHouse queries; one Gemini narration call layered on top of deterministic outputs. Orchestrator wires ingestion → monitor rule → investigation agent → risk/pivot engines → narration → incident store. SSE for live updates, `agent_actions` table for observability. Crew/location availability modeled as static fields, not event streams, for MVP.

### First 5 tasks to actually execute
1. Local dev environment (docker-compose + FastAPI skeleton + `/health`)
2. Minimal ClickHouse schema
3. Hand-crafted seed data proving the camera-failure narrative
4. ClickHouse connection layer
5. First real query function (`get_scenes_requiring_equipment`) + freeze the agent tool contract so Dev B can start in parallel

### Decisions needing team approval before implementation
1. ADK running in-process on Cloud Run vs. managed Agent Engine (recommend: in-process)
2. ClickHouse MCP server vs. direct `clickhouse-connect` client for the agent's tools (recommend: real MCP server for stronger partner-track compliance, if time allows)
3. Crew/location constraints as static fields vs. full event streams for MVP (recommend: static fields)
4. SSE vs. WebSockets for realtime (recommend: SSE)
5. One unified `crew` table (with a role field) vs. separate crew/actors tables (recommend: unified)
6. Agent framing: one Investigation Agent + deterministic engines + one narration call, vs. a fuller multi-agent setup (recommend: the former, per Section 7)
7. Demo-recording strategy: live Gemini call during the recorded demo vs. relying on a rehearsed/cached run (needs a joint decision, not just a technical one)

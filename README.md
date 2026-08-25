# On-Set War Room

Production incident command center for the **Agentic Cinema / ClickHouse** partner track.

When **CAMERA-02** goes **DOWN**, the system ingests the event into ClickHouse Cloud, runs a **Google ADK** `SequentialAgent` pipeline (Monitor → Investigator → Impact → Narrator) whose FunctionTools wrap ClickHouse queries and deterministic risk/pivot engines, then surfaces an incident on the war-room dashboard — including affected Scenes **43 & 48** and a recommended pivot to Scene **47**.

## Architecture (MVP)

| Layer | Role |
|-------|------|
| FastAPI (`backend/`) | Ingestion, incidents API, ADK Runner bridge |
| ClickHouse Cloud | Productions, scenes, requirements, events, incidents, agent_actions |
| Google ADK (`google-adk`) | Mandatory multi-agent runtime (`SequentialAgent`) |
| Deterministic engines | `risk_engine`, `pivot_engine` exposed as ADK FunctionTools |
| React + Vite + Tailwind | OLED ops dashboard (`frontend/`) |
| Simulator | Canned scenarios (`camera_failure`, `actor_delay`, `weather_issue`) |

`GOOGLE_API_KEY` (or `GEMINI_API_KEY`) enables **live** ADK LLM turns. Without it, the same `google-adk` `SequentialAgent` tool choreography still runs against ClickHouse (scores/pivots stay deterministic). `/health/adk` reports `live_llm` and `mode`.

## Prerequisites

- Python 3.10+
- Node.js 20+
- ClickHouse Cloud credentials (not Docker)
- Google AI Studio / Gemini API key for ADK

## 1. Environment

```powershell
cd d:\on-war-room\on-set-war-room
copy .env.example .env
# Edit .env with ClickHouse Cloud + GOOGLE_API_KEY (never commit .env)
```

```
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-3.6-flash
```

## 2. ClickHouse schema + seed

```powershell
cd d:\on-war-room\on-set-war-room
python -m pip install -e backend
python scripts/apply_clickhouse.py --schema
python scripts/apply_clickhouse.py --seed
```

Midnight Protocol seed: CAMERA-02 → Scenes 43 & 48; Scene 47 is a valid pivot (no CAMERA-02, same soundstage as 43).

## 3. Backend

```powershell
cd d:\on-war-room\on-set-war-room\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health checks:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/health/clickhouse
curl.exe http://127.0.0.1:8000/health/adk
```

## 4. Frontend

```powershell
cd d:\on-war-room\on-set-war-room\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 for the **cinematic landing**. Open http://127.0.0.1:5173/war-room for the live ops dashboard. Vite proxies `/api` and `/health` to the API.

## 5. CAMERA-02 demo (end-to-end)

With the API running and `/health/adk` ok:

```powershell
cd d:\on-war-room\on-set-war-room
python simulator/event_generator.py --scenario camera_failure
```

Or via API:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/simulate/camera_failure
```

Then:

```powershell
curl.exe http://127.0.0.1:8000/api/incidents
python scripts/verify_mvp.py
```

Expect:

- `risk_level`: **HIGH**
- `affected_scenes`: **[43, 48]**
- `recommended_scene`: **47**
- Investigation `timeline` with ADK agents + FunctionTool steps

## Key API routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/events` | Ingest event (ADK investigates DOWN/DEGRADED) |
| POST | `/api/events/equipment` | Equipment alias |
| GET | `/api/incidents` | List incidents |
| GET | `/api/incidents/{id}` | Full incident + timeline + narrative |
| POST | `/api/agent/investigate` | Re-run ADK pipeline for an existing `event_id` |
| GET | `/api/agent/actions/{id}` | Tool/action rows from ClickHouse |
| GET | `/api/simulate/scenarios` | List canned scenarios |
| POST | `/api/simulate/{name}` | Ingest + ADK investigate scenario |
| GET | `/api/production/health` | Dashboard health aggregate |
| GET | `/health/adk` | ADK import + API key |

## Gaps / notes

- ADK is mandatory; investigation fails closed without a Google API key.
- MCP client is a stub; investigation tools use `clickhouse-connect` directly.
- Do not commit `.env` or secrets.

See [docs/implementation-plan.md](docs/implementation-plan.md) for the ADK-first delivery plan.

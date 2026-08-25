# On-Set War Room

Production incident command center for the **Agentic Cinema / ClickHouse** partner track.

When **CAMERA-02** goes **DOWN**, the system ingests the event into ClickHouse Cloud, runs a hybrid investigation (deterministic risk + pivot engines, optional Gemini narration), and surfaces an incident on the war-room dashboard — including affected Scenes **43 & 48** and a recommended pivot to Scene **47**.

## Architecture (MVP)

| Layer | Role |
|-------|------|
| FastAPI (`backend/`) | Ingestion, incidents API, agent orchestration |
| ClickHouse Cloud | Productions, scenes, requirements, events, incidents, agent_actions |
| Deterministic engines | `risk_engine`, `pivot_engine`, ClickHouse investigation tools |
| Optional Gemini | Narration only — never invents scenes or overrides scores |
| React + Vite + Tailwind | OLED ops dashboard (`frontend/`) |
| Simulator | Canned scenarios (`camera_failure`, `actor_delay`, `weather_issue`) |

If `GEMINI_API_KEY` / `GOOGLE_API_KEY` is missing, the full pipeline still works with a canned narrative template.

## Prerequisites

- Python 3.10+
- Node.js 20+
- ClickHouse Cloud credentials (not Docker)

## 1. Environment

```powershell
cd d:\on-war-room\on-set-war-room
copy .env.example .env
# Edit .env with ClickHouse Cloud values (never commit .env)
```

Optional Gemini:

```
GEMINI_API_KEY=...
# or GOOGLE_API_KEY=...
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
curl.exe http://127.0.0.1:8000/health/gemini
```

## 4. Frontend

```powershell
cd d:\on-war-room\on-set-war-room\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 for the **cinematic landing** (GSAP scroll + Framer Motion + Lenis). Open http://127.0.0.1:5173/war-room for the live ops dashboard. Vite proxies `/api` and `/health` to the API.

Hero media lives in `frontend/public/media/` (`hero.mp4`, `hero-poster.png`). Motion respects `prefers-reduced-motion`.

## 5. CAMERA-02 demo (end-to-end)

With the API running:

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
```

Expect:

- `risk_level`: **HIGH**
- `affected_scenes`: **[43, 48]**
- `recommended_scene`: **47**
- Investigation `timeline` with monitor → investigate → impact → pivot → narrate

Other scenarios:

```powershell
python simulator/event_generator.py --list
python simulator/event_generator.py --scenario actor_delay
python simulator/event_generator.py --scenario weather_issue
```

## Key API routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/events` | Ingest event (auto-investigates DOWN/DEGRADED) |
| POST | `/api/events/equipment` | Equipment alias |
| GET | `/api/incidents` | List incidents |
| GET | `/api/incidents/{id}` | Full incident + timeline + narrative |
| POST | `/api/agent/investigate` | Re-run pipeline for an existing `event_id` |
| GET | `/api/agent/actions/{id}` | Tool/action rows from ClickHouse |
| GET | `/api/simulate/scenarios` | List canned scenarios |
| POST | `/api/simulate/{name}` | Ingest + investigate scenario |
| GET | `/api/production/health` | Dashboard health aggregate |

## Design

OLED dark ops UI tokens live in `design-system/on-set-war-room/` (Fira Code / Fira Sans, green / red / amber on slate). Lucide icons only — no emoji icons.

## Gaps / notes

- Gemini narration requires an API key and optional `pip install -e "backend[gemini]"`.
- MCP client is a stub; investigation tools use `clickhouse-connect` directly.
- Do not commit `.env` or secrets.

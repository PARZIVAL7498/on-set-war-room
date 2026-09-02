# On-Set War Room

Agentic production incident command center for film sets. When **CAMERA-02** goes **DOWN** mid-shoot, the system ingests the event into **ClickHouse Cloud**, runs a **Google ADK** four-agent pipeline, scores risk with deterministic engines, ranks a schedule pivot, and surfaces everything on a cinematic ops dashboard.

Built for the **Google Cloud × ClickHouse (Agentic Cinema)** partner track.

---
## Demo outcome (Midnight Protocol seed)

| Signal | Expected value |
|--------|----------------|
| Failed resource | `CAMERA-02` |
| Affected scenes | **43**, **48** |
| Risk | **HIGH** (~80) |
| Recommended pivot | **Scene 47** |

Run the **camera_failure** scenario in the War Room UI or via API to verify.

---

## How it works

```text
┌─────────────────────────┐
│  React / Vite UI        │
│  /        landing page  │
│  /war-room  ops console │
└───────────┬─────────────┘
            │  /api  /health
┌───────────▼─────────────┐
│  FastAPI backend        │
│  Google ADK pipeline    │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  ClickHouse Cloud       │
│  events · scenes ·      │
│  incidents · traces     │
└─────────────────────────┘
```

### Event → incident flow

1. A resource status event is ingested (`CAMERA-02 DOWN`).
2. **Monitor agent** decides whether to investigate.
3. **Investigator agent** queries ClickHouse for affected scenes and requirements.
4. **Impact agent** calls the deterministic `risk_engine` (no invented scores).
5. **Narrator agent** calls `pivot_engine` and writes a grounded recommendation.
6. The orchestrator re-runs the same tools in Python so facts stay stable even if the LLM narrates differently.
7. An incident is stored in ClickHouse and shown in the War Room UI.

### The four agents

| # | Agent | Role |
|---|--------|------|
| 1 | `monitor_agent` | Gatekeeper — investigate or skip |
| 2 | `investigator_agent` | Gather ClickHouse evidence |
| 3 | `impact_agent` | Score risk via `risk_engine` |
| 4 | `narrator_agent` | Rank pivot via `pivot_engine` + narrate |

### ADK runtime modes

| Mode | When | Behavior |
|------|------|----------|
| `live` | `GOOGLE_API_KEY` set | Real Gemini LLM turns + tool calls |
| `tools_choreography` | No key, or LLM error | Same tool sequence without LLM |

Check `/health/adk` for current mode.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion, GSAP |
| Backend | FastAPI, Python 3.12, Google ADK, Gemini |
| Database | ClickHouse Cloud |

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Node.js 20+**
- **ClickHouse Cloud** account
- **Gemini API key** — optional but recommended for live LLM turns
---

## Local development

### 1. Environment

```bash
cp .env.example .env
```

Fill in `.env` (never commit it):

```env
CLICKHOUSE_HOST=your-service.region.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_DATABASE=on_set_war_room
CLICKHOUSE_SECURE=true

GOOGLE_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-3.6-flash
```

### 2. Install dependencies and apply ClickHouse

```bash
pip install -e backend
python scripts/apply_clickhouse.py --all
```

### 3. Run backend

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

| Surface | URL |
|---------|-----|
| Landing | http://127.0.0.1:5173/ |
| War Room | http://127.0.0.1:5173/war-room |
| API | http://127.0.0.1:8000 |
| API docs | http://127.0.0.1:8000/docs |

Vite proxies `/api` and `/health` to the backend during local development.

---

## Demo scenarios

### From the UI

Open `/war-room` and click a scenario button (**camera_failure**, **actor_delay**, **weather_issue**).

### From the CLI

```bash
python simulator/event_generator.py --list
python simulator/event_generator.py --scenario camera_failure
```

### From the API

```bash
curl -X POST http://127.0.0.1:8000/api/simulate/camera_failure
curl http://127.0.0.1:8000/api/incidents
```

### Verify MVP assertions

```bash
python scripts/verify_mvp.py
```

Checks: `HIGH` risk, scenes `[43, 48]`, pivot scene `47`, non-empty agent timeline.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/health/clickhouse` | ClickHouse connectivity |
| `GET` | `/health/adk` | ADK status and runtime mode |
| `POST` | `/api/events` | Ingest event; auto-investigate DOWN/DEGRADED |
| `POST` | `/api/events/equipment` | Equipment-shaped ingest alias |
| `GET` | `/api/incidents` | List incidents |
| `GET` | `/api/incidents/{id}` | Full incident detail |
| `POST` | `/api/agent/investigate` | Re-run pipeline for an event |
| `GET` | `/api/agent/actions/{id}` | Agent action rows |
| `GET` | `/api/agent/adk-status` | ADK health |
| `GET` | `/api/simulate/scenarios` | List demo scenarios |
| `POST` | `/api/simulate/{name}` | Run scenario end-to-end |
| `GET` | `/api/production/health` | Dashboard aggregate |

Interactive docs: `/docs` when the backend is running.

---

## Repository layout

```text
on-set-war-room/
├── backend/
│   ├── app/
│   │   ├── agents/          # ADK SequentialAgent, orchestrator, tools
│   │   ├── api/             # FastAPI routes
│   │   ├── integrations/    # ClickHouse client
│   │   ├── schemas/         # Pydantic models
│   │   └── services/        # event_service, risk_engine, pivot_engine
│   └── pyproject.toml
├── frontend/
│   └── src/                 # React pages and components
├── clickhouse/
│   ├── schema/              # DDL (apply with --schema)
│   └── seed/                # Demo data (apply with --seed)
├── simulator/
│   ├── scenarios/           # camera_failure, actor_delay, etc.
│   └── event_generator.py
├── scripts/
│   ├── apply_clickhouse.py
│   ├── verify_mvp.py
│   └── verify_clickhouse.py
└── .env.example
```

---

## ClickHouse data model

Database: `on_set_war_room`

| Table | Purpose |
|-------|---------|
| `productions` | Production metadata |
| `scenes` | Call sheet windows, locations, status |
| `scene_requirements` | Scene ↔ equipment/crew dependencies |
| `resource_status_events` | Live event ingest stream |
| `incidents` | Investigation outcomes, narrative, timeline |
| `agent_actions` | Per-step agent/tool observability |

Seed data is intentional: **CAMERA-02** is required by scenes **43** and **48**; scene **47** is a valid pivot that does not need CAMERA-02.

---

## Security

- Never commit `.env`, API keys, or ClickHouse passwords
- Rotate any credentials shared in chat or screenshots
- Agent tools query scoped ClickHouse data — no full-table dumps

---

## License

MIT (or add a `LICENSE` file before public submission).

"""ADK Runner bridge — execute war_room_pipeline for one event."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))
load_dotenv()

APP_NAME = "on_set_war_room"
_runner = None
_session_service = None


def get_api_key() -> str | None:
    key = (
        os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_GENAI_API_KEY", "").strip()
    )
    return key or None


def health() -> dict[str, Any]:
    key_ok = bool(get_api_key())
    try:
        import google.adk  # noqa: F401

        import_ok = True
        err = None
    except Exception as exc:  # noqa: BLE001
        import_ok = False
        err = str(exc)
    # ADK package is mandatory; live LLM needs a key. Tools choreography works without key.
    out: dict[str, Any] = {
        "ok": import_ok,
        "api_key_present": key_ok,
        "adk_import_ok": import_ok,
        "live_llm": key_ok and import_ok,
        "runtime": "google-adk",
        "mode": "live" if key_ok else "tools_choreography",
    }
    if err:
        out["error"] = err
        out["ok"] = False
    return out


def adk_available() -> bool:
    """True when google-adk imports (pipeline can run; live LLM optional)."""
    try:
        import google.adk  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _ensure_google_api_key_env() -> None:
    """ADK / genai client expect GOOGLE_API_KEY."""
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return
    alias = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_GENAI_API_KEY", "").strip()
    )
    if alias:
        os.environ["GOOGLE_API_KEY"] = alias


def get_runner():
    """Lazy singleton Runner + InMemorySessionService."""
    global _runner, _session_service
    if _runner is not None:
        return _runner

    _ensure_google_api_key_env()
    if not get_api_key():
        raise RuntimeError("GOOGLE_API_KEY / GEMINI_API_KEY required for ADK")

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    from app.agents.adk_app import root_agent

    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=_session_service,
    )
    return _runner


@dataclass
class AdkRunResult:
    narrative: str = ""
    author: str | None = None
    session_id: str = ""
    events_summary: list[dict[str, Any]] = field(default_factory=list)
    used_adk: bool = False


def _event_text(event: Any) -> str:
    content = getattr(event, "content", None)
    if content is None:
        return ""
    parts = getattr(content, "parts", None) or []
    chunks: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


async def _run_async(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str,
    notes: str = "",
) -> AdkRunResult:
    from google.genai import types as genai_types

    runner = get_runner()
    assert _session_service is not None

    user_id = "war-room-ops"
    session_id = f"evt-{event_id}-{uuid.uuid4().hex[:8]}"
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={
            "production_id": production_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "event_id": event_id,
        },
    )

    prompt = (
        f"Production incident event:\n"
        f"- production_id: {production_id}\n"
        f"- resource_type: {resource_type}\n"
        f"- resource_id: {resource_id}\n"
        f"- status: {status}\n"
        f"- event_id: {event_id}\n"
        f"- notes: {notes or '(none)'}\n"
        f"- utc_now: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Run the full war-room investigation pipeline using your tools."
    )
    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )

    result = AdkRunResult(session_id=session_id, used_adk=True)
    final_bits: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        author = getattr(event, "author", None) or getattr(event, "agent_name", None)
        text = _event_text(event)
        is_final = False
        if hasattr(event, "is_final_response") and callable(event.is_final_response):
            try:
                is_final = bool(event.is_final_response())
            except Exception:  # noqa: BLE001
                is_final = False

        result.events_summary.append(
            {
                "author": author,
                "is_final": is_final,
                "text_preview": (text[:240] if text else ""),
            }
        )
        if text and (is_final or author == "narrator_agent"):
            final_bits.append(text)
            result.author = author

    result.narrative = "\n\n".join(final_bits).strip()
    return result


def _run_tools_choreography(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str,
    notes: str = "",
) -> AdkRunResult:
    """Execute FunctionTools in SequentialAgent order without live LLM turns.

    Used when GOOGLE_API_KEY is absent so the ADK agent graph + tools still
    drive the demo. Prefer live Runner when a key is configured.
    """
    import json

    from app.agents import tools as war_tools
    from app.agents.adk_app import root_agent

    result = AdkRunResult(
        session_id=f"choreography-{event_id}-{uuid.uuid4().hex[:8]}",
        used_adk=True,
    )
    agent_names = [a.name for a in root_agent.sub_agents]
    result.events_summary.append(
        {
            "author": root_agent.name,
            "is_final": False,
            "text_preview": f"tools_choreography via {agent_names}",
        }
    )

    mon = war_tools.evaluate_event_risk(production_id, resource_type, resource_id, status)
    result.events_summary.append(
        {
            "author": "monitor_agent",
            "is_final": False,
            "text_preview": mon.get("reason", ""),
        }
    )
    if not mon.get("investigate"):
        result.narrative = f"SKIP: {mon.get('reason')}"
        return result

    findings = war_tools.investigate_resource_event(
        production_id, resource_type, resource_id, status, event_id, notes
    )
    scenes = [s.get("scene_number") for s in findings.get("affected_scenes", [])]
    result.events_summary.append(
        {
            "author": "investigator_agent",
            "is_final": False,
            "text_preview": f"Affected scenes: {scenes}",
        }
    )

    risk = war_tools.score_risk(json.dumps(findings))
    result.events_summary.append(
        {
            "author": "impact_agent",
            "is_final": False,
            "text_preview": f"Risk {risk.get('level')} ({risk.get('score')}/100)",
        }
    )

    pivots = war_tools.find_pivot_candidates(json.dumps(findings))
    top = pivots.get("top_scene")
    result.events_summary.append(
        {
            "author": "narrator_agent",
            "is_final": True,
            "text_preview": f"Pivot candidates={pivots.get('count')}; top={top}",
        }
    )

    scene_txt = ", ".join(f"Scene {n}" for n in scenes) or "none"
    pivot_txt = (
        f"Recommend moving Scene {top} ahead to keep the day productive."
        if top
        else "No valid pivot candidate passed hard constraints."
    )
    result.narrative = (
        f"{resource_id} is unavailable. ADK tools choreography "
        f"({root_agent.name}) found impact on {scene_txt}. "
        f"Risk {risk.get('level')} (score {risk.get('score')}/100). {pivot_txt}"
    )
    result.author = "narrator_agent"
    return result


def run_war_room_pipeline(
    *,
    production_id: str,
    resource_type: str,
    resource_id: str,
    status: str,
    event_id: str,
    notes: str = "",
) -> AdkRunResult:
    """Sync entry for FastAPI orchestrator (safe if a loop is already running)."""
    if not adk_available():
        raise RuntimeError("google-adk is required but could not be imported")

    if get_api_key():
        try:
            coro = _run_async(
                production_id=production_id,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                event_id=event_id,
                notes=notes,
            )
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(coro)

            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except Exception as exc:  # noqa: BLE001 — fall back so demo stays green
            fallback = _run_tools_choreography(
                production_id=production_id,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                event_id=event_id,
                notes=notes,
            )
            fallback.events_summary.insert(
                0,
                {
                    "author": "war_room_pipeline",
                    "is_final": False,
                    "text_preview": f"live LLM failed ({type(exc).__name__}); tools choreography used",
                },
            )
            if fallback.narrative:
                fallback.narrative = (
                    f"[Live ADK LLM unavailable: {exc}]\n\n{fallback.narrative}"
                )
            return fallback

    return _run_tools_choreography(
        production_id=production_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        event_id=event_id,
        notes=notes,
    )

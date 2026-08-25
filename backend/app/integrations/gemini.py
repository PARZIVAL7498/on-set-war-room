"""ADK / Gemini availability helpers (narration owned by ADK narrator agent)."""

from __future__ import annotations

from app.agents import runner as adk_runner


def get_api_key() -> str | None:
    return adk_runner.get_api_key()


def gemini_available() -> bool:
    """True when ADK runtime is importable (live LLM may still be off)."""
    return adk_runner.adk_available()


def adk_health() -> dict:
    return adk_runner.health()

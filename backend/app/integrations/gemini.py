"""Gemini / Google GenAI narration helpers (optional).

Deterministic engines own scores and scene picks. Gemini only narrates evidence.
If GEMINI_API_KEY / GOOGLE_API_KEY is missing, callers use canned templates.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))
load_dotenv()


@lru_cache(maxsize=1)
def get_api_key() -> str | None:
    key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GOOGLE_GENAI_API_KEY", "").strip()
    )
    return key or None


def gemini_available() -> bool:
    return get_api_key() is not None


def narrate_pivot(
    *,
    resource_id: str,
    risk_level: str,
    risk_score: int,
    affected_scenes: list[int],
    pivot_scene: int | None,
    pivot_title: str | None,
    factors: list[str],
    reasons: list[str],
) -> tuple[str, bool]:
    """Return (narrative, used_gemini). Never invents scene numbers."""
    template = _canned_narrative(
        resource_id=resource_id,
        risk_level=risk_level,
        risk_score=risk_score,
        affected_scenes=affected_scenes,
        pivot_scene=pivot_scene,
        pivot_title=pivot_title,
        factors=factors,
        reasons=reasons,
    )

    api_key = get_api_key()
    if not api_key:
        return template, False

    prompt = f"""You are the On-Set War Room ops narrator for a film shoot.
Explain the incident clearly for producers. Use ONLY the facts below.
Do NOT invent scene numbers, equipment, or risk scores.
Do NOT change the recommended pivot scene.

Facts:
- Failed resource: {resource_id}
- Risk: {risk_level} (score {risk_score})
- Affected scenes: {affected_scenes}
- Recommended pivot scene: {pivot_scene} ({pivot_title or 'n/a'})
- Risk factors: {factors}
- Pivot reasons: {reasons}

Write 2-4 short paragraphs. Be operational and precise."""

    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
            or "gemini-2.0-flash",
            contents=prompt,
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return template, False
        # Guardrail: recommended scene must still appear if we have one.
        if pivot_scene and str(pivot_scene) not in text:
            text = f"{text}\n\nRecommended pivot remains Scene {pivot_scene} per deterministic ranking."
        return text, True
    except Exception:  # noqa: BLE001 — fall back silently for MVP demos
        return template, False


def _canned_narrative(
    *,
    resource_id: str,
    risk_level: str,
    risk_score: int,
    affected_scenes: list[int],
    pivot_scene: int | None,
    pivot_title: str | None,
    factors: list[str],
    reasons: list[str],
) -> str:
    scenes = ", ".join(f"Scene {n}" for n in affected_scenes) or "none"
    pivot_line = (
        f"Recommend moving Scene {pivot_scene}"
        + (f" ({pivot_title})" if pivot_title else "")
        + " ahead to keep the day productive."
        if pivot_scene
        else "No valid pivot candidate passed hard constraints."
    )
    factor_block = "; ".join(factors) if factors else "n/a"
    reason_block = "; ".join(reasons) if reasons else "n/a"
    return (
        f"{resource_id} is unavailable. Deterministic investigation found impact on {scenes}. "
        f"Risk assessed at {risk_level} (score {risk_score}/100). "
        f"Drivers: {factor_block}. "
        f"{pivot_line} "
        f"Pivot rationale: {reason_block}."
    )

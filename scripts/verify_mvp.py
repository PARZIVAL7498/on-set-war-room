#!/usr/bin/env python3
"""End-to-end MVP check: CAMERA-02 → HIGH risk, scenes 43/48, pivot 47.

Usage (API must be running):
  python scripts/verify_mvp.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"


def http_json(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> int:
    try:
        status, health = http_json("GET", "/health")
    except urllib.error.URLError as exc:
        print(f"API not reachable: {exc}", file=sys.stderr)
        return 1

    if not (isinstance(health, dict) and health.get("ok")):
        print(f"Health failed: {health}", file=sys.stderr)
        return 1

    print("POST /api/simulate/camera_failure ...")
    try:
        status, result = http_json("POST", "/api/simulate/camera_failure")
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        return 1

    incident = result.get("incident") if isinstance(result, dict) else None
    if not incident:
        print(f"No incident in response: {result}", file=sys.stderr)
        return 1

    incident_id = incident["incident_id"]
    # Brief poll in case list/detail lag
    time.sleep(0.5)
    _, detail = http_json("GET", f"/api/incidents/{incident_id}")

    affected = sorted(detail.get("affected_scenes") or [])
    risk = detail.get("risk_level")
    pivot = (detail.get("recommended_pivot") or {}).get("scene_number")

    print(f"incident_id={incident_id}")
    print(f"risk_level={risk} score={detail.get('risk_score')}")
    print(f"affected_scenes={affected}")
    print(f"recommended_pivot={pivot}")
    print(f"timeline_steps={len(detail.get('timeline') or [])}")
    print(f"adk_used={detail.get('gemini_used')}")

    timeline = detail.get("timeline") or []
    has_adk = any(
        (t.get("tool") == "google.adk.Runner")
        or str(t.get("agent", "")).endswith("_agent")
        or str(t.get("step", "")).startswith("adk")
        for t in timeline
    )

    ok = risk == "HIGH" and affected == [43, 48] and pivot == 47 and has_adk
    if not ok:
        print("ASSERTION FAILED", file=sys.stderr)
        if not has_adk:
            print("Missing ADK timeline steps", file=sys.stderr)
        return 1

    print("MVP verification passed (ADK pipeline).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

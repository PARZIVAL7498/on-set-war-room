#!/usr/bin/env python3
"""Post canned scenario events to the On-Set War Room API.

Usage (from repo root, with API running):
  python simulator/event_generator.py --scenario camera_failure
  python simulator/event_generator.py --list
  python simulator/event_generator.py --scenario camera_failure --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def post_event(base_url: str, payload: dict, *, investigate: bool = True) -> dict:
    qs = "investigate=true" if investigate else "investigate=false"
    url = base_url.rstrip("/") + f"/api/events?{qs}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def list_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate operational events")
    parser.add_argument(
        "--scenario",
        default="camera_failure",
        help="Scenario name without .json (default: camera_failure)",
    )
    parser.add_argument("--list", action="store_true", help="List scenario names")
    parser.add_argument(
        "--no-investigate",
        action="store_true",
        help="Ingest only — skip agent pipeline",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="FastAPI base URL",
    )
    args = parser.parse_args()

    if args.list:
        for name in list_scenarios():
            print(name)
        return 0

    scenario_path = SCENARIOS_DIR / f"{args.scenario}.json"
    if not scenario_path.exists():
        print(f"Scenario not found: {scenario_path}", file=sys.stderr)
        print(f"Available: {', '.join(list_scenarios())}", file=sys.stderr)
        return 1

    payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    print(f"Posting {args.scenario} → {args.base_url}/api/events")
    print(json.dumps(payload, indent=2))

    try:
        result = post_event(
            args.base_url,
            payload,
            investigate=not args.no_investigate,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print("Response:")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

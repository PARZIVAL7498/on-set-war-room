#!/usr/bin/env python3
"""Verify event ingestion: POST /api/events then poll ClickHouse for the row.

Usage (API must be running):
  python scripts/verify_ingestion.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services import event_service  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
SCENARIO = REPO_ROOT / "simulator" / "scenarios" / "camera_failure.json"


def main() -> int:
    payload = json.loads(SCENARIO.read_text(encoding="utf-8"))
    # Use a distinct note so this run is identifiable if needed
    payload["notes"] = f"{payload.get('notes', '')} [verify_ingestion]".strip()

    request = urllib.request.Request(
        BASE_URL + "/api/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"API not reachable at {BASE_URL}: {exc}", file=sys.stderr)
        return 1

    if status != 201:
        print(f"Expected 201, got {status}: {body}", file=sys.stderr)
        return 1

    event_id = UUID(body["event_id"])
    print(f"Ingested event_id={event_id}")

    row = event_service.fetch_event_by_id(event_id)
    if not row:
        print("Row not visible in ClickHouse after polling.", file=sys.stderr)
        return 1

    print(f"ClickHouse row: {row}")
    if row["resource_id"] != "CAMERA-02" or row["status"] != "DOWN":
        print("Unexpected resource/status", file=sys.stderr)
        return 1

    print("Ingestion verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

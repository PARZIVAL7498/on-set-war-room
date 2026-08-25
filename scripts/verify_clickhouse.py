#!/usr/bin/env python3
"""Verify Python can reach ClickHouse Cloud and the CAMERA-02 demo query works.

Usage (from repo root):
  python scripts/verify_clickhouse.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.integrations import clickhouse_client  # noqa: E402

CAMERA_QUERY = """
SELECT
    s.scene_number,
    s.title
FROM on_set_war_room.scene_requirements AS r
ANY INNER JOIN on_set_war_room.scenes AS s
    ON r.production_id = s.production_id
   AND r.scene_number = s.scene_number
WHERE r.requirement_type = 'equipment'
  AND r.requirement_id = 'CAMERA-02'
  AND s.status = 'scheduled'
ORDER BY s.scene_number
"""


def main() -> int:
    print("1) Config ...")
    cfg = clickhouse_client.get_config()
    print(f"   host={cfg['host']} port={cfg['port']} database={cfg['database']} secure={cfg['secure']}")

    print("2) Ping ...")
    ping = clickhouse_client.ping()
    print(f"   {ping}")
    if not ping.get("ok"):
        print("Ping failed.", file=sys.stderr)
        return 1

    print("3) Tables ...")
    tables = clickhouse_client.query(
        "SHOW TABLES FROM on_set_war_room"
    ).result_rows
    table_names = sorted(row[0] for row in tables)
    print(f"   {table_names}")
    expected = {
        "productions",
        "scenes",
        "scene_requirements",
        "resource_status_events",
    }
    missing = expected - set(table_names)
    if missing:
        print(f"Missing tables: {sorted(missing)}", file=sys.stderr)
        return 1

    print("4) CAMERA-02 affected scenes ...")
    rows = clickhouse_client.query(CAMERA_QUERY).result_rows
    scene_numbers = [row[0] for row in rows]
    print(f"   rows={rows}")
    if scene_numbers != [43, 48]:
        print(f"Expected scenes [43, 48], got {scene_numbers}", file=sys.stderr)
        return 1

    print("5) Scene 47 must not require CAMERA-02 ...")
    scene_47 = clickhouse_client.query(
        """
        SELECT count()
        FROM on_set_war_room.scene_requirements
        WHERE scene_number = 47
          AND requirement_type = 'equipment'
          AND requirement_id = 'CAMERA-02'
        """
    ).result_rows[0][0]
    if scene_47 != 0:
        print("Scene 47 unexpectedly requires CAMERA-02", file=sys.stderr)
        return 1
    print("   ok")

    print("Verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

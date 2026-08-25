#!/usr/bin/env python3
"""Apply ClickHouse SQL files from the repo to ClickHouse Cloud.

Usage (from repo root):
  python scripts/apply_clickhouse.py --schema
  python scripts/apply_clickhouse.py --seed
  python scripts/apply_clickhouse.py --all
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.integrations import clickhouse_client  # noqa: E402


def split_sql_statements(sql_text: str) -> list[str]:
    """Split a SQL file into executable statements (skips comment-only blocks)."""
    without_block = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    statements: list[str] = []
    for chunk in without_block.split(";"):
        lines = []
        for line in chunk.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            lines.append(line)
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


def apply_file(path: Path) -> int:
    print(f"Applying {path.relative_to(REPO_ROOT)} ...")
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    if not statements:
        print("  (no statements found)")
        return 0

    # Bootstrap against default so CREATE DATABASE works before target DB exists.
    client = clickhouse_client.get_client(database="default")
    for index, statement in enumerate(statements, start=1):
        preview = " ".join(statement.split())[:100]
        print(f"  [{index}/{len(statements)}] {preview}")
        client.command(statement)
    print(f"  done ({len(statements)} statements)")
    return len(statements)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply ClickHouse Cloud SQL from the repo")
    parser.add_argument("--schema", action="store_true", help="Apply clickhouse/schema/*.sql")
    parser.add_argument("--seed", action="store_true", help="Apply clickhouse/seed/*.sql")
    parser.add_argument("--all", action="store_true", help="Apply schema then seed")
    args = parser.parse_args()

    if not (args.schema or args.seed or args.all):
        parser.print_help()
        return 1

    try:
        clickhouse_client.get_config()
    except clickhouse_client.ClickHouseConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    total = 0
    if args.schema or args.all:
        schema_dir = REPO_ROOT / "clickhouse" / "schema"
        for path in sorted(schema_dir.glob("*.sql")):
            total += apply_file(path)

    if args.seed or args.all:
        # Reconnect to app database after schema create.
        clickhouse_client.close_client()
        seed_dir = REPO_ROOT / "clickhouse" / "seed"
        for path in sorted(seed_dir.glob("*.sql")):
            total += apply_file(path)

    print(f"Applied {total} statements to ClickHouse Cloud.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

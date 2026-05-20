"""
SPEC-008 — minimal forward-only SQL migration runner.

Applies every ``migrations/*.sql`` file in lexical order exactly once, tracking
applied files in ``pulse.schema_migrations``. Phase-1 simplicity over Alembic
(ADR-008 resourceful-OSS posture); migrations are plain idempotent SQL.

Run from 03_build/ with DATABASE_URL set (in .env):
    python scripts/db_migrate.py            # apply pending migrations
    python scripts/db_migrate.py --status   # list applied vs pending
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from core.db import database_url  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_TRACKING_DDL = """
CREATE SCHEMA IF NOT EXISTS pulse;
CREATE TABLE IF NOT EXISTS pulse.schema_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _applied(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM pulse.schema_migrations;")
        return {r[0] for r in cur.fetchall()}


def migrate(status_only: bool = False) -> int:
    """Apply pending migrations. Returns the number applied (0 in status mode)."""
    with psycopg.connect(database_url(), connect_timeout=10) as conn:
        conn.execute(_TRACKING_DDL)
        conn.commit()
        applied = _applied(conn)
        pending = [f for f in _migration_files() if f.name not in applied]

        if status_only:
            print(f"Applied ({len(applied)}): {sorted(applied)}")
            print(f"Pending ({len(pending)}): {[f.name for f in pending]}")
            return 0

        for f in pending:
            print(f"applying {f.name} ...")
            with conn.cursor() as cur:
                # SQL comes from a trusted local migrations/ file, not user input;
                # psycopg's LiteralString guard doesn't apply to file contents.
                cur.execute(f.read_text())  # type: ignore[arg-type]
                cur.execute(
                    "INSERT INTO pulse.schema_migrations (filename) VALUES (%s);", (f.name,)
                )
            conn.commit()
        print(f"done — {len(pending)} migration(s) applied.")
        return len(pending)


if __name__ == "__main__":
    migrate(status_only="--status" in sys.argv)

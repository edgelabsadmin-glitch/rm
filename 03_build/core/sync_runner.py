"""
On-demand "full refresh" — runs the same syncs the 12-hour background loops do
(Salesforce accounts + contacts, Chorus, Zoom), with DB-backed progress so the
admin Settings UI can poll a percentage.

Progress lives in the single-row pulse.sync_status table (id = 1), so any API
instance can read it regardless of which one is running the sync.
"""

from __future__ import annotations

import importlib
import logging
from datetime import UTC, datetime

from psycopg.rows import dict_row

from core.db import get_pool

log = logging.getLogger(__name__)

# (label, module, async-fn) for each phase, run in order. Imported lazily.
_PHASES: list[tuple[str, str, str]] = [
    ("Salesforce accounts", "core.salesforce.sync", "pull_and_upsert"),
    ("Salesforce contacts", "core.salesforce.sync", "pull_and_upsert_contacts"),
    ("Salesforce talent", "core.salesforce.sync", "pull_and_upsert_associates"),
    ("Chorus meetings", "core.chorus.sync", "pull_and_ingest"),
    ("Zoom meetings", "core.zoom.sync", "pull_and_ingest"),
]


async def _set(**fields: object) -> None:
    cols = ", ".join(f"{k} = %s" for k in fields)
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            f"UPDATE pulse.sync_status SET {cols} WHERE id = 1", list(fields.values())
        )
        await conn.commit()


async def get_status() -> dict:
    """Return the current sync status row as a JSON-friendly dict."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT state, percent, phase, detail, started_at, finished_at "
                "FROM pulse.sync_status WHERE id = 1"
            )
        ).fetchone()
    if not row:
        return {"state": "idle", "percent": 0, "phase": None, "detail": None}
    return {
        "state": row["state"],
        "percent": row["percent"],
        "phase": row["phase"],
        "detail": row["detail"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
    }


async def mark_started() -> None:
    """Flip status to running before the background task is scheduled, so the
    immediate response reflects the in-progress state (no idle/running race)."""
    await _set(
        state="running",
        percent=0,
        phase="Starting…",
        detail=None,
        started_at=datetime.now(UTC),
        finished_at=None,
    )


async def run_full_sync() -> None:
    """Run every phase in sequence, updating progress. A phase failure is recorded
    but does not abort the remaining phases (so one broken integration doesn't
    block the others). Final state is 'error' if any phase failed, else 'done'."""
    n = len(_PHASES)
    errors: list[str] = []
    for i, (label, module, fn_name) in enumerate(_PHASES):
        await _set(phase=label, percent=round((i / n) * 100))
        try:
            fn = getattr(importlib.import_module(module), fn_name)
            result = await fn()
            log.info("admin sync — %s done: %s", label, result)
        except Exception as exc:  # noqa: BLE001 — isolate per-phase failures
            log.error("admin sync — %s failed: %s", label, exc)
            errors.append(f"{label}: {exc}")
        await _set(percent=round(((i + 1) / n) * 100))

    if errors:
        await _set(
            state="error",
            percent=100,
            phase="Finished with errors",
            detail=" | ".join(errors)[:1000],
            finished_at=datetime.now(UTC),
        )
    else:
        await _set(
            state="done",
            percent=100,
            phase="Complete",
            detail=None,
            finished_at=datetime.now(UTC),
        )

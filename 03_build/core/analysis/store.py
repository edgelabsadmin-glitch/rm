"""
Snapshot store for entity matrices. Append-only with date: each analysis run adds
a row; the latest row per entity is the current state, the full series is history.
"""

from __future__ import annotations

import json
from typing import Any

from psycopg.rows import dict_row

from core.db import get_pool


async def save_snapshot(
    *,
    entity_type: str,
    entity_id: str,
    priority: str,
    color: str,
    score: float,
    fired_signals: list[dict],
    scores: dict | None = None,
    narrative: str | None = None,
    model_used: str | None = None,
    data_version: str | None = None,
    state: str = "ok",
) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO pulse.entity_matrices (
                entity_type, entity_id, priority, priority_color, priority_score,
                fired_signals, scores, narrative, model_used, data_version, state
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            [
                entity_type,
                entity_id,
                priority,
                color,
                score,
                json.dumps(fired_signals),
                json.dumps(scores or {}),
                narrative,
                model_used,
                data_version,
                state,
            ],
        )
        await conn.commit()


async def latest(entity_type: str, entity_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        return await (
            await cur.execute(
                "SELECT * FROM pulse.entity_matrices WHERE entity_type=%s AND entity_id=%s "
                "ORDER BY analyzed_at DESC LIMIT 1",
                [entity_type, entity_id],
            )
        ).fetchone()


async def history(entity_type: str, entity_id: str, limit: int = 30) -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        rows = await (
            await cur.execute(
                "SELECT analyzed_at, priority, priority_color, priority_score, state "
                "FROM pulse.entity_matrices WHERE entity_type=%s AND entity_id=%s "
                "ORDER BY analyzed_at DESC LIMIT %s",
                [entity_type, entity_id, limit],
            )
        ).fetchall()
    return list(rows)


async def latest_for_type(entity_type: str) -> list[dict]:
    """The latest matrix per entity of a type — compact fields for list coloring."""
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        rows = await (
            await cur.execute(
                "SELECT DISTINCT ON (entity_id) entity_id, priority, priority_color, "
                "priority_score, state, analyzed_at "
                "FROM pulse.entity_matrices WHERE entity_type=%s "
                "ORDER BY entity_id, analyzed_at DESC",
                [entity_type],
            )
        ).fetchall()
    return list(rows)


async def last_data_version(entity_type: str, entity_id: str) -> Any:
    row = await latest(entity_type, entity_id)
    return row["data_version"] if row else None


# ── analysis_status (single-row progress, mirrors pulse.sync_status) ───────────


async def set_status(**fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = %s" for k in fields)
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            f"UPDATE pulse.analysis_status SET {cols} WHERE id = 1", list(fields.values())
        )
        await conn.commit()


async def get_status() -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        row = await (
            await cur.execute(
                "SELECT state, percent, phase, detail, started_at, finished_at "
                "FROM pulse.analysis_status WHERE id = 1"
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

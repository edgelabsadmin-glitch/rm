"""
SPEC-008 — the five named queries over the event log (Design 04 §"Querying the
event log"). Repository functions rather than SQL views so they're unit-testable
and callable from the agent/CEO-View layers without raw SQL leaking upward.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, LiteralString
from uuid import UUID

from psycopg.rows import dict_row

from core.db import get_pool


async def _fetch(sql: LiteralString, params: dict[str, Any]) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def action_history(action_id: str | UUID) -> list[dict[str, Any]]:
    """Full lifecycle of a single action, oldest → newest."""
    return await _fetch(
        "SELECT event_type, occurred_at, actor, payload "
        "FROM pulse.events WHERE action_id = %(action_id)s "
        "ORDER BY occurred_at ASC;",
        {"action_id": str(action_id)},
    )


async def customer_recent_actions(customer_id: str, since: datetime) -> list[dict[str, Any]]:
    """Every action proposed/dispatched/outcome'd for a customer (Design 04 #2),
    newest first — i.e. both action-* and outcome-* events."""
    return await _fetch(
        "SELECT event_type, occurred_at, action_id, skill_id, payload "
        "FROM pulse.events "
        "WHERE customer_id = %(customer_id)s AND occurred_at >= %(since)s "
        "AND (event_type LIKE 'action-%%' OR event_type LIKE 'outcome-%%') "
        "ORDER BY occurred_at DESC;",
        {"customer_id": customer_id, "since": since},
    )


async def skill_funnel(skill_id: str, since: datetime) -> dict[str, int]:
    """suggested → approved → executed → outcome-recorded counts for a skill."""
    rows = await _fetch(
        "SELECT event_type, COUNT(*) AS n FROM pulse.events "
        "WHERE skill_id = %(skill_id)s AND occurred_at >= %(since)s "
        "GROUP BY event_type;",
        {"skill_id": skill_id, "since": since},
    )
    counts = {r["event_type"]: r["n"] for r in rows}
    return {
        "suggested": counts.get("action-suggested", 0),
        "approved": counts.get("action-approved", 0)
        + counts.get("action-modified-and-approved", 0),
        "executed": counts.get("action-executed", 0),
        "outcome_recorded": counts.get("outcome-recorded", 0),
    }


async def rm_throughput(rm_id: str, since: datetime) -> int:
    """Count of actions approved by this RM in the window (incl. modified-and-approved)."""
    rows = await _fetch(
        "SELECT COUNT(*) AS n FROM pulse.events "
        "WHERE rm_id = %(rm_id)s AND occurred_at >= %(since)s "
        "AND event_type IN ('action-approved', 'action-modified-and-approved');",
        {"rm_id": rm_id, "since": since},
    )
    return int(rows[0]["n"]) if rows else 0


async def recent_outcomes(since: datetime) -> list[dict[str, Any]]:
    """All recorded outcomes since `since` (CEO View aggregation source)."""
    return await _fetch(
        "SELECT occurred_at, action_id, customer_id, skill_id, payload "
        "FROM pulse.events "
        "WHERE event_type = 'outcome-recorded' AND occurred_at >= %(since)s "
        "ORDER BY occurred_at DESC;",
        {"since": since},
    )

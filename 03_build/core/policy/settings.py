"""
SPEC-009/010 — read/write the singleton pulse.settings row (kill switch +
auto-approve list). The kill-switch *semantics* live in core/policy/kill_switch.py;
this module is just the storage accessor.
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from core.db import get_pool

_DEFAULT_KILL_SWITCH: dict[str, Any] = {"global": False, "by_skill": {}, "by_customer": {}}
_DEFAULT_AUTO_APPROVE = ["recognition", "talent-care", "onboarding"]


async def get_settings() -> dict[str, Any]:
    """Return {kill_switch, auto_approve_skills}; defaults if the row is missing."""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT kill_switch, auto_approve_skills FROM pulse.settings WHERE id = 1;"
            )
            row = await cur.fetchone()
    if not row:
        return {"kill_switch": _DEFAULT_KILL_SWITCH, "auto_approve_skills": _DEFAULT_AUTO_APPROVE}
    return {
        "kill_switch": row["kill_switch"] or _DEFAULT_KILL_SWITCH,
        "auto_approve_skills": row["auto_approve_skills"] or _DEFAULT_AUTO_APPROVE,
    }


async def write_kill_switch(kill_switch: dict[str, Any]) -> None:
    """Persist the full kill-switch JSONB (upserting the singleton row)."""
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.settings (id, kill_switch) VALUES (1, %s) "
            "ON CONFLICT (id) DO UPDATE "
            "SET kill_switch = EXCLUDED.kill_switch, updated_at = NOW();",
            (Jsonb(kill_switch),),
        )

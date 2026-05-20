"""
SPEC-010 — kill switch (Design 04 §"Kill switch").

A single global boolean plus per-skill and per-customer overrides, stored in the
pulse.settings JSONB. When a scope is on, `policy_decide` returns `block` for
matching suggestions (no silent failure — the block itself is logged as a
`policy-decision` event, and every toggle emits `kill-switch-flipped`, §6 rule 14).

Shape: {"global": bool, "by_skill": {skill_id: bool}, "by_customer": {cust_id: bool}}.
"""

from __future__ import annotations

from typing import Any

from core.events import log
from core.policy.settings import get_settings, write_kill_switch


async def kill_switch_state() -> dict[str, Any]:
    """Return the current kill-switch JSONB."""
    return (await get_settings())["kill_switch"]


def _blocked(state: dict[str, Any], skill_id: str | None, customer_id: str | None) -> str | None:
    """Return the blocking scope string, or None if not blocked."""
    if state.get("global"):
        return "global"
    if skill_id and state.get("by_skill", {}).get(skill_id):
        return f"skill:{skill_id}"
    if customer_id and state.get("by_customer", {}).get(customer_id):
        return f"customer:{customer_id}"
    return None


async def blocked_scope(skill_id: str | None, customer_id: str | None) -> str | None:
    """Async convenience: the blocking scope for this skill/customer, or None."""
    return _blocked(await kill_switch_state(), skill_id, customer_id)


def _apply(state: dict[str, Any], scope: str, on: bool) -> dict[str, Any]:
    new = {
        "global": state.get("global", False),
        "by_skill": dict(state.get("by_skill", {})),
        "by_customer": dict(state.get("by_customer", {})),
    }
    if scope == "global":
        new["global"] = on
    elif scope.startswith("skill:"):
        new["by_skill"][scope[len("skill:") :]] = on
    elif scope.startswith("customer:"):
        new["by_customer"][scope[len("customer:") :]] = on
    else:
        raise ValueError(f"unknown kill-switch scope {scope!r} (use global | skill:X | customer:X)")
    return new


async def set_kill_switch(scope: str, on: bool, user_id: str) -> dict[str, Any]:
    """Toggle a kill-switch scope, persist it, and emit `kill-switch-flipped`."""
    new_state = _apply(await kill_switch_state(), scope, on)
    await write_kill_switch(new_state)
    await log.emit_kill_switch_flipped(user_id=user_id, scope=scope, on_or_off=on)
    return new_state

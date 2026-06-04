"""
SPEC-018 — skill execution context + suggested-action shape (Design 05 / 03).

`SkillContext` is what every skill's `run(ctx)` receives; `SuggestedAction` is
what it produces. `submit_action` is the shared path that records the proposal
(action-suggested event, Design 04) and routes it through the policy module
(spec 009) — every skill funnels through it so nothing dispatches un-audited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from graphiti_core import Graphiti

    from core.policy.types import PolicyDecision


@dataclass
class SkillContext:
    """Inputs handed to a skill's run(). `facts` carries any pre-evaluated signal
    state; `graphiti` is injectable for tests (else the shared instance)."""

    customer_id: str | None = None
    talent_id: str | None = None
    rm_id: str | None = None
    tier: str | None = None  # "SMB" | "Mid-Market" | "Enterprise"
    trigger: str = "manual"  # "calendar" | "rm-query" | "scheduled" | "manual"
    query: str | None = None
    as_of: datetime | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    graphiti: Graphiti | None = None


@dataclass
class SuggestedAction:
    """A proposed action a skill wants to take (Design 03 action card)."""

    skill_id: str
    action_type: str
    body: dict[str, Any]
    why_oneline: str
    urgency: str = "medium"  # low | medium | high
    why_detail: str | None = None  # the inline-tag-voice reasoning capture
    modifiable_fields: list[str] = field(default_factory=list)
    source_episodes: list[str] = field(default_factory=list)
    customer_id: str | None = None
    talent_id: str | None = None
    action_id: str = field(default_factory=lambda: str(uuid4()))


async def submit_action(ctx: SkillContext, action: SuggestedAction) -> PolicyDecision:
    """Record the proposal (action-suggested event) and run the policy module.

    Returns the PolicyDecision (auto-approve / require-human / block). The Action
    Queue (spec 031) and dispatch (spec 032) act on it downstream.
    """
    from core.events import log
    from core.policy.decide import policy_decide
    from core.policy.types import ActionSuggested

    await log.emit_action_suggested(
        action_card={"action_type": action.action_type, **action.body},
        why_oneline=action.why_oneline,
        urgency=action.urgency,
        why_detail=action.why_detail,
        source_episodes=action.source_episodes,
        modifiable_fields=action.modifiable_fields,
        action_id=action.action_id,
        customer_id=action.customer_id or ctx.customer_id,
        talent_id=action.talent_id or ctx.talent_id,
        rm_id=ctx.rm_id,  # owning RM — drives Action Queue scope (spec 031)
        skill_id=action.skill_id,
        tier_class=ctx.tier,
        reasoning_text=action.why_detail,
    )
    return await policy_decide(
        ActionSuggested(
            skill_id=action.skill_id,
            urgency=action.urgency,
            action_id=action.action_id,
            customer_id=action.customer_id or ctx.customer_id,
            tier_class=ctx.tier,
            action_card=action.body,
        )
    )


async def recently_actioned(
    skill_id: str,
    *,
    talent_id: str | None = None,
    customer_id: str | None = None,
    within_days: int = 30,
) -> bool:
    """True if this skill already proposed an action for this talent/customer
    within `within_days` (rate-limit, computed from the event log)."""
    from datetime import datetime, timedelta, timezone
    UTC = timezone.utc

    from core.db import get_pool

    cutoff = datetime.now(UTC) - timedelta(days=within_days)
    field, value = ("talent_id", talent_id) if talent_id else ("customer_id", customer_id)
    if not value:
        return False
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT 1 FROM pulse.events WHERE event_type = 'action-suggested' "
                f"AND skill_id = %s AND {field} = %s AND occurred_at >= %s LIMIT 1;",
                (skill_id, value, cutoff),
            )
            return await cur.fetchone() is not None

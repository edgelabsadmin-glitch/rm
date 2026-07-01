"""
SPEC-009 — the policy module (Design 04 §"Policy module").

`policy_decide(suggestion)` routes an action proposal to one of
{auto-approve, require-human, block} and emits a `policy-decision` event for the
audit trail. Phase-1 rules are pure Python with OPA-shape I/O (Q44).

Precedence (consolidates Design 04's listed rules; the most-restrictive outcome
wins so a misbehaving or killed path can never auto-fire):

    1. kill switch on (global / skill / customer)        -> block
    2. skill has >= 3 rejections in the last 14 days      -> require-human (+flag)
    3. customer tier == Enterprise                        -> require-human
    4. urgency == high                                    -> require-human
    5. skill == 'recognition'                             -> auto-approve (+1h)
    6. tier == SMB AND skill in the auto-approve list     -> auto-approve (+1h)
    7. otherwise                                          -> require-human

block > require-human > auto-approve; the auto-approve rules (5, 6) are reached
only when no restriction above applies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from langfuse.decorators import observe

from core.db import get_pool
from core.events import log
from core.policy.kill_switch import blocked_scope
from core.policy.settings import get_settings
from core.policy.types import ActionSuggested, PolicyDecision

REJECTION_THRESHOLD = 3
REJECTION_WINDOW_DAYS = 14
AUTO_APPROVE_DELAY_SECONDS = 3600  # +1h


def _evaluate(
    suggestion: ActionSuggested,
    *,
    kill_scope: str | None,
    rejections: int,
    auto_approve_skills: list[str],
) -> PolicyDecision:
    """Pure decision logic (no I/O) — unit-tested directly for every rule."""
    if kill_scope is not None:
        return PolicyDecision(
            decision="block",
            reason=f"kill_switch:{kill_scope}",
            thresholds_applied={"kill_switch_scope": kill_scope},
        )
    if rejections >= REJECTION_THRESHOLD:
        return PolicyDecision(
            decision="require-human",
            reason="skill_rejection_dampening",
            thresholds_applied={
                "rejections_14d": rejections,
                "threshold": REJECTION_THRESHOLD,
                "flag_for_tuning": True,
            },
        )
    if suggestion.tier_class == "Enterprise":
        return PolicyDecision(
            decision="require-human",
            reason="enterprise_tier",
            thresholds_applied={"tier_class": "Enterprise"},
        )
    if suggestion.urgency.lower() == "high":
        return PolicyDecision(
            decision="require-human",
            reason="high_urgency",
            thresholds_applied={"urgency": suggestion.urgency},
        )
    if suggestion.skill_id == "recognition":
        return PolicyDecision(
            decision="auto-approve",
            reason="recognition_low_blast_radius",
            thresholds_applied={"skill_id": suggestion.skill_id},
            delay_seconds=AUTO_APPROVE_DELAY_SECONDS,
        )
    if suggestion.tier_class == "SMB" and suggestion.skill_id in auto_approve_skills:
        return PolicyDecision(
            decision="auto-approve",
            reason="smb_auto_approve_list",
            thresholds_applied={"tier_class": "SMB", "auto_approve_skills": auto_approve_skills},
            delay_seconds=AUTO_APPROVE_DELAY_SECONDS,
        )
    return PolicyDecision(
        decision="require-human",
        reason="default_require_human",
        thresholds_applied={},
    )


async def _recent_rejection_count(skill_id: str) -> int:
    """Count action-rejected events for `skill_id` in the dampening window
    (computed from the event log — Design 04 stores no aggregations)."""
    from psycopg.rows import tuple_row

    cutoff = datetime.now(UTC) - timedelta(days=REJECTION_WINDOW_DAYS)
    pool = await get_pool()
    async with pool.connection() as conn:
        # Pin tuple_row: a pooled connection may carry a dict_row factory leaked by a
        # prior caller (some read endpoints set conn.row_factory), which would break
        # the positional row[0] below with KeyError.
        async with conn.cursor(row_factory=tuple_row) as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'action-rejected' AND skill_id = %s AND occurred_at >= %s;",
                (skill_id, cutoff),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0


@observe(name="policy_decide")
async def policy_decide(suggestion: ActionSuggested) -> PolicyDecision:
    """Decide routing for an action proposal and emit a `policy-decision` event."""
    kill_scope = await blocked_scope(suggestion.skill_id, suggestion.customer_id)
    rejections = await _recent_rejection_count(suggestion.skill_id)
    auto_approve_skills = (await get_settings())["auto_approve_skills"]

    decision = _evaluate(
        suggestion,
        kill_scope=kill_scope,
        rejections=rejections,
        auto_approve_skills=auto_approve_skills,
    )

    await log.emit_policy_decision(
        # action_id is a UUID column; fall back to a fresh id if the caller had none.
        action_id=suggestion.action_id or str(uuid4()),
        decision=decision.decision,
        thresholds_applied={"reason": decision.reason, **decision.thresholds_applied},
        skill_id=suggestion.skill_id,
        customer_id=suggestion.customer_id,
        tier_class=suggestion.tier_class,
        urgency=suggestion.urgency,
    )
    return decision

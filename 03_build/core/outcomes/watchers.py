"""
SPEC-033 — After-action outcome detection (Design 03 §"After-action outcome capture").

A dispatched action (`action-executed`) opens an outcome window. A daily sweep
(`run_outcome_watch`, invoked by the Activepieces `outcome_watch_daily` cron via
scripts/outcome_watch.py) looks for evidence the action landed:

  - email-reply   (channel=email)      → window 7d   (Q45)
  - task-completed(channel=sfdc_task)  → window 14d
  - ebr-detected  (meeting actions)    → window aligned to the meeting date (else 14d)

Found → `outcome-recorded`. Window closed with no evidence → `outcome-missing`.
Action types with no automated watcher get a manual "did this work?" follow-up
card emitted at window+7d (once).

Evidence checks are injected (`EvidenceCheckers`) so unit tests drive them and so
the real Chorus/SFDC/email-IMAP wiring stays swappable (Phase-1 defaults are
conservative: no false positives).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from langfuse.decorators import observe

# Outcome windows by expected outcome type (Q45). EBR aligns to the meeting date
# when known; this is the fallback when it isn't.
WINDOW_DAYS = {"email-reply": 7, "task-completed": 14, "ebr-detected": 14}
_MANUAL_FOLLOWUP_GRACE = timedelta(days=7)  # after window close, for unwatched types
_FOLLOWUP_SKILL = "outcome-watcher"

# action_type → ("expected outcome type", watched?). Mirrors the dispatch channel
# routing (spec 032) but expressed in outcome terms.
_OUTCOME_BY_ACTION_TYPE = {
    "renewal-touch": "email-reply",
    "talent-checkin": "email-reply",
    "recognition-note": "email-reply",
    "advocacy-touch": "email-reply",
    "expansion-intent-outreach": "email-reply",
    "meeting-brief": "ebr-detected",
    "escalation-routed": "task-completed",
    "coaching-handoff": "task-completed",
    "onboarding": "task-completed",
    "talent-checkin-sparse": "task-completed",
    "pattern-surface": "task-completed",
}


@dataclass
class OutcomePlan:
    expected_outcome_type: str | None  # None ⇒ unwatched (manual follow-up only)
    window_close_at: datetime
    watched: bool


def plan_for(
    action_type: str,
    dispatched_at: datetime,
    *,
    meeting_date: datetime | None = None,
) -> OutcomePlan:
    """Resolve the expected outcome type + window-close time for an executed action."""
    outcome_type = _OUTCOME_BY_ACTION_TYPE.get(action_type)
    if outcome_type == "ebr-detected" and meeting_date is not None:
        # EBR window closes the day after the meeting.
        return OutcomePlan(outcome_type, meeting_date + timedelta(days=1), watched=True)
    if outcome_type is None:
        # Unwatched: nominal 14d window, then a manual follow-up card after grace.
        return OutcomePlan(None, dispatched_at + timedelta(days=14), watched=False)
    return OutcomePlan(
        outcome_type, dispatched_at + timedelta(days=WINDOW_DAYS[outcome_type]), watched=True
    )


# Evidence checker signatures (all async, all return evidence or None/False).
EmailReplyCheck = Callable[[str | None, str | None, datetime], Awaitable[str | None]]
TaskCompletedCheck = Callable[[str | None], Awaitable[bool]]
EbrCheck = Callable[[str | None, datetime], Awaitable[str | None]]


async def _no_email_reply(external_id, customer_id, since) -> str | None:
    return None  # IMAP/Gmail reply scan not wired in Phase 1 (returns no evidence)


async def _no_task_completed(external_id) -> bool:
    return False


async def _no_ebr(customer_id, since) -> str | None:
    return None


@dataclass
class EvidenceCheckers:
    email_reply: EmailReplyCheck = _no_email_reply
    task_completed: TaskCompletedCheck = _no_task_completed
    ebr: EbrCheck = _no_ebr


async def _executed_awaiting_outcome(now: datetime) -> list[dict[str, Any]]:
    """action-executed events with no outcome-recorded/-missing yet."""
    from psycopg.rows import dict_row

    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT e.action_id, e.occurred_at, e.payload, e.customer_id "
                "FROM pulse.events e WHERE e.event_type = 'action-executed' "
                "AND NOT EXISTS (SELECT 1 FROM pulse.events o WHERE o.action_id = e.action_id "
                "AND o.event_type IN ('outcome-recorded', 'outcome-missing')) "
                "ORDER BY e.occurred_at ASC;"
            )
            return await cur.fetchall()


async def _followup_already_emitted(action_id: str) -> bool:
    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM pulse.events WHERE event_type = 'action-suggested' "
                "AND skill_id = %s AND payload->'action_card'->>'followup_for' = %s LIMIT 1;",
                (_FOLLOWUP_SKILL, action_id),
            )
            return await cur.fetchone() is not None


def _meeting_date(action_card: dict) -> datetime | None:
    raw = action_card.get("meeting_date") or action_card.get("proposed_time")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


@observe(name="outcome_watch")
async def run_outcome_watch(
    *, now: datetime | None = None, evidence: EvidenceCheckers | None = None
) -> dict[str, int]:
    """Sweep executed actions for outcome evidence; emit outcome-* events.

    Returns a small tally {recorded, missing, followup, pending} for the cron log.
    """
    from core.actions.queue import get_action
    from core.events import log

    now = now or datetime.now(UTC)
    evidence = evidence or EvidenceCheckers()
    tally = {"recorded": 0, "missing": 0, "followup": 0, "pending": 0}

    for row in await _executed_awaiting_outcome(now):
        action_id = str(row["action_id"])
        dispatched_at = row["occurred_at"]
        exec_payload = row["payload"] or {}
        external_id = exec_payload.get("external_id")

        rec = await get_action(action_id)
        action_card = rec.action_card if rec else {}
        action_type = action_card.get("action_type", "")
        customer_id = row["customer_id"] or (rec.customer_id if rec else None)
        plan = plan_for(action_type, dispatched_at, meeting_date=_meeting_date(action_card))

        # 1) Evidence check (watched types only).
        evidence_episode: str | None = None
        if plan.watched and plan.expected_outcome_type == "email-reply":
            evidence_episode = await evidence.email_reply(external_id, customer_id, dispatched_at)
        elif plan.watched and plan.expected_outcome_type == "task-completed":
            if await evidence.task_completed(external_id):
                evidence_episode = external_id
        elif plan.watched and plan.expected_outcome_type == "ebr-detected":
            evidence_episode = await evidence.ebr(customer_id, dispatched_at)

        if plan.watched and evidence_episode is not None:
            await log.emit_outcome_recorded(
                action_id=action_id,
                outcome_type=plan.expected_outcome_type or "unknown",
                evidence_episode_id=evidence_episode,
                customer_id=customer_id,
                rm_id=rec.rm_id if rec else None,
                skill_id=rec.skill_id if rec else None,
            )
            tally["recorded"] += 1
            continue

        # 2) Window still open → nothing yet.
        if now < plan.window_close_at:
            tally["pending"] += 1
            continue

        # 3) Window closed.
        if plan.watched:
            await log.emit_outcome_missing(
                action_id=action_id,
                outcome_window_closed_at=plan.window_close_at.isoformat(),
                expected_outcome_type=plan.expected_outcome_type or "unknown",
                customer_id=customer_id,
                rm_id=rec.rm_id if rec else None,
                skill_id=rec.skill_id if rec else None,
            )
            tally["missing"] += 1
        elif (
            now >= plan.window_close_at + _MANUAL_FOLLOWUP_GRACE
            and not await _followup_already_emitted(action_id)
        ):
            # Unwatched type: ask the RM to confirm, once, after the grace period.
            await log.emit_action_suggested(
                action_card={"action_type": "outcome-followup", "followup_for": action_id},
                why_oneline="Did this action land? Confirm the outcome.",
                urgency="low",
                action_id=str(__import__("uuid").uuid4()),
                customer_id=customer_id,
                rm_id=rec.rm_id if rec else None,
                skill_id=_FOLLOWUP_SKILL,
            )
            tally["followup"] += 1
        else:
            tally["pending"] += 1

    return tally

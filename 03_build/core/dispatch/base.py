"""
SPEC-032 — dispatch orchestration (Design 03 §"Approval flow").

`dispatch_approved_action(action_id)` is the single entry point the dispatch
consumer (Activepieces, on an `action-approved` / `action-modified-and-approved`
event — ADR-002) calls. It:

  1. Loads the action and ENFORCES §6 rule 6 — only an *approved* action may
     dispatch. A direct dispatch with no approval raises DispatchNotAllowed (the
     webhook surface maps that to 403). No SFDC/email side effect ever happens
     for an un-approved action.
  2. Routes to the channel handler (email / sfdc_task / calendar_hold).
  3. Retries with exponential backoff (3 attempts); on success emits
     `action-executed`, on terminal failure emits `dispatch-failed` AND
     dead-letters the action into `pulse.dispatch_failed`.

Handlers are injectable (email_transport / sf_runner) so unit tests verify call
shapes without real OAuth or the `sf` CLI.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from langfuse.decorators import observe

from core.actions.queue import ActionRecord, get_action

_APPROVED_STATES = {"approved", "modified-approved"}

# action_type → channel (Phase-1 default routing). Skills emit semantic
# action_types; an action_card may override with an explicit "channel" key.
_CHANNEL_BY_ACTION_TYPE = {
    "renewal-touch": "email",
    "meeting-brief": "email",
    "talent-checkin": "email",
    "talent-checkin-sparse": "sfdc_task",
    "recognition-note": "email",
    "advocacy-touch": "email",
    "expansion-intent-outreach": "email",
    "onboarding": "sfdc_task",
    "escalation-routed": "sfdc_task",
    "coaching-handoff": "sfdc_task",
    "pattern-surface": "sfdc_task",
}
_DEFAULT_CHANNEL = "sfdc_task"  # safe canonical Pulse→SFDC write path (§6 rule 6)


class DispatchNotAllowed(Exception):
    """The action is missing/un-approved — dispatch is refused (§6 rule 6)."""


@dataclass
class DispatchResult:
    handler: str
    ok: bool
    external_id: str | None = None
    error_class: str | None = None
    error_message: str | None = None
    attempts: int = 1


def channel_for(action: ActionRecord) -> str:
    """Resolve the dispatch channel: explicit action_card['channel'] wins, else
    the action_type map, else the safe SFDC-Task default."""
    explicit = action.action_card.get("channel")
    if explicit in {"email", "sfdc_task", "calendar_hold"}:
        return explicit
    action_type = action.action_card.get("action_type", "")
    return _CHANNEL_BY_ACTION_TYPE.get(action_type, _DEFAULT_CHANNEL)


async def _record_dead_letter(
    action_id: str, handler: str, attempts: int, error_class: str, error_message: str
) -> None:
    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.dispatch_failed "
            "(action_id, handler, attempts, error_class, error_message) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (action_id) DO UPDATE SET "
            "handler = EXCLUDED.handler, attempts = EXCLUDED.attempts, "
            "error_class = EXCLUDED.error_class, error_message = EXCLUDED.error_message, "
            "failed_at = NOW(), resolved_at = NULL;",
            (action_id, handler, attempts, error_class, error_message[:1000]),
        )


@observe(name="dispatch_action")
async def dispatch_approved_action(
    action_id: str,
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    email_transport=None,
    sf_runner=None,
) -> DispatchResult:
    """Dispatch one approved action through its channel handler (with retry)."""
    rec = await get_action(action_id)
    if rec is None:
        raise DispatchNotAllowed(f"no such action {action_id}")
    if rec.status not in _APPROVED_STATES:
        # §6 rule 6: never dispatch (and never write to SFDC) for un-approved actions.
        raise DispatchNotAllowed(f"action {action_id} is not approved (status={rec.status})")

    # Late import keeps handler deps (subprocess/OAuth) out of the import graph
    # for callers that only need the queue.
    from core.dispatch import calendar_hold, email, sfdc_task

    channel = channel_for(rec)
    handler = {
        "email": lambda: email.send(rec, transport=email_transport),
        "calendar_hold": lambda: calendar_hold.send(rec, transport=email_transport),
        "sfdc_task": lambda: sfdc_task.create(rec, runner=sf_runner),
    }[channel]

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            external_id = await handler()
        except Exception as e:  # noqa: BLE001 — uniform retry/dead-letter path
            last_exc = e
            from core.events import log

            await log.emit_dispatch_failed(
                action_id=action_id,
                handler=channel,
                error_class=type(e).__name__,
                retry_attempt=attempt,
                customer_id=rec.customer_id,
                talent_id=rec.talent_id,
                rm_id=rec.rm_id,
                skill_id=rec.skill_id,
            )
            if attempt < max_attempts:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
            continue
        else:
            from core.events import log

            await log.emit_action_executed(
                action_id=action_id,
                handler=channel,
                external_id=external_id,
                customer_id=rec.customer_id,
                talent_id=rec.talent_id,
                rm_id=rec.rm_id,
                skill_id=rec.skill_id,
            )
            return DispatchResult(channel, ok=True, external_id=external_id, attempts=attempt)

    # Retry budget exhausted → dead-letter for operator follow-up.
    assert last_exc is not None
    await _record_dead_letter(
        action_id, channel, max_attempts, type(last_exc).__name__, str(last_exc)
    )
    return DispatchResult(
        channel,
        ok=False,
        error_class=type(last_exc).__name__,
        error_message=str(last_exc),
        attempts=max_attempts,
    )

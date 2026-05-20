"""
SPEC-031 — Action Queue lifecycle service (Design 03 approval flow).

The write side of the queue: approve / modify-and-approve / reject / expire. Each
operation guards on current state (only a *pending* action can be decided — a
second approve is a no-op-raise, not a double-dispatch), emits the lifecycle
event into the append-only log, and returns the refreshed record.

Dispatch (spec 032) is intentionally decoupled: approve/modify emit
`action-approved` / `action-modified-and-approved`, and the dispatch layer
consumes those events. This module never calls SFDC/email directly — keeping the
gated-write rule (§6 rule 6) and the audit trail honest.
"""

from __future__ import annotations

from core.actions.queue import ActionRecord, get_action


class ActionNotFound(Exception):
    """No action-suggested genesis for this action_id."""


class ActionNotPending(Exception):
    """The action already left the pending queue (decided/expired/dispatched)."""

    def __init__(self, status: str) -> None:
        super().__init__(f"action is not pending (status={status})")
        self.status = status


class NonModifiableField(Exception):
    """A modify diff touched a field the skill did not mark modifiable."""

    def __init__(self, fields: list[str]) -> None:
        super().__init__(f"fields not modifiable: {sorted(fields)}")
        self.fields = fields


async def _require_pending(action_id: str) -> ActionRecord:
    rec = await get_action(action_id)
    if rec is None:
        raise ActionNotFound(action_id)
    if rec.status != "pending":
        raise ActionNotPending(rec.status)
    return rec


async def approve_action(
    action_id: str, approver_id: str, *, decision_latency_ms: int | None = None
) -> ActionRecord:
    """Approve a pending action as-is. Emits action-approved (dispatch consumes it)."""
    rec = await _require_pending(action_id)
    from core.events import log

    await log.emit_action_approved(
        action_id=action_id,
        approver_id=approver_id,
        decision_latency_ms=decision_latency_ms,
        customer_id=rec.customer_id,
        talent_id=rec.talent_id,
        rm_id=rec.rm_id,
        skill_id=rec.skill_id,
        actor=f"user:{approver_id}",
    )
    refreshed = await get_action(action_id)
    assert refreshed is not None
    return refreshed


async def modify_action(
    action_id: str,
    approver_id: str,
    diff: dict,
    *,
    decision_latency_ms: int | None = None,
) -> ActionRecord:
    """Modify-and-approve. Only `modifiable_fields` may appear in `diff`; touching
    any other field raises NonModifiableField (→ 400 at the API)."""
    rec = await _require_pending(action_id)
    illegal = [k for k in diff if k not in rec.modifiable_fields]
    if illegal:
        raise NonModifiableField(illegal)

    from core.events import log

    await log.emit_action_modified_and_approved(
        action_id=action_id,
        approver_id=approver_id,
        diff=diff,
        decision_latency_ms=decision_latency_ms,
        customer_id=rec.customer_id,
        talent_id=rec.talent_id,
        rm_id=rec.rm_id,
        skill_id=rec.skill_id,
        actor=f"user:{approver_id}",
    )
    refreshed = await get_action(action_id)
    assert refreshed is not None
    return refreshed


async def reject_action(
    action_id: str, approver_id: str, reason_picker: str, free_text: str | None = None
) -> ActionRecord:
    """Reject a pending action with a reason (Design 03 reason picker)."""
    rec = await _require_pending(action_id)
    from core.events import log

    await log.emit_action_rejected(
        action_id=action_id,
        approver_id=approver_id,
        reason_picker=reason_picker,
        free_text=free_text,
        customer_id=rec.customer_id,
        talent_id=rec.talent_id,
        rm_id=rec.rm_id,
        skill_id=rec.skill_id,
        actor=f"user:{approver_id}",
    )
    refreshed = await get_action(action_id)
    assert refreshed is not None
    return refreshed


async def expire_action(action_id: str, expired_after_seconds: int) -> ActionRecord:
    """Expire a stale pending action (TTL sweep / system). Emits action-expired."""
    rec = await _require_pending(action_id)
    from core.events import log

    await log.emit_action_expired(
        action_id=action_id,
        expired_after_seconds=expired_after_seconds,
        customer_id=rec.customer_id,
        talent_id=rec.talent_id,
        rm_id=rec.rm_id,
        skill_id=rec.skill_id,
        actor="system",
    )
    refreshed = await get_action(action_id)
    assert refreshed is not None
    return refreshed

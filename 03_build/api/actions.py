"""
SPEC-031 — Action Queue API (Design 03).

GET  /actions               → pending actions in the caller's scope (ranked, paged, filtered).
GET  /actions/{id}          → full detail + lifecycle history (skill hidden from non-admins).
POST /actions/{id}/approve  → emit action-approved (dispatch — spec 032 — consumes it).
POST /actions/{id}/modify   → emit action-modified-and-approved (only modifiable_fields).
POST /actions/{id}/reject   → emit action-rejected (reason picker).
POST /actions/{id}/expire   → emit action-expired (TTL sweep / system).

RBAC is a placeholder header guard (X-User-Id / X-User-Role, plus X-Report-Ids
for managers) until the real Google-Workspace RBAC lands in spec 042. Scope rules
mirror Design 09: RM sees own; Manager sees self + direct reports; Admin sees all.
Every state-changing call is audited via the event it emits (Design 04).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from core.actions import queue, service

router = APIRouter(prefix="/actions", tags=["actions"])

_ROLES = {"rm", "manager", "admin"}


class Caller:
    """Resolved identity + scope (placeholder for spec 042 RBAC)."""

    def __init__(self, user_id: str, role: str, report_ids: list[str]) -> None:
        self.user_id = user_id
        self.role = role
        self.report_ids = report_ids

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def visible_rm_ids(self) -> list[str] | None:
        """RM ids the caller may see — None means unrestricted (admin)."""
        if self.role == "admin":
            return None
        if self.role == "manager":
            return [self.user_id, *self.report_ids]
        return [self.user_id]

    def can_act_on(self, action_rm_id: str | None) -> bool:
        """Can this caller approve/modify/reject the action? Same scope as visibility."""
        allowed = self.visible_rm_ids()
        if allowed is None:
            return True
        return action_rm_id in allowed


async def require_caller(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_report_ids: str | None = Header(default=None),
) -> Caller:
    """Placeholder auth: trust the gateway-set identity headers.

    TODO(spec 042): replace with Google-Workspace OAuth + RBAC chokepoint.
    """
    if not x_user_id or x_user_role not in _ROLES:
        raise HTTPException(status_code=403, detail="valid X-User-Id and X-User-Role required")
    reports = [r.strip() for r in (x_report_ids or "").split(",") if r.strip()]
    return Caller(x_user_id, x_user_role, reports)


class RejectBody(BaseModel):
    reason_picker: str
    free_text: str | None = None


class ModifyBody(BaseModel):
    diff: dict[str, Any]


class ExpireBody(BaseModel):
    expired_after_seconds: int = 0


@router.get("")
async def list_actions(
    caller: Annotated[Caller, Depends(require_caller)],
    tier: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    skill_id: str | None = Query(default=None),
    rm_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    records = await queue.list_pending_actions(
        visible_rm_ids=caller.visible_rm_ids(),
        tier_class=tier,
        customer_id=customer_id,
        skill_id=skill_id,
        rm_id=rm_id,
        limit=limit,
        offset=offset,
    )
    return {
        "actions": [r.public_dict(include_skill=caller.is_admin) for r in records],
        "count": len(records),
        "limit": limit,
        "offset": offset,
    }


async def _load_in_scope(action_id: str, caller: Caller) -> queue.ActionRecord:
    rec = await queue.get_action(action_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="action not found")
    if not caller.can_act_on(rec.rm_id):
        raise HTTPException(status_code=403, detail="action outside your scope")
    return rec


@router.get("/{action_id}")
async def get_action_detail(
    action_id: str, caller: Annotated[Caller, Depends(require_caller)]
) -> dict[str, Any]:
    rec = await _load_in_scope(action_id, caller)
    out = rec.public_dict(include_skill=caller.is_admin)
    out["history"] = rec.history
    return out


def _map_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.ActionNotFound):
        return HTTPException(status_code=404, detail="action not found")
    if isinstance(exc, service.ActionNotPending):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, service.NonModifiableField):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/{action_id}/approve")
async def approve(
    action_id: str, caller: Annotated[Caller, Depends(require_caller)]
) -> dict[str, Any]:
    await _load_in_scope(action_id, caller)
    try:
        rec = await service.approve_action(action_id, caller.user_id)
    except (service.ActionNotFound, service.ActionNotPending) as e:
        raise _map_service_error(e) from e
    return rec.public_dict(include_skill=caller.is_admin)


@router.post("/{action_id}/modify")
async def modify(
    action_id: str, body: ModifyBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict[str, Any]:
    await _load_in_scope(action_id, caller)
    try:
        rec = await service.modify_action(action_id, caller.user_id, body.diff)
    except (service.ActionNotFound, service.ActionNotPending, service.NonModifiableField) as e:
        raise _map_service_error(e) from e
    return rec.public_dict(include_skill=caller.is_admin)


@router.post("/{action_id}/reject")
async def reject(
    action_id: str, body: RejectBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict[str, Any]:
    await _load_in_scope(action_id, caller)
    try:
        rec = await service.reject_action(
            action_id, caller.user_id, body.reason_picker, body.free_text
        )
    except (service.ActionNotFound, service.ActionNotPending) as e:
        raise _map_service_error(e) from e
    return rec.public_dict(include_skill=caller.is_admin)


@router.post("/{action_id}/expire")
async def expire(
    action_id: str, body: ExpireBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict[str, Any]:
    await _load_in_scope(action_id, caller)
    try:
        rec = await service.expire_action(action_id, body.expired_after_seconds)
    except (service.ActionNotFound, service.ActionNotPending) as e:
        raise _map_service_error(e) from e
    return rec.public_dict(include_skill=caller.is_admin)

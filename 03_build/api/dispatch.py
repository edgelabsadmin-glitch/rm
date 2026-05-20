"""
SPEC-032 — internal dispatch trigger.

The seam the dispatch consumer (Activepieces, on an action-approved event —
ADR-002) calls to actually fire a channel handler. Guarded by the shared
internal token (same placeholder as the kill switch; real RBAC = spec 042/043).

§6 rule 6: dispatch is refused for any action that is not approved — a direct
dispatch attempt against a missing/un-approved action returns 403, so no SFDC
write or email send can bypass the Action Queue.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException

from core.dispatch.base import DispatchNotAllowed, dispatch_approved_action

router = APIRouter(prefix="/internal/dispatch", tags=["dispatch"])


async def require_internal_token(x_internal_token: str | None = Header(default=None)) -> str:
    expected = os.environ.get("PULSE_INTERNAL_API_TOKEN")
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=403, detail="internal token required")
    return "internal"


@router.post("/{action_id}")
async def trigger_dispatch(
    action_id: str, _: Annotated[str, Depends(require_internal_token)]
) -> dict[str, Any]:
    try:
        result = await dispatch_approved_action(action_id)
    except DispatchNotAllowed as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return {
        "handler": result.handler,
        "ok": result.ok,
        "external_id": result.external_id,
        "attempts": result.attempts,
        "error_class": result.error_class,
    }

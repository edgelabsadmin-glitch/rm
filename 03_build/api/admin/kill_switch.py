"""
SPEC-010 — admin kill-switch API (Design 04 §"Kill switch").

GET  /admin/kill-switch  → current state.
POST /admin/kill-switch  → toggle a scope (global / skill:X / customer:X).

Auth is a placeholder admin guard (shared token in the X-Admin-Token header,
compared to PULSE_INTERNAL_API_TOKEN) until the real Google-Workspace RBAC lands
in specs 042/043. A non-admin caller gets 403.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from core.policy import kill_switch

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(
    x_admin_token: str | None = Header(default=None),
) -> str:
    """Placeholder admin guard. Returns the caller id; raises 403 otherwise.

    TODO(spec 042/043): replace with Google-Workspace OAuth + RBAC chokepoint.
    """
    expected = os.environ.get("PULSE_INTERNAL_API_TOKEN")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=403, detail="admin token required")
    return "admin"


class KillSwitchToggle(BaseModel):
    scope: str = "global"  # "global" | "skill:<id>" | "customer:<id>"
    on: bool
    user_id: str = "admin"


@router.get("/kill-switch")
async def get_kill_switch(_: str = Depends(require_admin)) -> dict[str, Any]:
    return {"kill_switch": await kill_switch.kill_switch_state()}


@router.post("/kill-switch")
async def post_kill_switch(
    body: KillSwitchToggle, admin: str = Depends(require_admin)
) -> dict[str, Any]:
    try:
        new_state = await kill_switch.set_kill_switch(
            scope=body.scope, on=body.on, user_id=body.user_id or admin
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"kill_switch": new_state}

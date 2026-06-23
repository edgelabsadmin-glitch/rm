"""
Admin on-demand data sync API.

POST /admin/sync         → kick off a full refresh (the 12-hour syncs), non-blocking.
GET  /admin/sync/status  → current progress { state, percent, phase, detail }.

Admin-only: gated on the logged-in caller's role (X-User-Role = admin), the same
identity the Settings page is already protected by.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.actions import Caller, require_caller
from core.sync_runner import get_status, mark_started, run_full_sync

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin_user(
    caller: Annotated[Caller, Depends(require_caller)],
) -> Caller:
    if not caller.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return caller


@router.get("/sync/status")
async def sync_status(_: Annotated[Caller, Depends(require_admin_user)]) -> dict:
    return await get_status()


@router.post("/sync")
async def start_sync(_: Annotated[Caller, Depends(require_admin_user)]) -> dict:
    status = await get_status()
    if status.get("state") == "running":
        return status  # already in progress — return current rather than double-start
    await mark_started()
    asyncio.create_task(run_full_sync())
    return await get_status()

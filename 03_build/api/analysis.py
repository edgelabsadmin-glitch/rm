"""
Analysis agent API.

Admin:
  POST /admin/analysis/backfill  → kick a full (resumable) re-analysis, non-blocking.
  GET  /admin/analysis/status    → backfill/incremental progress { state, percent, … }.

Read (any authed caller):
  GET /accounts/{id}/matrix          → latest account matrix snapshot (or null).
  GET /accounts/{id}/matrix/history  → dated priority series for the account.
  GET /talent/{id}/matrix            → latest talent matrix snapshot (or null).

Admin endpoints reuse the same identity guard as the rest of the admin surface.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.actions import Caller, require_caller
from core.analysis import store
from core.analysis.agent import run_backfill

router = APIRouter(tags=["analysis"])


async def require_admin_user(caller: Annotated[Caller, Depends(require_caller)]) -> Caller:
    if not caller.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return caller


@router.get("/admin/analysis/status")
async def analysis_status(_: Annotated[Caller, Depends(require_admin_user)]) -> dict:
    return await store.get_status()


@router.post("/admin/analysis/backfill")
async def start_backfill(_: Annotated[Caller, Depends(require_admin_user)]) -> dict:
    status = await store.get_status()
    if status.get("state") == "running":
        return status  # already in progress — return current rather than double-start
    await store.set_status(state="running", percent=0, phase="Starting…", detail=None)
    asyncio.create_task(run_backfill())
    return await store.get_status()


@router.get("/accounts/{account_id}/matrix")
async def account_matrix(
    account_id: str, _: Annotated[Caller, Depends(require_caller)]
) -> dict | None:
    return await store.latest("account", account_id)


@router.get("/accounts/{account_id}/matrix/history")
async def account_matrix_history(
    account_id: str, _: Annotated[Caller, Depends(require_caller)]
) -> list[dict]:
    return await store.history("account", account_id)


@router.get("/talent/{talent_id}/matrix")
async def talent_matrix(
    talent_id: str, _: Annotated[Caller, Depends(require_caller)]
) -> dict | None:
    return await store.latest("talent", talent_id)

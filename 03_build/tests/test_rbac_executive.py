"""
SPEC-042 Step-6 — executive role on the Action Queue API.

The `executive` role is a valid identity (full org scope via visible_rm_ids → None) but is
BLOCKED from the Action Queue endpoints (spec §3 permission matrix; defense in depth matching
the front-end RoleGuard). These tests don't need Postgres: the 403 fires in the
require_queue_caller dependency BEFORE any DB access, and the unit checks touch only the
Caller model — so no `db` marker (they run in the default `pytest`).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.actions import Caller, require_caller, require_queue_caller

# --- Caller model unit checks (no app, no DB) -------------------------------------------


def test_caller_role_accepts_executive() -> None:
    caller = Caller("iffi-wahla", "executive", [])
    assert caller.role == "executive"


def test_visible_rm_ids_executive_returns_none() -> None:
    # Executive = full org scope, same sentinel as admin.
    assert Caller("iffi-wahla", "executive", []).visible_rm_ids() is None
    assert Caller("boss", "admin", []).visible_rm_ids() is None


# --- Dependency enforcement (403 fires before DB) ---------------------------------------
# Tests call the FastAPI dependencies directly instead of using TestClient(create_app()),
# which triggers the full lifespan (DB pool startup) and fails in CI without DATABASE_URL.


async def test_executive_blocked_from_list_actions() -> None:
    caller = await require_caller(
        x_user_id="iffi-wahla", x_user_role="executive", x_report_ids=None
    )
    with pytest.raises(HTTPException) as exc:
        await require_queue_caller(caller)
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "insufficient_role"
    assert exc.value.detail["user_role"] == "executive"


async def test_executive_blocked_returns_structured_detail() -> None:
    caller = await require_caller(
        x_user_id="iffi-wahla", x_user_role="executive", x_report_ids=None
    )
    with pytest.raises(HTTPException) as exc:
        await require_queue_caller(caller)
    assert exc.value.status_code == 403
    assert isinstance(exc.value.detail, dict)


async def test_executive_is_valid_identity_not_bad_role() -> None:
    # require_caller accepts executive (valid role); the block is the specific queue 403,
    # NOT the generic "valid X-User-Id and X-User-Role required" rejection.
    caller = await require_caller(
        x_user_id="iffi-wahla", x_user_role="executive", x_report_ids=None
    )
    assert caller.role == "executive"

    bogus_exc = None
    with pytest.raises(HTTPException) as exc:
        await require_caller(x_user_id="x", x_user_role="bogus", x_report_ids=None)
    bogus_exc = exc.value
    assert isinstance(bogus_exc.detail, str)


async def test_rm_role_passes_queue_guard() -> None:
    caller = await require_caller(x_user_id="sidra-zia", x_user_role="rm", x_report_ids=None)
    result = await require_queue_caller(caller)
    assert result.role == "rm"

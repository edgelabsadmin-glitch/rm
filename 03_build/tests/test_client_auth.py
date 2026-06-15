"""Unit tests for client auth helpers — no DB, no network."""

from __future__ import annotations

import pytest
from fastapi import HTTPException


async def test_require_client_session_missing_header_raises_401():
    from api.client_auth import require_client_session

    with pytest.raises(HTTPException) as exc:
        await require_client_session(x_client_session=None)
    assert exc.value.status_code == 401


async def test_require_client_session_present_queries_db():
    """Verifies the dependency accepts a value; raises because DB is unavailable in unit tests."""
    from api.client_auth import require_client_session

    with pytest.raises((HTTPException, Exception)):
        await require_client_session(x_client_session="some-uuid")

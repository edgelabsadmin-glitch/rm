"""
Unit tests for support chat helpers — no DB, no network.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


def test_truncate_title_long():
    from api.support import _truncate_title
    result = _truncate_title("a" * 100)
    assert result == "a" * 60


def test_truncate_title_short():
    from api.support import _truncate_title
    assert _truncate_title("Hello world") == "Hello world"


def test_truncate_title_strips_whitespace():
    from api.support import _truncate_title
    assert _truncate_title("  hello  ") == "hello"


def test_truncate_title_exactly_60():
    from api.support import _truncate_title
    assert _truncate_title("x" * 60) == "x" * 60


async def test_require_user_id_missing_raises_400():
    from api.support import require_user_id
    with pytest.raises(HTTPException) as exc:
        await require_user_id(x_user_id=None)
    assert exc.value.status_code == 400


async def test_require_user_id_present_returns_id():
    from api.support import require_user_id
    result = await require_user_id(x_user_id="user-123")
    assert result == "user-123"

"""
Google OAuth token management for per-user Gmail/Calendar polling.

get_valid_token(user_id) returns a fresh access token, refreshing via
the stored refresh_token when the current one is within 5 minutes of expiry.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import httpx
from psycopg.rows import dict_row

from core.db import get_pool

log = logging.getLogger(__name__)

_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EXPIRY_BUFFER = timedelta(minutes=5)


async def get_valid_token(user_id: str) -> str | None:
    """Return a valid access token for user_id, refreshing if needed.

    Returns None if the user has no stored session or no refresh token.
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT google_access_token, google_refresh_token, google_token_expiry "
                "FROM pulse.google_sessions WHERE user_id = %s",
                [user_id],
            )
        ).fetchone()

    if not row or not row["google_refresh_token"]:
        return None

    expiry = row["google_token_expiry"]
    now = datetime.now(UTC)

    # Token still valid with buffer
    if expiry and expiry > now + _EXPIRY_BUFFER:
        return row["google_access_token"]

    # Refresh
    return await _refresh_token(user_id, row["google_refresh_token"])


async def _refresh_token(user_id: str, refresh_token: str) -> str | None:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            _TOKEN_URL,
            data={
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if not res.is_success:
        log.warning("Token refresh failed for %s: %s", user_id, res.text)
        return None

    data = res.json()
    access_token: str = data["access_token"]
    expires_in: int = data.get("expires_in", 3600)
    expiry = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()

    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE pulse.google_sessions "
            "SET google_access_token = %s, google_token_expiry = %s, updated_at = NOW() "
            "WHERE user_id = %s",
            [access_token, expiry, user_id],
        )

    log.debug("Refreshed token for %s", user_id)
    return access_token


async def list_connected_users() -> list[dict]:
    """Return all users with a stored refresh token."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (
            await conn.execute(
                "SELECT user_id, email FROM pulse.google_sessions "
                "WHERE google_refresh_token IS NOT NULL"
            )
        ).fetchall()
    return list(rows)

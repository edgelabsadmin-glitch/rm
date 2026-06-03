"""
Google OAuth sign-in for Edge Pulse (Spec-043 placeholder — Phase 1B).

Flow:
  GET /auth/google/start    → redirect browser to Google consent screen
  GET /auth/google/callback → exchange code, verify email against whitelist,
                              save tokens to pulse.google_sessions,
                              redirect frontend with google_user_id param

Only emails listed in ALLOWED_EMAILS (mirror of DEMO_USERS in demo_characters.ts)
can authenticate. Everyone else gets an "unauthorized" redirect.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from core.db import get_pool
from psycopg.rows import dict_row

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["auth"])

_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

_SCOPES = " ".join([
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
])

# Mirror of DEMO_USERS[].email → id (from front/src/fixtures/demo_characters.ts).
# Add an entry here whenever a new user is added to DEMO_USERS.
ALLOWED_EMAILS: dict[str, str] = {
    "iffi.wahla@edgeonline.co":       "iffi-wahla",
    "eddy.chen@onedge.co":            "eddy-chen",
    "sarah.hooper@onedge.co":         "sarah-hooper",
    "muhammad.ibrahim@onedge.co":     "muhammad-ibrahim",
    "sidra.zia@onedge.co":            "sidra-zia",
    "sajjal.shaheedi@edgeonline.co":  "sajjal-shaheedi",
    "michael.vasquez@onedge.co":      "michael-vasquez",
    "yozeline.candia@onedge.co":      "yozeline-candia",
    "tanveer.shoukat@onedge.co":      "tanveer-shoukat",
    "muhammad.dawar@onedge.co":       "muhammad-dawar",
    "attiya.arooj@onedge.co":         "attiya-arooj",
    "ameer.ali@onedge.co":            "ameer-ali",
    "abbas.haider@onedge.co":         "abbas.haider",
    "zeeshan.hassan@onedge.co":       "zeeshan-hassan",
    "ghaeen.salam@onedge.co":         "ghaeen-salam",
    "akash.tahir@onedge.co":          "akash-tahir",
    "ammar.ashique@onedge.co":        "ammar-ashique",
    "amir.zaidi@onedge.co":           "amir-zaidi",
    "mubeen.sohail@onedge.co":        "mubeen-sohail",
    "sheryl.stephen@onedge.co":       "sheryl-stephen",
    "edgelabs.admin@onedge.co":       "pulse-admin",
    "afnanhashmi11223344@gmail.com":  "pulse-admin",
    "edgelabss@gmail.com":            "pulse-admin",
}


@router.get("/start")
async def google_start() -> RedirectResponse:
    """Redirect browser to Google OAuth consent screen."""
    params = urlencode({
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/callback")
async def google_callback(
    code: str = Query(default=None),
    error: str = Query(default=None),
) -> RedirectResponse:
    """Exchange code for tokens, verify email whitelist, save to DB, redirect frontend."""
    fail = f"{_FRONTEND_URL}/login?google=error"

    if error or not code:
        log.warning("OAuth callback: error=%s code_present=%s", error, bool(code))
        return RedirectResponse(fail)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": _CLIENT_ID,
                    "client_secret": _CLIENT_SECRET,
                    "redirect_uri": _REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if not token_res.is_success:
                log.error("Token exchange failed: %s %s", token_res.status_code, token_res.text)
                return RedirectResponse(fail)

            tokens = token_res.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = int(tokens.get("expires_in", 3600))

            if not access_token:
                log.error("No access_token in token response: %s", list(tokens.keys()))
                return RedirectResponse(fail)

            profile_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if not profile_res.is_success:
                log.error("Profile fetch failed: %s", profile_res.status_code)
                return RedirectResponse(fail)

            profile = profile_res.json()

        google_email = profile.get("email", "").lower().strip()
        user_id = ALLOWED_EMAILS.get(google_email)
        if not user_id:
            log.warning("Unauthorized Google login attempt: %s", google_email)
            return RedirectResponse(f"{_FRONTEND_URL}/login?google=unauthorized")

        expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        pool = await get_pool()
        async with pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO pulse.google_sessions
                    (user_id, email, google_access_token, google_refresh_token,
                     google_token_expiry, google_name, google_picture, connected_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    email                = EXCLUDED.email,
                    google_access_token  = EXCLUDED.google_access_token,
                    google_refresh_token = COALESCE(
                        EXCLUDED.google_refresh_token,
                        pulse.google_sessions.google_refresh_token
                    ),
                    google_token_expiry  = EXCLUDED.google_token_expiry,
                    google_name          = EXCLUDED.google_name,
                    google_picture       = EXCLUDED.google_picture,
                    updated_at           = NOW()
                """,
                [
                    user_id, google_email, access_token, refresh_token,
                    expiry, profile.get("name"), profile.get("picture"),
                ],
            )

        log.info("Google auth success for %s (%s)", user_id, google_email)
        return RedirectResponse(
            f"{_FRONTEND_URL}/login?google=success&google_user_id={user_id}"
        )

    except Exception as exc:
        log.exception("Unhandled error in Google callback: %s", exc)
        return RedirectResponse(fail)


@router.get("/status")
async def google_status(user_id: str = Query(...)) -> dict:
    """Returns the Google connection status for a given demo user ID."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT email, google_name, google_picture, connected_at "
                "FROM pulse.google_sessions WHERE user_id = %s",
                [user_id],
            )
        ).fetchone()

    if not row:
        return {"connected": False}

    return {
        "connected": True,
        "email": row["email"],
        "name": row["google_name"],
        "picture": row["google_picture"],
        "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
    }

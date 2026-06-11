"""
Client portal auth — email + OTP flow.

POST /client/auth/request-otp   → validate email, send OTP via SES
POST /client/auth/verify-otp    → validate OTP, create session, return session_id
POST /client/auth/logout        → delete session row
GET  /client/me                 → return client name, account, rm name

Auth: X-Client-Session header containing a session_id UUID.
All endpoints except request-otp / verify-otp require this header.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

from core.client.otp import generate_otp, hash_otp, verify_otp_hash
from core.db import get_pool

log = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])


# ── Session dependency ────────────────────────────────────────────────────────

async def require_client_session(
    x_client_session: str | None = Header(default=None),
) -> dict:
    if not x_client_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (await conn.execute(
            """
            SELECT session_id, contact_email, account_id, rm_owner_id,
                   rm_name, rm_pulse_user_id, client_name
            FROM pulse.client_sessions
            WHERE session_id = %s::uuid AND expires_at > now()
            """,
            [x_client_session],
        )).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return dict(row)


ClientSession = Annotated[dict, Depends(require_client_session)]


# ── Request models ────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    email: str


class OtpVerify(BaseModel):
    email: str
    otp: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/auth/request-otp")
async def request_otp(body: OtpRequest) -> dict:
    """Validate email against sf_contacts, send OTP. Always returns 200 to prevent enumeration."""
    from core.client.email import send_otp_email
    from core.llm.config import load_env
    load_env()

    email_lower = body.email.lower().strip()
    if not email_lower or "@" not in email_lower:
        raise HTTPException(status_code=422, detail="Invalid email address")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Check email exists in sf_contacts
        contact = await (await conn.execute(
            "SELECT contact_id FROM pulse.sf_contacts WHERE lower(email) = %s LIMIT 1",
            [email_lower],
        )).fetchone()

        if not contact:
            # Return 200 to prevent enumeration — no OTP is actually sent
            log.info("OTP request for unknown email: %s", email_lower)
            return {"sent": True}

        # Rate limit: max 3 OTPs per email per 10 minutes
        count_row = await (await conn.execute(
            """
            SELECT COUNT(*) AS n FROM pulse.client_otps
            WHERE email = %s AND created_at > now() - INTERVAL '10 minutes'
            """,
            [email_lower],
        )).fetchone()

        if count_row["n"] >= 3:
            raise HTTPException(status_code=429, detail="Too many requests. Try again in 10 minutes.")

        otp = generate_otp()
        otp_hash_val = hash_otp(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        await conn.execute(
            """
            INSERT INTO pulse.client_otps (email, otp_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            [email_lower, otp_hash_val, expires_at],
        )
        await conn.commit()

    try:
        await send_otp_email(email_lower, otp)
    except Exception as exc:
        log.error("SES send failed for %s: %s", email_lower, exc)
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again.")

    return {"sent": True}


@router.post("/auth/verify-otp")
async def verify_otp(body: OtpVerify) -> dict:
    """Validate OTP, create session, return session_id."""
    email_lower = body.email.lower().strip()

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Find most recent unused, unexpired OTP
        otp_row = await (await conn.execute(
            """
            SELECT id, otp_hash, attempt_count
            FROM pulse.client_otps
            WHERE email = %s AND used_at IS NULL AND expires_at > now()
            ORDER BY created_at DESC LIMIT 1
            """,
            [email_lower],
        )).fetchone()

        if not otp_row:
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        if otp_row["attempt_count"] >= 3:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

        # Increment attempt count before checking hash
        await conn.execute(
            "UPDATE pulse.client_otps SET attempt_count = attempt_count + 1 WHERE id = %s",
            [otp_row["id"]],
        )

        if not verify_otp_hash(body.otp.strip(), otp_row["otp_hash"]):
            await conn.commit()
            raise HTTPException(status_code=400, detail="Invalid code")

        # Mark OTP as used
        await conn.execute(
            "UPDATE pulse.client_otps SET used_at = now() WHERE id = %s",
            [otp_row["id"]],
        )

        # Resolve: contact → account → RM
        contact_row = await (await conn.execute(
            """
            SELECT c.name AS client_name, c.account_id,
                   a.owner_id AS rm_owner_id, a.rm_name
            FROM pulse.sf_contacts c
            JOIN pulse.sf_accounts a ON c.account_id = a.account_id
            WHERE lower(c.email) = %s
            LIMIT 1
            """,
            [email_lower],
        )).fetchone()

        if not contact_row:
            raise HTTPException(status_code=400, detail="Account not found for this email")

        # Resolve RM's Pulse user_id via name match in google_sessions
        gs_row = await (await conn.execute(
            """
            SELECT gs.user_id
            FROM pulse.google_sessions gs
            JOIN pulse.sf_accounts sa ON LOWER(gs.google_name) = LOWER(sa.rm_name)
            WHERE sa.account_id = %s
            LIMIT 1
            """,
            [contact_row["account_id"]],
        )).fetchone()

        rm_pulse_user_id = gs_row["user_id"] if gs_row else None

        # Create session (24 hours)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        session_row = await (await conn.execute(
            """
            INSERT INTO pulse.client_sessions
                (contact_email, account_id, rm_owner_id, rm_name, rm_pulse_user_id, client_name, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING session_id
            """,
            [
                email_lower,
                contact_row["account_id"],
                contact_row["rm_owner_id"],
                contact_row["rm_name"],
                rm_pulse_user_id,
                contact_row["client_name"] or email_lower,
                expires_at,
            ],
        )).fetchone()

        await conn.commit()

    return {"session_id": str(session_row["session_id"])}


@router.post("/auth/logout", status_code=204)
async def logout(session: ClientSession) -> None:
    """Delete the client session row."""
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM pulse.client_sessions WHERE session_id = %s::uuid",
            [str(session["session_id"])],
        )
        await conn.commit()


@router.get("/me")
async def client_me(session: ClientSession) -> dict:
    """Return client identity info for the frontend."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        acct = await (await conn.execute(
            "SELECT name FROM pulse.sf_accounts WHERE account_id = %s",
            [session["account_id"]],
        )).fetchone()

    return {
        "client_name": session["client_name"],
        "account_name": acct["name"] if acct else "Unknown",
        "rm_name": session["rm_name"],
        "contact_email": session["contact_email"],
    }

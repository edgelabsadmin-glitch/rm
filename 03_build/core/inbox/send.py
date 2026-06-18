"""
Send a threaded reply through Gmail as the RM.

build_reply_raw constructs the RFC-2822 MIME message (pure, unit-tested).
send_reply loads the inbox row, calls Gmail users.messages.send with the raw
message + threadId, and flips the row to 'sent'. A missing send scope (Gmail
403) surfaces as a 403 with detail 'reconnect_required'.
"""

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage

import httpx
from fastapi import HTTPException
from psycopg.rows import dict_row

from core.db import get_pool
from core.google.auth import get_valid_token

log = logging.getLogger(__name__)

_GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def build_reply_raw(
    *,
    to_email: str,
    from_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None,
) -> str:
    """Return a base64url-encoded RFC-2822 reply message (Gmail `raw` field)."""
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = from_email
    subj = subject.strip()
    if not subj.lower().startswith("re:"):
        subj = f"Re: {subj}"
    msg["Subject"] = subj
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def send_reply(rm_user_id: str, email_id: str, text: str) -> str:
    """Send `text` as a threaded reply to the given inbox email. Returns Gmail id.

    Raises HTTPException(404) if the row isn't found/owned, 403 'reconnect_required'
    if Gmail rejects for missing scope, 502 on other Gmail errors.
    """
    token = await get_valid_token(rm_user_id)
    if not token:
        raise HTTPException(status_code=403, detail="reconnect_required")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT gmail_thread_id, rfc_message_id, from_email, subject "
                "FROM pulse.inbox_emails WHERE email_id = %s::uuid AND rm_user_id = %s",
                [email_id, rm_user_id],
            )
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="email not found")

    pool2 = await get_pool()
    async with pool2.connection() as conn:
        conn.row_factory = dict_row
        sess = await (
            await conn.execute(
                "SELECT email FROM pulse.google_sessions WHERE user_id = %s",
                [rm_user_id],
            )
        ).fetchone()
    from_email = sess["email"] if sess else rm_user_id

    raw = build_reply_raw(
        to_email=row["from_email"],
        from_email=from_email,
        subject=row["subject"] or "",
        body=text,
        in_reply_to=row["rfc_message_id"],
    )

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            _GMAIL_SEND,
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw, "threadId": row["gmail_thread_id"]},
        )
    if res.status_code in (401, 403):
        log.warning("Gmail send rejected for %s: %s", rm_user_id, res.text)
        raise HTTPException(status_code=403, detail="reconnect_required")
    if not res.is_success:
        log.error("Gmail send error for %s: %s", rm_user_id, res.text)
        raise HTTPException(status_code=502, detail="send failed")

    sent_id = res.json().get("id", "")
    pool3 = await get_pool()
    async with pool3.connection() as conn:
        await conn.execute(
            "UPDATE pulse.inbox_emails SET reply_state='sent', sent_at=now(), "
            "sent_message_id=%s WHERE email_id=%s::uuid AND rm_user_id=%s",
            [sent_id, email_id, rm_user_id],
        )
        await conn.commit()
    return sent_id

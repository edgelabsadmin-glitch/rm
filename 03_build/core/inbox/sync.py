"""
Sync one RM's unreplied client emails into pulse.inbox_emails, drafting a reply
for each newly-ingested message.

Flow per RM:
  1. resolve the RM's google_name + email,
  2. list recent INBOX threads,
  3. for each thread: keep only those whose newest message is from a client
     (unreplied) on an account this RM owns,
  4. fetch the full body, upsert the row, and generate a reply for new rows.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr

import httpx
from psycopg.rows import dict_row

from core.db import get_pool
from core.google.account_matcher import build_email_index, match_accounts
from core.google.auth import get_valid_token
from core.inbox.reply import generate_reply
from core.inbox.threads import extract_plain_body, latest_inbound_message

log = logging.getLogger(__name__)

_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
_LOOKBACK_DAYS = 14
_DEFAULT_STYLE = (
    "Write professionally and warmly. Use a friendly but concise tone. "
    "Keep responses focused and helpful."
)


def owned_account_ids(entities: list[dict], account_index: dict, rm_name: str) -> list[str]:
    """Account ids from `entities` that resolve to an account owned by `rm_name`."""
    out: list[str] = []
    target = rm_name.lower().strip()
    for e in entities:
        aid = e.get("sfdc_id")
        if not aid:
            continue
        meta = account_index.get(aid)
        if meta and (meta.get("rm_name") or "").lower().strip() == target:
            out.append(aid)
    return out


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


async def _rm_identity(rm_user_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        return await (
            await conn.execute(
                "SELECT email, google_name FROM pulse.google_sessions WHERE user_id = %s",
                [rm_user_id],
            )
        ).fetchone()


async def _account_meta(account_ids: list[str]) -> dict:
    """Return {account_id: {rm_name, name, tier, risk}} for the given ids."""
    if not account_ids:
        return {}
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (
            await conn.execute(
                "SELECT account_id, rm_name, name, tier, risk FROM pulse.sf_accounts "
                "WHERE account_id = ANY(%s)",
                [account_ids],
            )
        ).fetchall()
    return {r["account_id"]: dict(r) for r in rows}


async def sync_inbox(rm_user_id: str) -> dict:
    """Sync unreplied client emails for one RM. Returns counts."""
    token = await get_valid_token(rm_user_id)
    if not token:
        return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 0}

    identity = await _rm_identity(rm_user_id)
    if not identity:
        return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 0}
    rm_email = (identity["email"] or "").lower()
    rm_name = identity["google_name"] or ""

    email_index = await build_email_index()
    headers = {"Authorization": f"Bearer {token}"}
    since = (datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    query = f"in:inbox after:{since}"

    threads = ingested = skipped = errors = 0

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(
            f"{_GMAIL}/threads", headers=headers, params={"q": query, "maxResults": 100}
        )
        if not res.is_success:
            log.warning("inbox: thread list failed for %s: %s", rm_user_id, res.text)
            return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 1}
        thread_stubs = res.json().get("threads", [])
        threads = len(thread_stubs)

        for stub in thread_stubs:
            try:
                tres = await client.get(
                    f"{_GMAIL}/threads/{stub['id']}", headers=headers, params={"format": "full"}
                )
                if not tres.is_success:
                    errors += 1
                    continue
                tmsgs = tres.json().get("messages", [])

                # Normalize messages for unreplied detection
                norm = []
                for m in tmsgs:
                    mh = m.get("payload", {}).get("headers", [])
                    _, from_addr = parseaddr(_header(mh, "From"))
                    norm.append(
                        {
                            "id": m["id"],
                            "from_email": from_addr.lower(),
                            "internal_date": int(m.get("internalDate", "0")),
                            "raw": m,
                        }
                    )

                newest = latest_inbound_message(norm, rm_email)
                if newest is None:
                    skipped += 1
                    continue

                msg = newest["raw"]
                mh = msg.get("payload", {}).get("headers", [])
                from_name, from_addr = parseaddr(_header(mh, "From"))
                entities = match_accounts([from_addr.lower()], email_index)
                meta_index = await _account_meta([e["sfdc_id"] for e in entities])
                owned = owned_account_ids(entities, meta_index, rm_name)
                if not owned:
                    skipped += 1
                    continue

                account_id = owned[0]
                body = extract_plain_body(msg.get("payload", {})) or msg.get("snippet", "")
                subject = _header(mh, "Subject") or None
                rfc_id = _header(mh, "Message-Id") or _header(mh, "Message-ID") or None
                received = datetime.fromtimestamp(int(msg.get("internalDate", "0")) / 1000, tz=UTC)

                inserted = await _upsert_email(
                    rm_user_id=rm_user_id,
                    gmail_message_id=msg["id"],
                    gmail_thread_id=stub["id"],
                    rfc_message_id=rfc_id,
                    account_id=account_id,
                    from_email=from_addr.lower(),
                    from_name=from_name or from_addr,
                    subject=subject,
                    body=body,
                    received_at=received,
                )
                if not inserted:
                    skipped += 1
                    continue

                # Generate a reply for the newly-inserted row
                acct = meta_index.get(account_id, {})
                style = await _load_style(rm_user_id)
                drafted = await generate_reply(
                    style_prompt=style,
                    account_name=acct.get("name", "your client"),
                    from_name=from_name or from_addr,
                    subject=subject or "",
                    body=body,
                )
                await _save_suggestion(
                    rm_user_id, msg["id"], drafted["reply"], drafted["rationale"]
                )
                ingested += 1
            except Exception as exc:
                log.error("inbox: thread %s error for %s: %s", stub.get("id"), rm_user_id, exc)
                errors += 1

    log.info(
        "inbox sync %s — threads=%d ingested=%d skipped=%d errors=%d",
        rm_user_id,
        threads,
        ingested,
        skipped,
        errors,
    )
    return {"threads": threads, "ingested": ingested, "skipped": skipped, "errors": errors}


async def _load_style(rm_user_id: str) -> str:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT style_prompt FROM pulse.rm_style_profiles WHERE rm_pulse_user_id = %s",
                [rm_user_id],
            )
        ).fetchone()
    return row["style_prompt"] if row else _DEFAULT_STYLE


async def _upsert_email(**kw) -> bool:
    """Insert an inbox row; return True if newly inserted, False if it existed."""
    pool = await get_pool()
    async with pool.connection() as conn:
        row = await (
            await conn.execute(
                """
                INSERT INTO pulse.inbox_emails (
                    rm_user_id, gmail_message_id, gmail_thread_id, rfc_message_id,
                    account_id, from_email, from_name, subject, body, received_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (rm_user_id, gmail_message_id) DO NOTHING
                RETURNING email_id
                """,
                [
                    kw["rm_user_id"],
                    kw["gmail_message_id"],
                    kw["gmail_thread_id"],
                    kw["rfc_message_id"],
                    kw["account_id"],
                    kw["from_email"],
                    kw["from_name"],
                    kw["subject"],
                    kw["body"],
                    kw["received_at"],
                ],
            )
        ).fetchone()
        await conn.commit()
    return row is not None


async def _save_suggestion(
    rm_user_id: str, gmail_message_id: str, reply: str, rationale: str
) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE pulse.inbox_emails SET suggested_reply=%s, reply_rationale=%s "
            "WHERE rm_user_id=%s AND gmail_message_id=%s",
            [reply, rationale, rm_user_id, gmail_message_id],
        )
        await conn.commit()

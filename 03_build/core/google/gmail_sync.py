"""
Gmail → pulse.episodes sync for a single user.

pull_and_ingest(user_id, email_index) fetches all threads sent/received
in the last 6 months, extracts header metadata, matches addresses to SF
accounts via the email index, and upserts into pulse.episodes.

Rate limits: Gmail allows 250 quota units/s per user. Each messages.get
costs 5 units; messages.list costs 1. We throttle with a 0.05s delay per
message fetch (≈ 20 msgs/s) which stays well within quota.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime

import httpx

from core.db import get_pool
from core.google.auth import get_valid_token
from core.google.account_matcher import match_accounts

log = logging.getLogger(__name__)

_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
_LOOKBACK_DAYS = 180  # 6 months
_PAGE_SIZE = 500
_FETCH_DELAY = 0.05  # seconds between message fetches

_UPSERT_SQL = """
INSERT INTO pulse.episodes (
    episode_id, dedup_key, source, source_event_id, source_url,
    source_timestamp, content_type, content, subject, description,
    candidate_entities, tags, processing_state, ingested_at
) VALUES (
    %s, %s, 'gmail', %s, %s,
    %s, 'email', %s, %s, %s,
    %s, %s, 'received', NOW()
)
ON CONFLICT (dedup_key) DO NOTHING
"""


def _extract_addresses(header_value: str) -> list[str]:
    """Parse comma-separated RFC 2822 address list → list of email strings."""
    addrs = []
    for part in header_value.split(","):
        _, addr = parseaddr(part.strip())
        if addr and "@" in addr:
            addrs.append(addr.lower())
    return addrs


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


async def pull_and_ingest(
    user_id: str,
    email_index: dict[str, str],
) -> dict[str, int]:
    """Sync last 6 months of Gmail for user_id. Returns ingestion stats."""
    token = await get_valid_token(user_id)
    if not token:
        log.warning("Gmail sync skipped for %s — no valid token", user_id)
        return {"fetched": 0, "ingested": 0, "skipped": 0, "errors": 0}

    headers = {"Authorization": f"Bearer {token}"}
    since = (datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    query = f"after:{since}"

    fetched = ingested = skipped = errors = 0
    message_ids: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Page through message list
        page_token = None
        while True:
            params: dict = {"q": query, "maxResults": _PAGE_SIZE}
            if page_token:
                params["pageToken"] = page_token
            res = await client.get(f"{_GMAIL_BASE}/messages", headers=headers, params=params)
            if res.status_code == 401:
                log.warning("Gmail 401 for %s — token may be revoked", user_id)
                break
            if not res.is_success:
                log.error("Gmail list error for %s: %s", user_id, res.text)
                break
            data = res.json()
            for msg in data.get("messages", []):
                message_ids.append(msg["id"])
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        fetched = len(message_ids)
        log.info("Gmail sync for %s: %d messages to process", user_id, fetched)

        # Fetch each message and upsert
        pool = await get_pool()
        rows: list[tuple] = []

        for msg_id in message_ids:
            await asyncio.sleep(_FETCH_DELAY)
            try:
                msg_res = await client.get(
                    f"{_GMAIL_BASE}/messages/{msg_id}",
                    headers=headers,
                    params={"format": "metadata", "metadataHeaders": ["From", "To", "Cc", "Subject", "Date"]},
                )
                if not msg_res.is_success:
                    errors += 1
                    continue

                msg = msg_res.json()
                payload_headers = msg.get("payload", {}).get("headers", [])

                from_raw = _get_header(payload_headers, "From")
                to_raw = _get_header(payload_headers, "To")
                cc_raw = _get_header(payload_headers, "Cc")
                subject = _get_header(payload_headers, "Subject") or None
                date_raw = _get_header(payload_headers, "Date")

                all_addresses = (
                    _extract_addresses(from_raw)
                    + _extract_addresses(to_raw)
                    + _extract_addresses(cc_raw)
                )
                entities = match_accounts(all_addresses, email_index)

                # Skip emails with no account match — not client-facing
                if not entities:
                    skipped += 1
                    continue

                try:
                    ts = parsedate_to_datetime(date_raw) if date_raw else None
                except Exception:
                    ts = None

                dedup_key = f"gmail:{msg_id}"
                source_url = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
                snippet = msg.get("snippet", "")

                content = json.dumps({
                    "from": from_raw,
                    "to": to_raw,
                    "cc": cc_raw,
                    "snippet": snippet,
                    "gmail_labels": msg.get("labelIds", []),
                })

                rows.append((
                    str(uuid.uuid4()),
                    dedup_key,
                    msg_id,
                    source_url,
                    ts,
                    content,
                    subject,
                    snippet[:500] if snippet else None,
                    json.dumps(entities),
                    ["gmail", user_id],
                ))

                if len(rows) >= 200:
                    async with pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.executemany(_UPSERT_SQL, rows)
                        await conn.commit()
                    ingested += len(rows)
                    rows = []

            except Exception as exc:
                log.error("Gmail message %s error for %s: %s", msg_id, user_id, exc)
                errors += 1

        # Flush remaining
        if rows:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.executemany(_UPSERT_SQL, rows)
                    await conn.commit()
                ingested += len(rows)
            except Exception as exc:
                log.error("Gmail flush error for %s: %s", user_id, exc)
                errors += len(rows)

    log.info(
        "Gmail sync done for %s — fetched=%d ingested=%d skipped=%d errors=%d",
        user_id, fetched, ingested, skipped, errors,
    )

    # Trigger style profile analysis after sync (non-blocking background task)
    if ingested > 0:
        try:
            from core.llm.rm_style import analyze_rm_style
            asyncio.create_task(analyze_rm_style(user_id))
            log.info("rm_style: queued style analysis for %s", user_id)
        except Exception as exc:
            log.error("rm_style: failed to queue analysis for %s: %s", user_id, exc)

    return {"fetched": fetched, "ingested": ingested, "skipped": skipped, "errors": errors}

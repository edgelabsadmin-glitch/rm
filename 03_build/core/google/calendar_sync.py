"""
Google Calendar → pulse.episodes sync for a single user.

pull_and_ingest(user_id, email_index) fetches all calendar events in the
last 6 months, matches attendee emails to SF accounts, and upserts into
pulse.episodes with source='calendar'.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from core.db import get_pool
from core.google.auth import get_valid_token
from core.google.account_matcher import match_accounts

log = logging.getLogger(__name__)

_CAL_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_LOOKBACK_DAYS = 180
_PAGE_SIZE = 250

_UPSERT_SQL = """
INSERT INTO pulse.episodes (
    episode_id, dedup_key, source, source_event_id, source_url,
    source_timestamp, content_type, content, subject, description,
    candidate_entities, tags, processing_state, ingested_at
) VALUES (
    %s, %s, 'calendar', %s, %s,
    %s, 'meeting', %s, %s, %s,
    %s, %s, 'received', NOW()
)
ON CONFLICT (dedup_key) DO NOTHING
"""


def _parse_event_time(time_obj: dict) -> datetime | None:
    raw = time_obj.get("dateTime") or time_obj.get("date")
    if not raw:
        return None
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        # date-only event
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def pull_and_ingest(
    user_id: str,
    email_index: dict[str, str],
) -> dict[str, int]:
    """Sync last 6 months of Google Calendar events for user_id."""
    token = await get_valid_token(user_id)
    if not token:
        log.warning("Calendar sync skipped for %s — no valid token", user_id)
        return {"fetched": 0, "ingested": 0, "skipped": 0, "errors": 0}

    headers = {"Authorization": f"Bearer {token}"}
    time_min = (datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)).isoformat()

    fetched = ingested = skipped = errors = 0
    events: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        page_token = None
        while True:
            params: dict = {
                "timeMin": time_min,
                "maxResults": _PAGE_SIZE,
                "singleEvents": "true",
                "orderBy": "startTime",
            }
            if page_token:
                params["pageToken"] = page_token

            res = await client.get(_CAL_BASE, headers=headers, params=params)
            if res.status_code == 401:
                log.warning("Calendar 401 for %s — token may be revoked", user_id)
                break
            if not res.is_success:
                log.error("Calendar list error for %s: %s", user_id, res.text)
                break

            data = res.json()
            events.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            await asyncio.sleep(0.1)

    fetched = len(events)
    log.info("Calendar sync for %s: %d events to process", user_id, fetched)

    pool = await get_pool()
    rows: list[tuple] = []

    for event in events:
        try:
            event_id = event.get("id", "")
            attendees = event.get("attendees", [])
            attendee_emails = [a["email"] for a in attendees if a.get("email")]
            organizer_email = (event.get("organizer") or {}).get("email", "")
            if organizer_email:
                attendee_emails.append(organizer_email)

            entities = match_accounts(attendee_emails, email_index)
            if not entities:
                skipped += 1
                continue

            start_obj = event.get("start", {})
            ts = _parse_event_time(start_obj)

            summary = event.get("summary") or None
            description = event.get("description") or None
            html_link = event.get("htmlLink") or None

            duration_mins = None
            end_obj = event.get("end", {})
            end_ts = _parse_event_time(end_obj)
            if ts and end_ts:
                duration_mins = int((end_ts - ts).total_seconds() / 60)

            content = json.dumps({
                "attendees": attendee_emails,
                "organizer": organizer_email,
                "duration_mins": duration_mins,
                "status": event.get("status"),
                "location": event.get("location"),
                "conference_data": bool(event.get("conferenceData")),
            })

            dedup_key = f"gcal:{event_id}"
            rows.append((
                str(uuid.uuid4()),
                dedup_key,
                event_id,
                html_link,
                ts,
                content,
                summary,
                (description or "")[:500] or None,
                json.dumps(entities),
                ["calendar", user_id],
            ))

            if len(rows) >= 200:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.executemany(_UPSERT_SQL, rows)
                    await conn.commit()
                ingested += len(rows)
                rows = []

        except Exception as exc:
            log.error("Calendar event %s error for %s: %s", event.get("id"), user_id, exc)
            errors += 1

    if rows:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(_UPSERT_SQL, rows)
                await conn.commit()
            ingested += len(rows)
        except Exception as exc:
            log.error("Calendar flush error for %s: %s", user_id, exc)
            errors += len(rows)

    log.info(
        "Calendar sync done for %s — fetched=%d ingested=%d skipped=%d errors=%d",
        user_id, fetched, ingested, skipped, errors,
    )
    return {"fetched": fetched, "ingested": ingested, "skipped": skipped, "errors": errors}

"""
SPEC-014 — Calendar Signal Source Adapter (Google Calendar; Phase-1 default).

Detects customer meetings on RM calendars within the next 24h and emits one
`calendar.upcoming-customer-meeting` Episode per qualifying event. Attendee
emails are resolved to a Customer (SFDC Account.Id) by looking up the SFDC
Contact records already ingested into pulse.episodes by spec 012; an event with
no resolvable attendee still emits a low-urgency `unknown-attendee` Episode
(Q54). Meetings whose title looks like an EBR/QBR are tagged `ebr-candidate`
(Q55).

Provider is Google in Phase 1 (Q23/Q33); MS Graph is a later swap behind the
same adapter. Out of scope (Design 02): conflict detection, auto calendar holds,
past-meeting reconciliation.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from uuid import uuid4

import httpx

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import EntityRef, Episode, RawEvent

_GCAL_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_HTTP_TIMEOUT = 30.0
_LOOKAHEAD_HOURS = 24
_EBR_HINTS = ("ebr", "qbr", "quarterly review", "quarterly business review")
MEETING_PROVIDER = "google"


def _parse_start(event: dict) -> datetime | None:
    start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date")
    if not start:
        return None
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _within_lookahead(event: dict, now: datetime) -> bool:
    """True if the meeting starts in (now, now + 24h] — not past, not too far out."""
    start = _parse_start(event)
    if start is None:
        return False
    return now < start <= now + timedelta(hours=_LOOKAHEAD_HOURS)


def _is_ebr(event: dict) -> bool:
    title = (event.get("summary") or "").lower()
    return any(h in title for h in _EBR_HINTS)


def _attendee_emails(event: dict) -> list[str]:
    return [
        a["email"].lower()
        for a in (event.get("attendees") or [])
        if a.get("email") and not a.get("resource")
    ]


class CalendarAdapter(SignalSourceAdapter):
    SOURCE_NAME = "calendar"
    SUPPORTS_WEBHOOKS = True
    SUPPORTS_BACKFILL = False  # Phase 1: forward-looking only (Design 02)

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("GOOGLE_CALENDAR_TOKEN", "")

    # ── Google Calendar API ──────────────────────────────────────────────────
    async def _fetch_upcoming_events(self, time_min: datetime, time_max: datetime) -> list[dict]:
        params = {
            "timeMin": time_min.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "timeMax": time_max.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "singleEvents": "true",  # expand recurring series into instances
            "orderBy": "startTime",
        }
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(_GCAL_EVENTS_URL, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json().get("items", [])

    # ── attendee → Account resolution (via spec-012 Contact episodes) ─────────
    async def _resolve_attendees(self, emails: list[str]) -> list[EntityRef]:
        if not emails:
            return []
        from core.db import get_pool

        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT DISTINCT content->'fields'->>'AccountId' AS account_id "
                    "FROM pulse.episodes "
                    "WHERE source = 'salesforce' AND content->>'object_type' = 'Contact' "
                    "AND lower(content->'fields'->>'Email') = ANY(%s) "
                    "AND content->'fields'->>'AccountId' IS NOT NULL;",
                    (emails,),
                )
                rows = await cur.fetchall()
        return [{"type": "Customer", "sfdc_id": r[0]} for r in rows if r[0]]

    # ── Adapter contract ─────────────────────────────────────────────────────
    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        """Poll the next 24h of calendar events (the Activepieces cron path)."""
        now = datetime.now(UTC)
        items = await self._fetch_upcoming_events(now, now + timedelta(hours=_LOOKAHEAD_HOURS))
        events: list[RawEvent] = []
        for ev in items:
            if not _within_lookahead(ev, now):
                continue
            entities = await self._resolve_attendees(_attendee_emails(ev))
            events.append(self._raw(ev, entities))
        return events

    def _verify_signature(self, payload: dict, headers: dict) -> bool:
        secret = os.environ.get("GOOGLE_CALENDAR_WEBHOOK_TOKEN")
        if not secret:
            return True
        token = headers.get("X-Goog-Channel-Token") or headers.get("x-goog-channel-token") or ""
        return hmac.compare_digest(secret, token)

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """Activepieces posts a calendar event (the cron flow enriches the thin
        Google push into the event body). Validates the channel token."""
        if not self._verify_signature(payload, headers):
            raise ValueError("bad-signature")
        event = payload.get("event") or payload
        if not event.get("id"):
            raise ValueError("malformed calendar webhook: missing event id")
        entities = await self._resolve_attendees(_attendee_emails(event))
        return [self._raw(event, entities)]

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        return event  # calendar events arrive complete

    def normalize(self, raw: RawEvent) -> Episode:
        payload = raw.get("payload", {})
        ev: dict = payload["event"]
        entities: list[EntityRef] = payload.get("candidate_entities", [])
        event_id = ev.get("id", "")
        start = _parse_start(ev)

        tags = ["calendar", "upcoming-customer-meeting"]
        if _is_ebr(ev):
            tags.append("ebr-candidate")
        if not entities:
            tags.append("unknown-attendee")

        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=event_id,
            source_url=ev.get("htmlLink"),
            source_timestamp=start or datetime.now(UTC),
            content_type="json",
            content={
                "meeting_id": event_id,
                "attendees": _attendee_emails(ev),
                "start_time": start.isoformat() if start else None,
                "agenda": ev.get("summary") or "",
                "description": ev.get("description") or "",
                "meeting_provider": MEETING_PROVIDER,
            },
            subject=f"Upcoming: {ev.get('summary') or event_id}"[:120],
            description="Upcoming customer meeting (24h ahead)",
            candidate_entities=entities,
            tags=tags,
            ingested_at=datetime.now(UTC),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        ev = raw.get("payload", {}).get("event", {})
        return f"calendar:{ev.get('id', '')}:{ev.get('etag', '')}"

    # ── helper ───────────────────────────────────────────────────────────────
    def _raw(self, event: dict, entities: list[EntityRef]) -> RawEvent:
        return {
            "source": self.SOURCE_NAME,
            "source_event_id": event.get("id", ""),
            "source_url": event.get("htmlLink"),
            "payload": {"event": event, "candidate_entities": entities},
        }

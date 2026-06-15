"""
SPEC-014 unit tests — Calendar adapter (mocked Google Calendar API).

The attendee→Account resolution DB test is in tests/test_calendar_adapter_db.py
(marker `db`); the live Google Calendar test is gated on GOOGLE_CALENDAR_TOKEN.
"""

from datetime import UTC, datetime, timedelta

import pytest

from core.adapters.calendar import CalendarAdapter

NOW = datetime.now(UTC)


def _event(eid="ev-1", summary="Acrisure sync", start=None, etag="etag1", attendees=None):
    return {
        "id": eid,
        "etag": etag,
        "summary": summary,
        "htmlLink": "https://cal/x",
        "start": {"dateTime": (start or (NOW + timedelta(hours=3))).isoformat()},
        "attendees": attendees
        if attendees is not None
        else [{"email": "sarah@acrisure.com"}, {"email": "rm@onedge.co"}],
    }


def _raw(event, entities=None):
    return {
        "source": "calendar",
        "source_event_id": event["id"],
        "payload": {"event": event, "candidate_entities": entities or []},
    }


def test_dedup_key_includes_event_id_and_etag():
    a = CalendarAdapter()
    assert a.dedup_key(_raw(_event("ev-9", etag="W/abc"))) == "calendar:ev-9:W/abc"


def test_normalize_builds_json_episode_with_resolved_customer():
    a = CalendarAdapter()
    ents = [{"type": "Customer", "sfdc_id": "001ACRISURE"}]
    ep = a.normalize(_raw(_event(), entities=ents))
    assert ep["content_type"] == "json"
    assert ep["content"]["meeting_provider"] == "google"
    assert ep["content"]["attendees"] == ["sarah@acrisure.com", "rm@onedge.co"]
    assert ep["candidate_entities"] == ents
    assert ep["tags"] == ["calendar", "upcoming-customer-meeting"]


def test_normalize_unknown_attendee_tagged():
    ep = CalendarAdapter().normalize(_raw(_event(), entities=[]))
    assert "unknown-attendee" in ep["tags"]


@pytest.mark.parametrize("title", ["Acrisure EBR", "Q3 QBR", "Quarterly Review with DHR"])
def test_ebr_candidate_tagging(title):
    ep = CalendarAdapter().normalize(_raw(_event(summary=title), entities=[]))
    assert "ebr-candidate" in ep["tags"]


def test_non_ebr_not_tagged():
    ep = CalendarAdapter().normalize(_raw(_event(summary="Weekly standup"), entities=[]))
    assert "ebr-candidate" not in ep["tags"]


def test_24h_lookahead_filter():
    from core.adapters.calendar import _within_lookahead

    soon = {"start": {"dateTime": (NOW + timedelta(hours=3)).isoformat()}}
    far = {"start": {"dateTime": (NOW + timedelta(days=3)).isoformat()}}
    past = {"start": {"dateTime": (NOW - timedelta(hours=1)).isoformat()}}
    assert _within_lookahead(soon, NOW) is True
    assert _within_lookahead(far, NOW) is False
    assert _within_lookahead(past, NOW) is False


async def test_list_recent_events_filters_and_resolves(monkeypatch):
    a = CalendarAdapter(token="t")

    async def fake_fetch(time_min, time_max):
        return [
            _event("ev-soon", start=NOW + timedelta(hours=2)),
            _event("ev-far", start=NOW + timedelta(days=5)),  # filtered out
        ]

    async def fake_resolve(emails):
        return [{"type": "Customer", "sfdc_id": "001ACRISURE"}]

    monkeypatch.setattr(a, "_fetch_upcoming_events", fake_fetch)
    monkeypatch.setattr(a, "_resolve_attendees", fake_resolve)

    events = await a.list_recent_events(NOW)
    assert [e["source_event_id"] for e in events] == ["ev-soon"]
    assert events[0]["payload"]["candidate_entities"][0]["sfdc_id"] == "001ACRISURE"


async def test_receive_webhook_bad_channel_token(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_WEBHOOK_TOKEN", "secret-tok")
    with pytest.raises(ValueError, match="bad-signature"):
        await CalendarAdapter().receive_webhook(
            {"event": _event()}, {"X-Goog-Channel-Token": "wrong"}
        )


async def test_receive_webhook_good_channel_token(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_WEBHOOK_TOKEN", "secret-tok")

    async def fake_resolve(emails):
        return []

    a = CalendarAdapter()
    monkeypatch.setattr(a, "_resolve_attendees", fake_resolve)
    events = await a.receive_webhook({"event": _event()}, {"X-Goog-Channel-Token": "secret-tok"})
    assert events[0]["source_event_id"] == "ev-1"

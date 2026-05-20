"""
SPEC-013 unit tests — Chorus adapter (mocked API).

No live Chorus: _http_get is monkeypatched. The real-API ingest is gated behind
the `integration` marker + CHORUS_API_TOKEN.
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest

from core.adapters.chorus import ChorusAdapter, fuzz_score, strip_html

NOW = datetime.now(UTC)


def _eng(eid="eng-1", account="Acrisure", ts=None, **extra):
    e = {
        "engagement_id": eid,
        "account_name": account,
        "subject": "Acrisure QBR",
        "date_time": (ts if ts is not None else NOW.timestamp()),
        "meeting_summary": "<p>Client praised <b>medical coders</b>.</p>",
        "action_items": ["Send ramp-up plan", "Follow up on dental"],
        "participants": [{"type": "prospect", "name": "Sarah Chen"}],
    }
    e.update(extra)
    return e


def _raw(eng):
    return {
        "source": "chorus",
        "source_event_id": eng["engagement_id"],
        "payload": {"engagement": eng},
    }


# ── lifted helpers ───────────────────────────────────────────────────────────
def test_strip_html():
    assert strip_html("<p>Hi<br/>there &amp; you</p>") == "Hi\nthere & you"
    assert strip_html(None) == ""


def test_fuzz_score_token_set_and_containment():
    assert fuzz_score("acrisure llc west", "acrisure") >= 85
    assert fuzz_score("acrisure", "totally different co") < 50


# ── adapter ──────────────────────────────────────────────────────────────────
def test_dedup_key_format():
    assert ChorusAdapter().dedup_key(_raw(_eng("conv-9"))) == "chorus:conv:conv-9"


def test_normalize_composes_text_and_strips_html():
    ep = ChorusAdapter().normalize(_raw(_eng()))
    assert ep["content_type"] == "text"
    assert "medical coders" in ep["content"]
    assert "<b>" not in ep["content"]  # html stripped
    assert "Action items:" in ep["content"]
    assert "Sarah Chen" in ep["content"]
    assert ep["tags"] == ["chorus", "meeting"]


def test_normalize_fuzzy_account_join_binds_sfdc_id():
    idx = [{"id": "001ACRISURE", "name": "Acrisure"}, {"id": "001OTHER", "name": "Globex"}]
    ep = ChorusAdapter(account_index=idx).normalize(_raw(_eng(account="Acrisure LLC West")))
    assert ep["candidate_entities"] == [
        {"type": "Customer", "sfdc_id": "001ACRISURE", "name": "Acrisure"}
    ]


def test_normalize_no_confident_match_keeps_name_hint():
    idx = [{"id": "001OTHER", "name": "Globex Corporation"}]
    ep = ChorusAdapter(account_index=idx).normalize(_raw(_eng(account="Nonesuch Holdings")))
    assert ep["candidate_entities"] == [{"type": "Customer", "name": "Nonesuch Holdings"}]


async def test_receive_webhook_no_secret_accepts(monkeypatch):
    monkeypatch.delenv("CHORUS_WEBHOOK_SECRET", raising=False)
    events = await ChorusAdapter().receive_webhook({"engagement_id": "eng-1"}, {})
    assert events[0]["source_event_id"] == "eng-1"


async def test_receive_webhook_bad_signature_raises(monkeypatch):
    monkeypatch.setenv("CHORUS_WEBHOOK_SECRET", "s3cret")
    with pytest.raises(ValueError, match="bad-signature"):
        await ChorusAdapter().receive_webhook(
            {"engagement_id": "eng-1"}, {"X-Chorus-Signature": "nope"}
        )


async def test_receive_webhook_good_signature_passes(monkeypatch):
    monkeypatch.setenv("CHORUS_WEBHOOK_SECRET", "s3cret")
    payload = {"engagement_id": "eng-1"}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    events = await ChorusAdapter().receive_webhook(payload, {"X-Chorus-Signature": sig})
    assert events[0]["source_event_id"] == "eng-1"


async def test_fetch_full_hydrates_thin_event(monkeypatch):
    a = ChorusAdapter()
    thin = {"source": "chorus", "source_event_id": "eng-1", "payload": {"engagement": {}}}

    async def fake_get(url):
        assert url.endswith("/v3/engagements/eng-1")
        return {"engagement": _eng("eng-1")}

    monkeypatch.setattr(a, "_http_get", fake_get)
    full = await a.fetch_full(thin)
    assert full["payload"]["engagement"]["meeting_summary"]


async def test_fetch_full_passthrough_when_already_full():
    a = ChorusAdapter()
    raw = _raw(_eng())
    assert await a.fetch_full(raw) is raw  # already has summary → no fetch


async def test_list_recent_events_paginates_and_filters(monkeypatch):
    a = ChorusAdapter(token="t")
    old_ts = (NOW - timedelta(days=400)).timestamp()
    recent_ts = (NOW - timedelta(days=2)).timestamp()

    async def fake_get(url):
        if "continuation_key" not in url:
            return {
                "engagements": [
                    _eng("e1", ts=recent_ts),
                    _eng("e2", ts=recent_ts, no_show=True),  # dropped
                ],
                "continuation_key": "ck1",
            }
        return {"engagements": [_eng("e3", ts=old_ts)], "continuation_key": None}  # too old

    monkeypatch.setattr(a, "_http_get", fake_get)
    events = await a.list_recent_events(NOW - timedelta(days=30))
    ids = [e["source_event_id"] for e in events]
    assert ids == ["e1"]  # e2 no_show dropped, e3 older than window


@pytest.mark.integration
@pytest.mark.skipif(
    not __import__("os").environ.get("CHORUS_API_TOKEN"),
    reason="needs CHORUS_API_TOKEN for live Chorus ingest",
)
async def test_live_chorus_list():
    a = ChorusAdapter()
    events = await a.list_recent_events(NOW - timedelta(days=30), max_pages=1)
    assert isinstance(events, list)
    if events:
        ep = a.normalize(events[0])
        assert ep["content_type"] == "text"
        assert ep["dedup_key"].startswith("chorus:conv:")

"""
SPEC-011 unit tests — adapter ABC, Episode envelope, and ingest_raw orchestration.

No DB / no LLM: the DB-backed idempotency + real-Graphiti tests live in
tests/test_ingest_pipeline_db.py (markers `db` / `integration`).
"""

from datetime import datetime, timezone
UTC = timezone.utc
from uuid import uuid4

import pytest
from graphiti_core.nodes import EpisodeType

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import Episode, RawEvent
from core.ingest import pipeline

# Design 02 §"The Episode envelope" — the locked key set.
EXPECTED_EPISODE_KEYS = {
    "episode_id",
    "dedup_key",
    "source",
    "source_event_id",
    "source_url",
    "source_timestamp",
    "content_type",
    "content",
    "subject",
    "description",
    "candidate_entities",
    "tags",
    "ingested_at",
    "processing_state",
}


class FakeAdapter(SignalSourceAdapter):
    SOURCE_NAME = "fake"
    SUPPORTS_WEBHOOKS = True
    SUPPORTS_BACKFILL = True

    def __init__(self) -> None:
        self.fetched = False

    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        return []

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        return [{"source": self.SOURCE_NAME, "source_event_id": payload["id"], "payload": payload}]

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        self.fetched = True
        full = dict(event)
        full["payload"] = {**event.get("payload", {}), "body": "hydrated transcript"}
        return full  # type: ignore[return-value]

    def normalize(self, raw: RawEvent) -> Episode:
        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=str(raw.get("source_event_id", "")),
            source_url=None,
            source_timestamp=datetime(2026, 5, 5, tzinfo=UTC),
            content_type="text",
            content=raw.get("payload", {}).get("body", ""),
            subject="Acrisure EBR 2026-05-05",
            description="Quarterly business review",
            candidate_entities=[{"type": "Customer", "sfdc_id": "001ACRISURE"}],
            tags=["ebr"],
            ingested_at=datetime.now(UTC),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        return f"{self.SOURCE_NAME}:conv:{raw.get('source_event_id')}"


class IncompleteAdapter(SignalSourceAdapter):
    SOURCE_NAME = "incomplete"
    SUPPORTS_WEBHOOKS = False
    SUPPORTS_BACKFILL = False

    async def list_recent_events(self, since):  # missing the other 4 methods
        return []


def test_episode_envelope_keys_match_design_02():
    assert set(Episode.__annotations__) == EXPECTED_EPISODE_KEYS


def test_complete_adapter_instantiates():
    a = FakeAdapter()
    assert a.SOURCE_NAME == "fake"


def test_incomplete_adapter_cannot_instantiate():
    with pytest.raises(TypeError):
        IncompleteAdapter()  # type: ignore[abstract]


def test_dedup_key_is_deterministic_and_namespaced():
    a = FakeAdapter()
    raw: RawEvent = {"source": "fake", "source_event_id": "abc", "payload": {}}
    assert a.dedup_key(raw) == "fake:conv:abc"
    assert a.dedup_key(raw) == a.dedup_key(raw)  # deterministic


def test_normalize_is_pure_and_repeatable_shape():
    a = FakeAdapter()
    raw: RawEvent = {"source": "fake", "source_event_id": "abc", "payload": {"body": "hi"}}
    ep1 = a.normalize(raw)
    ep2 = a.normalize(raw)
    # Pure w.r.t. content/provenance (episode_id is a fresh uuid per call by design).
    assert ep1["content"] == ep2["content"] == "hi"
    assert ep1["dedup_key"] == ep2["dedup_key"] == "fake:conv:abc"


def test_episode_body_maps_content_type_to_episode_type():
    text_ep = {"content_type": "text", "content": "hello"}
    body, kind = pipeline._episode_body(text_ep)  # type: ignore[arg-type]
    assert body == "hello" and kind == EpisodeType.text

    json_ep = {"content_type": "json", "content": {"a": 1}}
    body, kind = pipeline._episode_body(json_ep)  # type: ignore[arg-type]
    assert kind == EpisodeType.json and '"a": 1' in body


def test_content_size():
    assert pipeline._content_size("hello") == 5
    assert pipeline._content_size({"a": 1}) == len('{"a": 1}')


async def test_ingest_raw_orchestration(monkeypatch):
    """ingest_raw: signal-received → fetch_full → normalize → run_episode,
    forcing the Episode's dedup_key to the adapter's deterministic key."""
    captured: dict = {}

    async def fake_emit_signal_received(**kwargs):
        captured["signal_received"] = kwargs

    async def fake_run_episode(episode, *, graphiti=None):
        captured["episode"] = episode
        return True

    monkeypatch.setattr(pipeline.log, "emit_signal_received", fake_emit_signal_received)
    monkeypatch.setattr(pipeline, "run_episode", fake_run_episode)

    adapter = FakeAdapter()
    raw: RawEvent = {"source": "fake", "source_event_id": "abc", "payload": {"id": "abc"}}
    result = await pipeline.ingest_raw(adapter, raw)

    assert result is True
    assert adapter.fetched is True  # fetch_full ran (hydration)
    assert captured["episode"]["dedup_key"] == "fake:conv:abc"  # forced to adapter key
    assert captured["episode"]["content"] == "hydrated transcript"  # from hydrated body
    assert captured["signal_received"]["source"] == "fake"

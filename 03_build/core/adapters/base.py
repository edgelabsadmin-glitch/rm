"""
SPEC-011 — the Signal Source Adapter contract (Design 02 §"The adapter
contract"). Every source (Chorus, Salesforce, Calendar, and future Zoom/Slack/…)
implements this one ABC; the workflow engine only validates signatures and
routes — the source-specific logic lives here in code, not in workflow nodes
(Design 02 / Decision 9).

Phase-1 concrete adapters are specs 012-015 in core/adapters/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from core.adapters.episode import Episode, RawEvent


class SignalSourceAdapter(ABC):
    """Five-method plug-in interface for ingesting a source's signals."""

    SOURCE_NAME: str  # e.g. "chorus", "salesforce", "calendar"
    SUPPORTS_WEBHOOKS: bool  # webhook-driven vs. poll-driven
    SUPPORTS_BACKFILL: bool  # can re-ingest historical events

    @abstractmethod
    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        """Poll path: raw events since `since`. Also used for webhook backfill
        on missed deliveries."""

    @abstractmethod
    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """Webhook path: validate signature, parse payload, return zero or more
        RawEvents. Raise on malformed/forged payloads."""

    @abstractmethod
    async def fetch_full(self, event: RawEvent) -> RawEvent:
        """Hydrate a thin event (e.g. a webhook notification) into a full event
        (e.g. the transcript text). Idempotent."""

    @abstractmethod
    def normalize(self, raw: RawEvent) -> Episode:
        """Convert source-shape into the canonical Episode envelope. Pure: no
        I/O, no side effects, deterministic for the same input."""

    @abstractmethod
    def dedup_key(self, raw: RawEvent) -> str:
        """Stable key for this event; two events with the same key are the same
        event. Format: f"{SOURCE_NAME}:{stable-source-id}"."""

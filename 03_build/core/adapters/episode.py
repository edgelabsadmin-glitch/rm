"""
SPEC-011 — the canonical Episode envelope + RawEvent (Design 02 §"The Episode
envelope"). Every Signal Source Adapter normalizes its source-shaped events into
an `Episode`; the ingest pipeline (core/ingest/pipeline.py) is the only writer of
Episodes into the memory layer and the pulse.episodes audit table.

`Episode` is a TypedDict matching Design 02 verbatim. `content` stays in source
shape (text-as-text, json-as-dict) — Graphiti's extractor handles both.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict
from uuid import UUID


class EntityRef(TypedDict, total=False):
    """A source-known entity hint, pre-filled by the adapter to save the LLM work."""

    type: str  # "Customer" | "Talent" | "RM" | "Contact" | "Case" | ...
    sfdc_id: str  # canonical Salesforce Id when known
    name: str


class RawEvent(TypedDict, total=False):
    """A source-shaped event as returned by an adapter's poll/webhook path.

    Deliberately loose: each adapter knows its own source's shape. `payload`
    holds the raw source object; the typed fields are convenience provenance.
    """

    source: str
    source_event_id: str
    source_url: str | None
    source_timestamp: datetime
    payload: dict


class Episode(TypedDict):
    """Canonical normalized signal (Design 02 §"The Episode envelope")."""

    # Identity
    episode_id: UUID
    dedup_key: str

    # Provenance
    source: str
    source_event_id: str
    source_url: str | None
    source_timestamp: datetime

    # Content
    content_type: Literal["text", "json", "structured"]
    content: str | dict
    subject: str
    description: str

    # Routing hints (pre-computed by adapter)
    candidate_entities: list[EntityRef]
    tags: list[str]

    # Pulse-internal
    ingested_at: datetime
    processing_state: Literal["received", "normalized", "ingested", "failed"]

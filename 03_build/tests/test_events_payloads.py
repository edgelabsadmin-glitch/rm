"""
SPEC-008 unit tests — event-type enum + per-type payload validation.

No DB: these exercise the validation surface that runs before any insert. The
DB-backed emit/query/ordering/burst tests live in tests/test_events_db.py
(marker `db`, gated on a reachable Postgres).
"""

import inspect

import pytest
from pydantic import ValidationError

from core.events import log
from core.events.types import EVENT_TYPES, PAYLOAD_MODELS


def test_event_types_locked():
    # Design 04's 20 Phase-1 types + additive: signal-evaluated (017),
    # profile-regenerated + profile-edited (029), health-tier-changed (030).
    assert len(EVENT_TYPES) == 24
    for added in (
        "signal-evaluated",
        "profile-regenerated",
        "profile-edited",
        "health-tier-changed",
    ):
        assert added in EVENT_TYPES
    assert set(EVENT_TYPES) == set(PAYLOAD_MODELS)


def test_validate_payload_rejects_unknown_event_type():
    with pytest.raises(ValueError, match="unknown event_type"):
        log.validate_payload("not-a-real-event", {})


def test_validate_payload_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        log.validate_payload("signal-received", {})  # missing source + source_event_id


def test_validate_payload_rejects_extra_field():
    # extra="forbid" — typos must fail at emit time, not silently persist.
    with pytest.raises(ValidationError):
        log.validate_payload(
            "signal-received",
            {"source": "chorus", "source_event_id": "e1", "typo_field": 1},
        )


def test_validate_payload_returns_clean_dict():
    clean = log.validate_payload(
        "episode-ingested",
        {"episode_id": "ep1", "extraction_model": "claude-haiku-4-5-20251001", "latency_ms": 900},
    )
    assert clean["episode_id"] == "ep1"
    assert clean["entity_extractions"] == []  # default filled
    assert clean["latency_ms"] == 900


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_every_event_type_has_a_payload_model(event_type):
    model = PAYLOAD_MODELS[event_type]
    assert issubclass(model, __import__("pydantic").BaseModel)


def test_one_emit_helper_per_event_type():
    # Design 04: "Per-event-type helper functions … (one per Design 04 enum)."
    generic = {"emit_event", "emit_events_bulk"}  # the type-agnostic write paths
    helpers = {
        name
        for name, fn in inspect.getmembers(log, inspect.iscoroutinefunction)
        if name.startswith("emit_") and name not in generic
    }
    assert len(helpers) == 24, (
        f"expected 24 emit_* helpers, found {len(helpers)}: {sorted(helpers)}"
    )


def test_current_trace_id_is_none_outside_observe_context():
    # Best-effort: with no active Langfuse trace, resolution must not raise.
    assert log._current_trace_id() is None

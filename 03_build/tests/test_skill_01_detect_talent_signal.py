"""
SPEC-020 unit tests — Skill 01 signal extractor (mocked Haiku + emit).
"""

import json

import pytest

import skills.skill_01_detect_talent_signal as skill
from skills.skill_01_detect_talent_signal import ExtractionResult

_EXTRACTION = {
    "client_sentiment": "negative",
    "sentiment_vector": {"warmth": 0.2, "frustration": 0.7, "urgency": 0.6, "momentum": 0.3},
    "competitor_mentions": [
        {"competitor": "Globex", "quote": "we're evaluating Globex", "severity": "high"}
    ],
    "expansion_signals": [
        {"signal": "more coders", "quote": "need 3 more coders", "severity": "medium"}
    ],
    "talent_welfare": {
        "burnout": {"fired": True, "severity": "high", "quote": "I'm exhausted"},
        "growth": {"fired": False},
        "pay": {"fired": False},
    },
    "positive_quotes": ["your team has been great"],
    "key_quote": "we're evaluating Globex",
    "topic": "QBR",
}


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        fake_complete.captured = {"model": model, "prompt": prompt, "system": system}
        return "```json\n" + json.dumps(_EXTRACTION) + "\n```"

    async def fake_emit(**kwargs):
        fake_emit.calls.append(kwargs)

    fake_emit.calls = []
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr("core.events.log.emit_reasoning_completed", fake_emit)
    return fake_complete, fake_emit


async def test_run_parses_extraction_and_emits(_mock):
    fake_complete, fake_emit = _mock
    result = await skill.run("Client said: we're evaluating Globex", subject="Acrisure QBR")
    assert result.fired is True
    assert result.topic == "QBR"
    assert "haiku" in fake_complete.captured["model"]
    assert len(fake_emit.calls) == 1  # reasoning-completed emitted


async def test_skip_rule_empty_content():
    result = await skill.run("   ")
    assert result.fired is False
    assert result.topic == "no content"


def test_to_signal_facts_maps_all_downstream_inputs():
    r = ExtractionResult(
        sentiment_vector={"warmth": 0.2, "frustration": 0.7},
        competitor_mentions=[{"competitor": "Globex", "quote": "q", "severity": "high"}],
        expansion_signals=[{"signal": "x", "quote": "need more", "severity": "medium"}],
        talent_welfare={"burnout": {"fired": True, "severity": "high", "quote": "exhausted"}},
        positive_quotes=["great team"],
    )
    facts = r.to_signal_facts()
    assert facts["competitor_mentions"][0]["competitor"] == "Globex"
    assert facts["expansion_mention"]["fired"] is True
    assert facts["burnout"] == {"fired": True, "severity": "high", "evidence": ["exhausted"]}
    assert facts["growth_concern"]["fired"] is False
    assert facts["positive_quotes"] == ["great team"]
    # sentiment_now reflects warmth-frustration (0.2-0.7 → below 0.5)
    assert facts["sentiment_now"] < 0.5


def test_fired_false_when_all_empty():
    assert ExtractionResult().fired is False

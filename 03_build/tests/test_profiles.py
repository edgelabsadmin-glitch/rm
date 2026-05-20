"""SPEC-029 unit tests — profile regeneration override/divergence logic (no DB)."""

from core.profiles.loader import content_hash
from core.profiles.regenerator import diverged, resolve_regeneration, should_regenerate


def test_should_regenerate_triggers():
    assert should_regenerate(5, False, 0) is True  # >=5 episodes
    assert should_regenerate(0, True, 0) is True  # high-urgency event
    assert should_regenerate(0, False, 7) is True  # weekly fallback
    assert should_regenerate(2, False, 3) is False


def test_diverged():
    assert diverged("same text here", "same text here") is False
    assert diverged("completely different content about other things", "x") is True
    assert diverged("anything", "") is True  # empty baseline


def test_content_hash_deterministic():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_resolve_no_override_takes_fresh():
    r = resolve_regeneration(False, None, "FRESH", "OLD")
    assert r["content_md"] == "FRESH" and r["remerge_needed"] is False


def test_resolve_override_preserved_when_not_diverged():
    # fresh ~ baseline → RM edit preserved silently
    r = resolve_regeneration(True, "baseline text", "baseline text", "RM EDITED VERSION")
    assert r["content_md"] == "RM EDITED VERSION" and r["remerge_needed"] is False


def test_resolve_override_remerge_when_diverged():
    r = resolve_regeneration(True, "old baseline", "totally new world of facts", "RM EDITED")
    assert r["content_md"] == "RM EDITED"  # keep the edit
    assert r["remerge_needed"] is True
    assert r["pending_md"] == "totally new world of facts"

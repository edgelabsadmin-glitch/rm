"""Tier-weighted priority + color — pure."""

from core.analysis.priority import compute_priority


def test_no_fired_is_healthy():
    p = compute_priority([], tier="Strategic")
    assert p["priority"] == "healthy" and p["color"] == "green" and p["score"] == 0


def test_high_on_strategic_is_critical():
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier="Strategic")
    assert p["priority"] == "critical" and p["color"] == "red"


def test_high_on_core_is_high():
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier="Core")
    assert p["priority"] == "high" and p["color"] == "orange"


def test_max_signal_wins():
    p = compute_priority(
        [{"signal_id": "a", "severity": "low"}, {"signal_id": "b", "severity": "high"}],
        tier="Growth",
    )
    assert p["score"] == round(3 * 1.2, 3)


def test_medium_core_is_medium():
    p = compute_priority([{"signal_id": "x", "severity": "medium"}], tier="Core")
    assert p["priority"] == "medium" and p["color"] == "amber"

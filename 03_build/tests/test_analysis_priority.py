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


# ── boundary + tier-weighting coverage (added round 2) ───────────────────────


def test_high_growth_is_high_not_critical():
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier="Growth")  # 3*1.2=3.6
    assert p["priority"] == "high" and p["color"] == "orange"


def test_medium_strategic_is_high():
    p = compute_priority([{"signal_id": "x", "severity": "medium"}], tier="Strategic")  # 2*1.5=3
    assert p["priority"] == "high" and p["score"] == 3.0


def test_low_strategic_is_low():
    p = compute_priority([{"signal_id": "x", "severity": "low"}], tier="Strategic")  # 1*1.5=1.5
    assert p["priority"] == "low" and p["color"] == "blue"


def test_unknown_tier_defaults_core_weight():
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier="Mystery")  # 3*1.0
    assert p["score"] == 3.0 and p["priority"] == "high"


def test_none_tier_defaults_core_weight():
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier=None)
    assert p["score"] == 3.0


def test_unknown_severity_scores_zero():
    p = compute_priority([{"signal_id": "x", "severity": "bogus"}], tier="Strategic")
    assert p["priority"] == "healthy" and p["score"] == 0


def test_missing_severity_scores_zero():
    p = compute_priority([{"signal_id": "x"}], tier="Strategic")
    assert p["priority"] == "healthy"


def test_max_severity_wins_over_many_lows():
    p = compute_priority(
        [
            {"signal_id": "a", "severity": "low"},
            {"signal_id": "b", "severity": "low"},
            {"signal_id": "c", "severity": "medium"},
        ],
        tier="Core",
    )
    assert p["priority"] == "medium" and p["score"] == 2.0


def test_score_rounded_to_three_places():
    # 3 * 1.2 = 3.6 stays clean; ensure rounding key exists and is numeric
    p = compute_priority([{"signal_id": "x", "severity": "high"}], tier="Growth")
    assert p["score"] == round(3 * 1.2, 3)

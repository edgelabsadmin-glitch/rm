"""SPEC-030 unit tests — dual-sided account-health formula (pure, no DB)."""

from core.health.dual_sided import evaluate, score_customer_side, score_talent_side, tier_for


def test_tier_for_thresholds():
    assert tier_for(50) == "Healthy"
    assert tier_for(20) == "Stable"
    assert tier_for(0) == "Watch"
    assert tier_for(-25) == "At-Risk"
    assert tier_for(-60) == "Escalated"


def test_customer_side_polarity():
    bad, _ = score_customer_side({"churn_probability": 1.0, "open_account_risk_cases": 3})
    good, _ = score_customer_side({"expansion_probability": 1.0, "customer_health": "Healthy"})
    assert bad < 0 < good


def test_talent_side_replacement_rate_drives_negative():
    score, contrib = score_talent_side({"replacement_rate": 0.9, "open_talent_risk_cases": 3})
    assert score < -30
    assert contrib[0]["signal"] in {"replacement_rate", "open_talent_risk_cases"}


def test_customer_healthy_but_talent_dying_weighted_by_tier():
    facts = {
        "customer_health": "Healthy",
        "expansion_probability": 0.8,
        "replacement_rate": 0.9,
        "open_talent_risk_cases": 3,
    }
    smb = evaluate("001X", "SMB", facts)  # beta=0.4 (customer leads)
    ent = evaluate("001X", "Enterprise", facts)  # beta=0.6 (talent leads)
    # talent-side is very negative; Enterprise weights it more -> lower composite
    assert ent.composite_score < smb.composite_score
    assert ent.customer_side_score > 0 > ent.talent_side_score


def test_evaluate_top_contributors_capped():
    h = evaluate("001X", "Mid-Market", {"churn_probability": 0.9, "replacement_rate": 0.8})
    assert len(h.top_contributors) <= 3
    assert h.tier in {"Healthy", "Stable", "Watch", "At-Risk", "Escalated"}

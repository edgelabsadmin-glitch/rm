"""Evidence-pack pure shaping — no IO."""

from core.analysis.evidence_pack import shape_account_facts, shape_talent_facts


def test_shape_account_facts_computes_quant_inputs():
    row = {
        "account_id": "A1",
        "tier": "Strategic",
        "active_talent": 6,
        "churn_probability": 0.7,
        "rm_name": "R",
        "owner_id": "O",
    }
    facts = shape_account_facts(
        row,
        days_since_ebr=200,
        talent_baseline=10,
        departures_30d=3,
        onboarding_30d=0,
        max_days_in_onboarding=0,
        reply_latency_now_h=80,
        reply_latency_prior_h=8,
        inbound_now_30d=1,
        inbound_prior_30d=10,
        distinct_engaged_contacts=1,
    )
    assert facts["tier"] == "Strategic"
    assert facts["days_since_ebr"] == 200
    assert facts["coverage_gap_input"]["active_talent"] == 6
    assert "evidence_ids" in facts and isinstance(facts["evidence_ids"], set)
    # a present fact yields a stable evidence id; an absent one does not
    assert "fact:days_since_ebr" in facts["evidence_ids"]


def test_shape_talent_facts():
    row = {"associate_id": "T1", "account_id": "A1", "tier": "Growth", "stage": "Active"}
    facts = shape_talent_facts(
        row,
        days_in_current_stage=120,
        max_days_in_onboarding=None,
        days_since_last_contact=40,
        stage_changes_90d=2,
    )
    assert facts["associate_id"] == "T1"
    assert facts["stage"] == "Active"
    assert facts["days_in_current_stage"] == 120
    assert "fact:days_since_last_contact" in facts["evidence_ids"]
    # None-valued derived inputs do not produce evidence ids
    assert "fact:max_days_in_onboarding" not in facts["evidence_ids"]

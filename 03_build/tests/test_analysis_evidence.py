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


# ── _days_since + shaping edge coverage (added round 2) ──────────────────────

from datetime import datetime, timedelta, timezone  # noqa: E402

from core.analysis.evidence_pack import _days_since  # noqa: E402

UTC = timezone.utc  # noqa: UP017 — datetime.UTC is 3.11+; keeps local 3.9 tests runnable


def test_days_since_none():
    assert _days_since(None) is None


def test_days_since_bad_string():
    assert _days_since("not-a-date") is None


def test_days_since_aware_datetime():
    ref = datetime.now(UTC) - timedelta(days=10, minutes=5)
    assert _days_since(ref) == 10


def test_days_since_naive_datetime_assumed_utc():
    ref = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=3, minutes=5)
    assert _days_since(ref) == 3


def test_days_since_iso_string():
    ref = (datetime.now(UTC) - timedelta(days=5, minutes=5)).isoformat()
    assert _days_since(ref) == 5


def test_days_since_plain_date():
    d = (datetime.now(UTC) - timedelta(days=7)).date()
    assert _days_since(d) in (6, 7)


def test_days_since_unsupported_type_returns_none():
    assert _days_since(12345) is None


def test_shape_account_facts_missing_derived_are_none():
    facts = shape_account_facts({"account_id": "A1", "tier": "Core"})
    assert facts["days_since_ebr"] is None
    assert facts["active_talent"] is None
    # None facts produce no evidence id
    assert "fact:days_since_ebr" not in facts["evidence_ids"]
    # the always-present account_id does
    assert "fact:account_id" in facts["evidence_ids"]


def test_shape_account_facts_coverage_bundle_excluded_from_evidence():
    facts = shape_account_facts(
        {"account_id": "A1", "tier": "Core", "active_talent": 5}, talent_baseline=10
    )
    # the dict-valued bundle must not become an evidence id
    assert "fact:coverage_gap_input" not in facts["evidence_ids"]
    assert facts["coverage_gap_input"]["talent_baseline"] == 10


def test_shape_talent_facts_all_none_minimal_evidence():
    facts = shape_talent_facts({"associate_id": "T1"})
    assert facts["evidence_ids"] == {"fact:associate_id"}


def test_shape_account_facts_includes_meeting_context():
    facts = shape_account_facts(
        {"account_id": "A1", "tier": "Strategic"},
        days_since_last_meeting=12,
        meetings_60d=3,
    )
    assert facts["days_since_last_meeting"] == 12
    assert facts["meetings_60d"] == 3
    assert "fact:days_since_last_meeting" in facts["evidence_ids"]

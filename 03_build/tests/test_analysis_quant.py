"""Deterministic quantitative signal computations — pure, no IO."""

from core.analysis.quant_signals import (
    attrition_velocity,
    coverage_gap,
    ebr_overdue,
    inbound_volume_drop,
    ramp_stall,
    response_time_degradation,
    single_threaded,
)


def test_ebr_overdue_recent_not_fired():
    assert ebr_overdue({"days_since_ebr": 20, "tier": "Strategic"}).fired is False


def test_ebr_overdue_just_past_low():
    r = ebr_overdue({"days_since_ebr": 100, "tier": "Strategic"})  # cadence 90
    assert r.fired and r.severity == "low"


def test_ebr_overdue_far_past_high():
    r = ebr_overdue({"days_since_ebr": 200, "tier": "Strategic"})
    assert r.fired and r.severity == "high"


def test_ebr_overdue_null_not_fired():
    assert ebr_overdue({"days_since_ebr": None, "tier": "Core"}).fired is False


def test_attrition_velocity_none():
    assert attrition_velocity({"departures_30d": 0, "active_talent": 10}).fired is False


def test_attrition_velocity_cluster_high():
    r = attrition_velocity({"departures_30d": 4, "active_talent": 8})  # 50% in 30d
    assert r.fired and r.severity == "high"


def test_attrition_velocity_backfilled_not_fired():
    # 2 left but 2 onboarding to replace → net stable, don't false-fire
    assert (
        attrition_velocity({"departures_30d": 2, "active_talent": 10, "onboarding_30d": 2}).fired
        is False
    )


def test_response_time_stable_not_fired():
    assert (
        response_time_degradation({"reply_latency_now_h": 6, "reply_latency_prior_h": 5}).fired
        is False
    )


def test_response_time_degraded_fired():
    r = response_time_degradation({"reply_latency_now_h": 72, "reply_latency_prior_h": 8})
    assert r.fired and r.severity in ("medium", "high")


def test_response_time_insufficient_history():
    assert (
        response_time_degradation({"reply_latency_now_h": 50, "reply_latency_prior_h": None}).fired
        is False
    )


def test_ramp_stall_fired():
    assert ramp_stall({"max_days_in_onboarding": 45}).fired is True


def test_ramp_stall_ok():
    assert ramp_stall({"max_days_in_onboarding": 7}).fired is False


def test_coverage_gap_fired():
    r = coverage_gap({"active_talent": 6, "talent_baseline": 10})  # -40%
    assert r.fired and r.severity == "high"


def test_coverage_gap_ok():
    assert coverage_gap({"active_talent": 10, "talent_baseline": 10}).fired is False


def test_single_threaded_fired():
    assert single_threaded({"distinct_engaged_contacts": 1}).fired is True


def test_single_threaded_ok():
    assert single_threaded({"distinct_engaged_contacts": 4}).fired is False


def test_inbound_drop_fired():
    r = inbound_volume_drop({"inbound_now_30d": 1, "inbound_prior_30d": 12})
    assert r.fired


def test_inbound_drop_insufficient():
    assert inbound_volume_drop({"inbound_now_30d": 1, "inbound_prior_30d": 2}).fired is False

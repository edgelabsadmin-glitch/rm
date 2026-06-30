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


# ── boundary + edge coverage (added round 2) ─────────────────────────────────


def test_ebr_overdue_exactly_at_cadence_not_fired():
    # days == cadence is not overdue (strictly greater required)
    assert ebr_overdue({"days_since_ebr": 90, "tier": "Strategic"}).fired is False


def test_ebr_overdue_one_day_over_is_low():
    r = ebr_overdue({"days_since_ebr": 91, "tier": "Strategic"})  # over=1
    assert r.fired and r.severity == "low"


def test_ebr_overdue_medium_band_core():
    # Core cadence 180; over >= 0.3*180=54 → medium, but < 180 → not high
    r = ebr_overdue({"days_since_ebr": 240, "tier": "Core"})  # over=60
    assert r.fired and r.severity == "medium"


def test_ebr_overdue_unknown_tier_defaults_core():
    # cadence 180; 200 over by 20 (<54) → low
    r = ebr_overdue({"days_since_ebr": 200, "tier": "Mystery"})
    assert r.fired and r.severity == "low"


def test_ebr_overdue_missing_tier_key_defaults_core():
    r = ebr_overdue({"days_since_ebr": 400})
    assert r.fired and r.severity == "high"  # over=220 >= 180


def test_attrition_velocity_rate_exactly_threshold_fires_low():
    # net 3 / 20 = 0.15 → not < 0.15 → fires, 0.15 < 0.25 → low
    r = attrition_velocity({"departures_30d": 3, "active_talent": 20})
    assert r.fired and r.severity == "low"


def test_attrition_velocity_just_below_threshold_not_fired():
    # net 2 / 20 = 0.10 → below 0.15
    assert attrition_velocity({"departures_30d": 2, "active_talent": 20}).fired is False


def test_attrition_velocity_medium_band():
    r = attrition_velocity({"departures_30d": 6, "active_talent": 20})  # 0.30
    assert r.fired and r.severity == "medium"


def test_attrition_velocity_onboarding_outpaces_departures_not_fired():
    # net negative → not fired
    assert (
        attrition_velocity({"departures_30d": 2, "active_talent": 10, "onboarding_30d": 5}).fired
        is False
    )


def test_attrition_velocity_none_inputs_safe():
    assert attrition_velocity({"departures_30d": None, "active_talent": None}).fired is False


def test_response_time_ratio_below_two_not_fired():
    assert (
        response_time_degradation({"reply_latency_now_h": 30, "reply_latency_prior_h": 20}).fired
        is False
    )  # ratio 1.5


def test_response_time_now_below_24h_not_fired():
    # ratio high but absolute latency still small
    assert (
        response_time_degradation({"reply_latency_now_h": 20, "reply_latency_prior_h": 2}).fired
        is False
    )


def test_response_time_ratio_five_is_high():
    r = response_time_degradation({"reply_latency_now_h": 50, "reply_latency_prior_h": 10})
    assert r.fired and r.severity == "high"


def test_response_time_just_at_24h_medium():
    r = response_time_degradation({"reply_latency_now_h": 24, "reply_latency_prior_h": 10})
    assert r.fired and r.severity == "medium"


def test_response_time_prior_zero_not_fired():
    assert (
        response_time_degradation({"reply_latency_now_h": 80, "reply_latency_prior_h": 0}).fired
        is False
    )


def test_ramp_stall_exactly_30_is_medium():
    r = ramp_stall({"max_days_in_onboarding": 30})
    assert r.fired and r.severity == "medium"


def test_ramp_stall_exactly_60_is_high():
    r = ramp_stall({"max_days_in_onboarding": 60})
    assert r.fired and r.severity == "high"


def test_ramp_stall_none_not_fired():
    assert ramp_stall({"max_days_in_onboarding": None}).fired is False


def test_coverage_gap_exactly_25pct_is_medium():
    r = coverage_gap({"active_talent": 75, "talent_baseline": 100})  # -25%
    assert r.fired and r.severity == "medium"


def test_coverage_gap_just_below_25pct_not_fired():
    assert coverage_gap({"active_talent": 76, "talent_baseline": 100}).fired is False


def test_coverage_gap_40pct_is_high():
    r = coverage_gap({"active_talent": 60, "talent_baseline": 100})
    assert r.fired and r.severity == "high"


def test_coverage_gap_above_baseline_not_fired():
    assert coverage_gap({"active_talent": 12, "talent_baseline": 10}).fired is False


def test_single_threaded_exactly_one_fires():
    assert single_threaded({"distinct_engaged_contacts": 1}).fired is True


def test_single_threaded_two_not_fired():
    assert single_threaded({"distinct_engaged_contacts": 2}).fired is False


def test_single_threaded_zero_is_silence_not_fired():
    # zero engaged contacts is silence, not single-threading
    assert single_threaded({"distinct_engaged_contacts": 0}).fired is False


def test_single_threaded_none_not_fired():
    assert single_threaded({"distinct_engaged_contacts": None}).fired is False


def test_inbound_drop_prior_below_min_not_fired():
    assert inbound_volume_drop({"inbound_now_30d": 0, "inbound_prior_30d": 3}).fired is False


def test_inbound_drop_at_40pct_not_fired():
    # now == prior*0.4 exactly → not a drop
    assert inbound_volume_drop({"inbound_now_30d": 4, "inbound_prior_30d": 10}).fired is False


def test_inbound_drop_to_zero_is_high():
    r = inbound_volume_drop({"inbound_now_30d": 0, "inbound_prior_30d": 12})
    assert r.fired and r.severity == "high"


def test_inbound_drop_partial_is_medium():
    r = inbound_volume_drop({"inbound_now_30d": 3, "inbound_prior_30d": 12})  # 25% of prior
    assert r.fired and r.severity == "medium"

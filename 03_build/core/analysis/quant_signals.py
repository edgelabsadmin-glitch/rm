"""
Deterministic, pure computations for the quantitative signals. No IO.

Each returns a QuantResult the analyst's claims are later validated against
(core/analysis/validate.py): if the LLM disagrees with these, the math wins.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class QuantResult:
    signal_id: str
    fired: bool
    severity: str | None = None  # 'low' | 'medium' | 'high'
    detail: str = ""


_EBR_CADENCE = {"Strategic": 90, "Growth": 120, "Core": 180}


def ebr_overdue(f: dict) -> QuantResult:
    sid = "ebr_overdue_v1"
    days = f.get("days_since_ebr")
    cadence = _EBR_CADENCE.get(f.get("tier") or "Core", 180)
    if days is None or days <= cadence:
        return QuantResult(sid, False)
    over = days - cadence
    sev = "high" if over >= cadence else ("medium" if over >= cadence * 0.3 else "low")
    return QuantResult(sid, True, sev, f"{days}d since EBR vs {cadence}d cadence")


def attrition_velocity(f: dict) -> QuantResult:
    sid = "talent_attrition_velocity_v1"
    dep = f.get("departures_30d", 0) or 0
    base = f.get("active_talent", 0) or 0
    onb = f.get("onboarding_30d", 0) or 0
    net = dep - onb  # backfill nets out
    if base <= 0 or net <= 0:
        return QuantResult(sid, False)
    rate = net / base
    if rate < 0.15:
        return QuantResult(sid, False)
    sev = "high" if rate >= 0.4 else ("medium" if rate >= 0.25 else "low")
    return QuantResult(sid, True, sev, f"net {net} departures / {base} ({rate:.0%})")


def response_time_degradation(f: dict) -> QuantResult:
    sid = "response_time_degradation_v1"
    now = f.get("reply_latency_now_h")
    prior = f.get("reply_latency_prior_h")
    if now is None or prior is None or prior <= 0:
        return QuantResult(sid, False)
    ratio = now / prior
    if ratio < 2 or now < 24:
        return QuantResult(sid, False)
    sev = "high" if ratio >= 5 else "medium"
    return QuantResult(sid, True, sev, f"reply latency {prior:.0f}h->{now:.0f}h")


def ramp_stall(f: dict) -> QuantResult:
    sid = "ramp_stall_v1"
    d = f.get("max_days_in_onboarding")
    if d is None or d < 30:
        return QuantResult(sid, False)
    sev = "high" if d >= 60 else "medium"
    return QuantResult(sid, True, sev, f"{d}d in onboarding")


def coverage_gap(f: dict) -> QuantResult:
    sid = "coverage_gap_v1"
    cur = f.get("active_talent", 0) or 0
    base = f.get("talent_baseline", 0) or 0
    if base <= 0 or cur >= base:
        return QuantResult(sid, False)
    drop = (base - cur) / base
    if drop < 0.25:
        return QuantResult(sid, False)
    sev = "high" if drop >= 0.4 else "medium"
    return QuantResult(sid, True, sev, f"{cur} vs baseline {base} (-{drop:.0%})")


def single_threaded(f: dict) -> QuantResult:
    sid = "single_threaded_account_v1"
    n = f.get("distinct_engaged_contacts")
    # Fires only at exactly one engaged contact. Zero is silence, not single-threading.
    if n != 1:
        return QuantResult(sid, False)
    return QuantResult(sid, True, "medium", "only 1 engaged contact")


def inbound_volume_drop(f: dict) -> QuantResult:
    sid = "inbound_volume_drop_v1"
    now = f.get("inbound_now_30d", 0) or 0
    prior = f.get("inbound_prior_30d", 0) or 0
    if prior < 4 or now >= prior * 0.4:
        return QuantResult(sid, False)
    sev = "high" if now == 0 else "medium"
    return QuantResult(sid, True, sev, f"inbound {prior}->{now} (30d)")


# Registry: signal_id → computation. Used by validate.py + agent.py.
QUANT_SIGNALS: dict[str, Callable[[dict], QuantResult]] = {
    "ebr_overdue_v1": ebr_overdue,
    "talent_attrition_velocity_v1": attrition_velocity,
    "response_time_degradation_v1": response_time_degradation,
    "ramp_stall_v1": ramp_stall,
    "coverage_gap_v1": coverage_gap,
    "single_threaded_account_v1": single_threaded,
    "inbound_volume_drop_v1": inbound_volume_drop,
}

"""SPEC-017 — churn_signal_contact_disengagement_v1 (hybrid; tiered).

Mirrors the definition's rule layer (A/B/C) + tier-aware thresholds + the LLM
ambiguity resolver (is_explained suppresses the fire). Reads ctx.facts:
  days_since_last_reply, ebr_no_shows_last_60d, chorus_call_count_21d,
  chorus_call_count_prior_21d, in_renewal_window(bool), renewal_days(int|None),
  is_explained(bool, from the LLM resolver).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="churn_signal_contact_disengagement_v1",
    category="churn",
    severity_model="tiered",
    owning_skills=frozenset({3, 5, 10}),
    detection_type="hybrid",
)

_SILENCE_DAYS = {"SMB": 21, "Mid-Market": 14, "Enterprise": 10}
_EBR_NO_SHOW_THRESHOLD = {"SMB": 2, "Mid-Market": 2, "Enterprise": 1}


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    tier = ctx.tier or "Mid-Market"
    silence_days = _SILENCE_DAYS.get(tier, 14)
    ebr_threshold = _EBR_NO_SHOW_THRESHOLD.get(tier, 2)

    rule_a = f.get("days_since_last_reply", 0) >= silence_days
    rule_b = f.get("ebr_no_shows_last_60d", 0) >= ebr_threshold
    rule_c = f.get("chorus_call_count_21d", 0) == 0 and f.get("chorus_call_count_prior_21d", 0) > 0

    fired_rules = [name for name, ok in (("a", rule_a), ("b", rule_b), ("c", rule_c)) if ok]
    if not fired_rules:
        return no_fire(META, rules=[])

    # LLM ambiguity resolver: a known absence (PTO/leave) explains the silence.
    if f.get("is_explained", False):
        return no_fire(META, is_explained=True, explanation=f.get("explanation", ""))

    in_renewal = bool(f.get("in_renewal_window", False))
    renewal_days = f.get("renewal_days")
    n = len(fired_rules)
    if n == 3 or (n == 2 and in_renewal and (renewal_days is not None and renewal_days < 30)):
        severity = "high"
    elif n == 2 or (n == 1 and in_renewal):
        severity = "medium"
    else:
        severity = "low"

    evidence = []
    if rule_a:
        evidence.append(f"no reply in {f.get('days_since_last_reply')}d (>= {silence_days})")
    if rule_b:
        evidence.append(f"{f.get('ebr_no_shows_last_60d')} EBR no-shows in 60d")
    if rule_c:
        evidence.append("Chorus activity went silent (active→0 in 21d)")
    return fire(META, severity, evidence=evidence, rules=fired_rules, tier=tier)

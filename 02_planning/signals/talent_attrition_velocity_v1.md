# talent_attrition_velocity_v1

**Version:** v1
**Category:** talent
**Severity model:** low|medium|high (deterministic)
**Detection type:** quantitative (net departures over a 30d window, backfill-aware)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Talent attrition velocity. A cluster of associates at one account departs (Terminated/Replaced/Downsell) faster than they are backfilled — net departures ≥15% of active talent in 30d. High at ≥40%.

## Fire criteria

A cluster of associates at one account departs (Terminated/Replaced/Downsell) faster than they are backfilled — net departures ≥15% of active talent in 30d. High at ≥40%.

## Evidence required

pulse.associate_stage_history departures_30d, onboarding_30d, sf_accounts.active_talent. Net of onboarding so churn-and-replace doesn't false-fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

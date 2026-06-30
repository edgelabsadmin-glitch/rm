# ramp_stall_v1

**Version:** v1
**Category:** talent
**Severity model:** medium|high (deterministic)
**Detection type:** quantitative (max days in an onboarding stage)
**Entity type(s):** talent
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Ramp stall. An associate has been stuck in Onboarding/Selected too long — ≥30 days. High at ≥60 days.

## Fire criteria

An associate has been stuck in Onboarding/Selected too long — ≥30 days. High at ≥60 days.

## Evidence required

pulse.associate_stage_history observed_at for onboarding stages. Active talent past onboarding → does not fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

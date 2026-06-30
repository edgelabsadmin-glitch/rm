# inbound_volume_drop_v1

**Version:** v1
**Category:** churn
**Severity model:** medium|high (deterministic)
**Detection type:** quantitative (now-30d vs prior-30d inbound count)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Inbound-volume drop. A client who emailed regularly has gone quiet — current 30d inbound < 40% of the prior 30d, with a prior baseline of ≥4. High when current is zero.

## Fire criteria

A client who emailed regularly has gone quiet — current 30d inbound < 40% of the prior 30d, with a prior baseline of ≥4. High when current is zero.

## Evidence required

pulse.inbox_emails counts (now-30d, prior-30d). Prior baseline <4 → insufficient, does not fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

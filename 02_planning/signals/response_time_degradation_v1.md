# response_time_degradation_v1

**Version:** v1
**Category:** churn
**Severity model:** low|medium|high (deterministic)
**Detection type:** quantitative (computed in quant_signals.py; LLM corroborates with snippets)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Response-time degradation. A client's reply latency to the RM is trending materially upward — the now-vs-prior reply-latency ratio ≥2× and current latency ≥24h. Severity high at ≥5× the prior baseline.

## Fire criteria

A client's reply latency to the RM is trending materially upward — the now-vs-prior reply-latency ratio ≥2× and current latency ≥24h. Severity high at ≥5× the prior baseline.

## Evidence required

pulse.inbox_emails received/reply timestamps; prior-period baseline. Insufficient history (no prior latency) → does not fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

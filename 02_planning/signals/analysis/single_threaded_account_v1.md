# single_threaded_account_v1

**Version:** v1
**Category:** churn
**Severity model:** medium (deterministic)
**Detection type:** quantitative (distinct engaged client contacts)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Single-threaded account. All client communication runs through exactly one contact — a concentration/continuity risk.

## Fire criteria

All client communication runs through exactly one contact — a concentration/continuity risk.

## Evidence required

pulse.inbox_emails distinct from_email over 90d = 1. More than one engaged contact → does not fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

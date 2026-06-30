# talent_silence_concern_v1

**Version:** v1
**Category:** talent
**Severity model:** low|medium|high (LLM-judged)
**Detection type:** LLM (placed talent goes quiet or raises an issue)
**Entity type(s):** talent
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Talent silence / concern. A placed associate has gone unusually quiet or has raised an explicit concern (workload, fit, pay, growth) in their own emails.

## Fire criteria

A placed associate has gone unusually quiet or has raised an explicit concern (workload, fit, pay, growth) in their own emails.

## Evidence required

pulse.inbox_emails authored by the associate; days_since_last_contact. Fire only with a cited snippet or a clear silence gap.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

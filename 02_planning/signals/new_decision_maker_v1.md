# new_decision_maker_v1

**Version:** v1
**Category:** expansion
**Severity model:** low|medium (LLM-judged)
**Detection type:** LLM (a new senior contact starts emailing)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

New decision-maker appears. A new senior/decision-maker contact begins corresponding on the account — an expansion or relationship-mapping opportunity.

## Fire criteria

A new senior/decision-maker contact begins corresponding on the account — an expansion or relationship-mapping opportunity.

## Evidence required

pulse.inbox_emails new from_email with a senior-title signal in signature/snippet. Fire only with a cited snippet evidencing seniority + novelty.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

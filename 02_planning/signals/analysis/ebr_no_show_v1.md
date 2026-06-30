# ebr_no_show_v1

**Version:** v1
**Category:** churn
**Severity model:** medium (LLM-judged)
**Detection type:** LLM (scheduled EBR held but key contact absent)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

EBR no-show. A scheduled EBR took place but the account's key contact did not attend — a disengagement tell distinct from 'EBR overdue'.

## Fire criteria

A scheduled EBR took place but the account's key contact did not attend — a disengagement tell distinct from 'EBR overdue'.

## Evidence required

Calendar/meeting snippets + contact list. Fire only with evidence the meeting occurred and the named contact was absent.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

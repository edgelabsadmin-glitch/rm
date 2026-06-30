# renewal_approaching_healthy_v1

**Version:** v1
**Category:** expansion
**Severity model:** low|medium (LLM-judged)
**Detection type:** hybrid (renewal proximity + health/advocacy)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Renewal-approaching + healthy. The account is near its renewal/EBR window AND shows high health or advocacy signals — a warm moment to propose expansion/upsell.

## Fire criteria

The account is near its renewal/EBR window AND shows high health or advocacy signals — a warm moment to propose expansion/upsell.

## Evidence required

last_ebr/tier cadence proximity + positive client snippets / advocacy. Fire only when both proximity and positive evidence are present.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

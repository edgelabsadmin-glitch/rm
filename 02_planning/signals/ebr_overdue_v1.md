# ebr_overdue_v1

**Version:** v1
**Category:** churn
**Severity model:** low|medium|high (deterministic)
**Detection type:** quantitative (days since last EBR vs tier cadence)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

EBR overdue. No Executive Business Review has occurred within the account's tier cadence (Strategic 90d / Growth 120d / Core 180d). Severity scales with how far past cadence.

## Fire criteria

No Executive Business Review has occurred within the account's tier cadence (Strategic 90d / Growth 120d / Core 180d). Severity scales with how far past cadence.

## Evidence required

sf_accounts.last_ebr + tier. Null last_ebr → does not fire (insufficient evidence).

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

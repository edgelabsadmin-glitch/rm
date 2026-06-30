# coverage_gap_v1

**Version:** v1
**Category:** talent
**Severity model:** medium|high (deterministic)
**Detection type:** quantitative (current active talent vs account baseline)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Coverage gap. Active placements at an account have fallen below its baseline by ≥25%. High at ≥40% drop.

## Fire criteria

Active placements at an account have fallen below its baseline by ≥25%. High at ≥40% drop.

## Evidence required

sf_accounts.active_talent vs talent_baseline (count of associates in Active/Onboarding/Selected). Baseline 0 → does not fire.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

# champion_departure_v1

**Version:** v1
**Category:** churn
**Severity model:** medium|high (LLM-judged)
**Detection type:** LLM (reads inbox bounce / auto-reply / 'no longer with the company' snippets)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Champion departure. A key contact at the account appears to have left — a hard bounce, an out-of-office 'no longer with', or an explicit handover message names a departure of the RM's primary contact.

## Fire criteria

A key contact at the account appears to have left — a hard bounce, an out-of-office 'no longer with', or an explicit handover message names a departure of the RM's primary contact.

## Evidence required

pulse.inbox_emails snippets (bounce notices, auto-replies). Fire only with a cited snippet that names the departure; ambiguous → not fired.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.

# Spec 027 — Skill 10 — cross-account-pattern-finder (+ client_termination_pattern variant)

**Maps to:** §14 Skills (Skill 10 including client_termination_pattern); `01_design/skills/10-cross-account-pattern-finder.md`; §13.4 cross-account query example; §13.6 #1.
**Depends on:** specs 005, 006, 007 (cross-account retriever — Q77), 008, 009, 017, 020.
**Effort:** 1.0 day. **Includes client_termination_pattern variant per Decision 36.**

## Description

Per `01_design/skills/10-cross-account-pattern-finder.md`. Schedule-driven (weekly Sunday 10:00). Uses the cross-account retriever (spec 007) to find recurring themes across customers. Phase 1 variants:
- **Theme patterns** — vendor consolidation, AI displacement, pay concerns, etc. — aggregate cross-customer same-Topic-node mentions.
- **client_termination_pattern variant** — cross-temporal cross-customer aggregation of `client_termination_pattern_v1` signal (Decision 36, ~0.5d) — surfaces cohorts of customers with elevated termination rates in a given vertical.

Pattern cards surface in the **Overall view** (not per-RM queue) because they don't have a single owner. Pseudonymization toggle (Q78) at export time only; in-app customer names visible.

## Inputs

- Weekly Sunday schedule.
- Cross-account retriever (spec 007).
- `client_termination_pattern_v1` signal evaluations.

## Outputs

- `03_build/pulse/skills/skill_10_cross_account_pattern_finder.py`.
- Per pattern: `action-suggested` with pattern_card payload (theme, support_cardinality, verbatim_evidence, proposed_portfolio_response).

## Definition of Done

- [ ] Minimum support threshold ≥3 customers enforced.
- [ ] Demographic-denylist guardrail enforced (no protected-class patterns).
- [ ] One pattern card per theme per month (frequency cap).
- [ ] client_termination_pattern variant produces cross-vertical cohort cards.
- [ ] Cards routed to Overall view (not per-RM queue) — verified by RBAC test (spec 042).
- [ ] Pseudonymization toggle at export time.

## Tests

- **Unit:** minimum-support enforcement; denylist guardrail; frequency cap.
- **Integration:** fixture with vendor-consolidation theme at 3 customers → pattern card emitted.
- **Negative:** denylisted theme → ValueError at retriever (spec 007 enforces).

## Signal definitions involved

Per skill 10 cross-reference: primary `client_termination_pattern_v1`; cross-account aggregators `churn_signal_competitor_mention_v1`, `expansion_signal_verbal_capacity_mention_v1`, `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1`, `escalation_signal_case_pattern_v1`.

## Open questions

Q77 (cross-account retriever shape — exact match), Q78 (pseudonymization), Q79 (cadence — weekly default with intra-week severity trigger) — disposed.

## What this is NOT

- Not where the cross-account retriever lives (spec 007).
- Not where pattern cards render (Overall view UI — spec 035 with RBAC from spec 042).

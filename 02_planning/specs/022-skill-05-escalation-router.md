# Spec 022 — Skill 05 — escalation-router

**Maps to:** §14 Skills (Skill 05); `01_design/skills/05-escalation-router.md`; §13.5 row "Primary escalation point"; §13.6 #6.
**Depends on:** specs 005, 006, 008, 009, 017, 020.
**Effort:** 0.75 day.

## Description

Per `01_design/skills/05-escalation-router.md`. Episode-driven on new risk-tagged Cases, high-urgency `raised_concern_about` edges, and Associate Stage→Replaced/Terminated transitions. Routes to internal teams per the category table.

## Inputs

- Risk-tagged Case episodes (spec 012 SFDC adapter emits).
- High-severity welfare/competitor signals (specs 020 + 017 fire).
- `pulse_team_leads.yaml` (Q63) for routing destinations.

## Outputs

- `03_build/pulse/skills/skill_05_escalation_router.py`.
- Per fire: `action-suggested` with email_draft (to team alias) + SFDC Task (assigned to team lead) + RM cc.

## Definition of Done

- [ ] Category-to-team routing table per Skill 05 spec implemented as data in `pulse_team_leads.yaml`.
- [ ] Self-healing case detection (Replaced → new Active within 7d at same customer/role) suppresses fire.
- [ ] No duplicate escalation: rate-limit table keyed on `case_id` enforced.
- [ ] Enterprise variant cc's VP-CS on every escalation.
- [ ] Risk-Customer-Payment-Failure category routes to Finance (hard rule).
- [ ] Langfuse-traced.

## Tests

- **Unit:** category-to-team routing for each of the 14 risk categories.
- **Integration:** new Case ingested → Skill 05 fires → expected action card structure.
- **Negative:** double-Case-create → no duplicate action.

## Signal definitions involved

Per skill 05 cross-reference: primary `escalation_signal_case_pattern_v1`, `escalation_signal_severity_jump_v1`; high-severity cascade `churn_signal_competitor_mention_v1`, `talent_pay_concern_v1`.

## Open questions

Q62 (routing table source-of-truth), Q63 (team-lead User.Id mapping), Q64 (Jira adapter timing) — disposed.

## What this is NOT

- Not Jira ticket creation (v1.5+; Phase 1 = email + SFDC Task).
- Not Skill 09 — Skill 05 routes *issues*; Skill 09 routes *coaching opportunities*. Deconfliction via shared rate-limit.

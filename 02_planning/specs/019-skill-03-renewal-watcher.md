# Spec 019 — Skill 03 — renewal-watcher

**Maps to:** §14 Skills (Skill 03); `01_design/skills/03-renewal-watcher.md`; §13.5 row "Manage renewals end-to-end" + "Proactive risk monitoring"; §13.6 #5.
**Depends on:** specs 005, 006, 008, 009, 012, 017, 020, 029, 030.
**Effort:** 1.0 day. **The second Week-2 end-to-end skill.**

## Description

Implement the renewal-watcher skill per `01_design/skills/03-renewal-watcher.md`. Schedule-driven (daily 06:00 local via Activepieces `daily_heartbeat` flow). For each Customer with a renewal in the watch window, evaluates `churn_signal_renewal_period_silence_v1` + `churn_signal_contact_disengagement_v1` + `client_termination_pattern_v1` (account-context); composes a draft renewal-touch action card if composite risk ≥ medium. Tier-aware lookahead windows: SMB 60d / Mid 90d / Enterprise 120d.

## Inputs

- Schedule trigger from Activepieces daily heartbeat flow.
- All Customer records with upcoming renewals.
- Signals: per `01_design/skills/03-renewal-watcher.md` §"Owned signals."
- Per-Profile Markdown (spec 029) for personalization.
- Account `Segment__c` for tier-aware variants.

## Outputs

- `03_build/pulse/skills/skill_03_renewal_watcher.py` exporting `async def run(ctx: SkillContext) -> list[ActionSuggested]`.
- For each at-risk renewal: `action-suggested` event with email_draft + sfdc_task per Design 05 spec.
- Reasoning capture with inline-tag voice citing the signal evaluations.

## Definition of Done

- [ ] Daily run scans the book and identifies upcoming renewals in tier-appropriate window.
- [ ] Composite risk scoring per `01_design/skills/03-renewal-watcher.md` §"Behavior" table.
- [ ] Tier variants enforce different lookahead windows and approval modes.
- [ ] Guardrails: no draft contains specific talent risk details by name (per Skill 03 spec).
- [ ] Outcome detection wired (spec 033): email-reply within 7d / Opportunity Closed Won/Lost / no-movement-30d.
- [ ] Langfuse trace per Customer scanned; per-fire trace shows the signal evaluations consulted.

## Tests

- **Unit:** risk-scoring function with fixture signal-states.
- **Integration:** real Customer with mock renewal Opportunity + fixture signals → action-suggested emitted.
- **Golden-trace:** for known fixture state, the email draft includes a specific renewal-window mention and references the right number of signals.

## Signal definitions involved

Per skill 03's "Owned signals" cross-reference: primary trigger `churn_signal_renewal_period_silence_v1`; composers `churn_signal_contact_disengagement_v1`, `churn_signal_sentiment_decline_v1`, `churn_signal_competitor_mention_v1`; account context `client_termination_pattern_v1`, `account_silence_pattern_v1`; read-only `escalation_signal_case_pattern_v1`, `escalation_signal_severity_jump_v1`.

## Open questions

- Q56 (champion identification), Q57 (risk-weight tuning), Q58 (Opportunity.Type enum) — all in `99_open_questions.md`.

## What this is NOT

- Not the renewal-touch dispatch — spec 032.
- Not the outcome tracking — spec 033 / Layer 8 Mechanism 3 (spec 045).

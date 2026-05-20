# Spec 028 — Skill 11 — detect-expansion-intent-from-job-posting

**Maps to:** §14 Skills (Skill 11); `01_design/skills/11-detect-expansion-intent-from-job-posting.md`; Spike 4 §Q4; §13.5 new row; §13.6 #10.
**Depends on:** specs 005, 006, 008, 009, 015 (opp-tracker adapter), 029 (Per-Profile Markdown for personalization).
**Effort:** 0.75 day.

## Description

Per `01_design/skills/11-detect-expansion-intent-from-job-posting.md`. Episode-driven on opportunity-tracker Episodes (after spec 015 ingestion + spec 016 precision fix). Composes outreach to the customer's champion contact with placed-talent context layered in from Graphiti.

## Inputs

- opportunity-tracker Episodes (tier ∈ {hottest, warm}; matched_role ≠ null; work_arrangement ≠ on-site).
- `get_customer_context` for placed-talent count + recent health.
- Customer Per-Profile Markdown for personalization.
- `expansion_signal_verbal_capacity_mention_v1` (compositional consumer — Q134).

## Outputs

- `03_build/pulse/skills/skill_11_detect_expansion_intent.py`.
- Per fire: `action-suggested` with email_draft + sfdc_task. Composes verbal+posting evidence into one card per Q134.

## Definition of Done

- [ ] Trigger conditions per Skill 11 spec strictly applied (off-scope episodes never enter; matched_role null skipped; on-site work_arrangement skipped).
- [ ] Composition with verbal mention: same-customer-same-window → single card.
- [ ] Tier variants enforced (SMB warm auto-approve; Mid+ human-required; Enterprise cc VP-CS + static EBR-tie-in copy per Mitigation B / Decision 41).
- [ ] 14-day rate-limit per Customer.
- [ ] Outcome detection: Opportunity created within 30d → outcome-recorded.

## Tests

- **Unit:** trigger filter; composition logic; tier-variant envelope.
- **Integration:** opp-tracker fixture row → Episode → Skill 11 → action card with placed-talent context.
- **Composition:** verbal-mention + posting-match same-customer-same-window → one card not two.

## Signal definitions involved

Per skill 11 cross-reference: primary `expansion_signal_job_posting_match_v1`; compositional `expansion_signal_verbal_capacity_mention_v1`.

## Open questions

Q118-Q125 (all opp-tracker dispositions in `99_open_questions.md`).

## What this is NOT

- Not the matcher (spec 016 — in opp-tracker repo).
- Not the adapter (spec 015 — Pulse-side normalizer).
- Not where the EBR-tie-in copy template lives — that's a prompt fragment in `prompts/skill_11_*.txt`.

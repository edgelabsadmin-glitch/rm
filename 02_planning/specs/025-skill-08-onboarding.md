# Spec 025 — Skill 08 — onboarding

**Maps to:** §14 Skills (Skill 08); `01_design/skills/08-onboarding.md`; §13.5 row "Kickoff calls with new customers."
**Depends on:** specs 005, 006, 008, 009, 012.
**Effort:** 0.5 day.

## Description

Per `01_design/skills/08-onboarding.md`. Episode-driven on (a) new Account stage transition to "Customer" / "Active" (Q71); (b) Associates__c first-time Stage=Active. Two sub-trigger paths produce two action types (kickoff-call action for new customer; placement-launch action for new talent).

## Inputs

- SFDC Episode-trigger events.
- Customer / Talent profile (may be sparse for net-new).

## Outputs

- `03_build/pulse/skills/skill_08_onboarding.py`.
- Per fire: `action-suggested` (kickoff or placement-launch type).

## Definition of Done

- [ ] Fires once per entity (subsequent Stage=Active re-entries don't re-trigger).
- [ ] No contractual content drafted (per guardrail).
- [ ] Calendar hold *suggestion* only (no auto-booking; Q73 v1.5+).
- [ ] Tier-aware variants (SMB single-touch; Mid+ kickoff + SFDC Task + calendar hold; Enterprise cc VP-CS).

## Tests

- **Unit:** trigger-once enforcement; sub-trigger routing.
- **Integration:** new SFDC Account stage transition → kickoff action emitted; subsequent re-entry → no fire.

## Signal definitions involved

None — structural-event-driven; no Signal Definition Library entry (Q147 v1.5+ consolidation).

## Open questions

Q71 (Account stage enum), Q72 (Start_Date semantics), Q73 (calendar hold mechanism) — disposed.

## What this is NOT

- Not where the talent's 90/60/30-day check-ins schedule — that's Skill 04 (cadence-driven).

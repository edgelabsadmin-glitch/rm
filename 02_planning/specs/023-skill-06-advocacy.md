# Spec 023 — Skill 06 — advocacy

**Maps to:** §14 Skills (Skill 06); `01_design/skills/06-advocacy.md`; §13.5 row "Recognition + advocacy programs"; §13.4 "ambassadors at Vertex" query.
**Depends on:** specs 005, 006, 008, 009, 017, 020.
**Effort:** 0.5 day.

## Description

Per `01_design/skills/06-advocacy.md`. Schedule-driven (weekly Monday 09:00). Scans last 30 days of positive-signal episodes per Customer; surfaces ambassador candidates from `recognition_signal_advocacy_candidate_v1`.

## Inputs

- Weekly Monday schedule.
- `recognition_signal_advocacy_candidate_v1` evaluations.
- Customer profile + advocacy history (track 12-month no-ask guardrail).

## Outputs

- `03_build/pulse/skills/skill_06_advocacy.py`.
- Per qualified customer: `action-suggested` with proposed_motion (recognition/reference-call/case-study).

## Definition of Done

- [ ] Disqualifier list enforced (active risk Cases of `Risk - Talent Competency`, `Risk - Resignation`, `Risk - Customer Payment Failure`, `Poor Experience with Edge`, `Competitor`).
- [ ] 12-month no-ask guardrail enforced.
- [ ] One advocacy action per Customer per quarter.
- [ ] Tier-aware motion selection (SMB recognition-only; Mid/Ent reference-call/case-study).
- [ ] Coordination with Skill 07 via shared rate-limit (Q67).

## Tests

- **Unit:** disqualifier list; rate-limit; motion selection by score + tier.
- **Integration:** customer with 4 positive quotes + healthy state → action emitted; customer with 1 open risk case → no fire.

## Signal definitions involved

Per skill 06 cross-reference: primary `recognition_signal_advocacy_candidate_v1`.

## Open questions

Q65-Q67 disposed; Q141 (Advocacy_Participation_History__c field) — pending Q21.

## What this is NOT

- Not Skill 07 (recognition is single-event; advocacy is portfolio-level).
- Not case-study artifact generation (v1.5+).

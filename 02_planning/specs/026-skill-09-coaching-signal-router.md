# Spec 026 — Skill 09 — coaching-signal-router

**Maps to:** §14 Skills (Skill 09); `01_design/skills/09-coaching-signal-router.md`; §13.5 row "Coach Talent for long-term success."
**Depends on:** specs 005, 006, 008, 009, 017, 020, 022 (Skill 05 deconfliction).
**Effort:** 0.5 day.

## Description

Per `01_design/skills/09-coaching-signal-router.md`. Routes talent growth + developmental concerns to Talent Dev. Distinct from Skill 05 (which routes *issues*) via the developmental-vs-deficit distinction. Privacy posture: pay-concern context mentioned generically; specific dollar figures stripped from why_oneline.

## Inputs

- Skill 01 outputs (welfare signals).
- Risk-tagged Cases of `Performance` / `Risk - Talent Competency`.
- Skill 04's talent-care outcomes (coaching-relevant themes surfaced in quarterly check-ins).

## Outputs

- `03_build/pulse/skills/skill_09_coaching_signal_router.py`.
- Per fire: `action-suggested` with email_draft to Talent Dev + SFDC Task.

## Definition of Done

- [ ] Developmental tone preserved (warm; not deficit-flavored).
- [ ] Privacy guardrail: pay-related triggers fire, but why_oneline scrubs $ figures (per Q137).
- [ ] Deconfliction with Skill 05 via shared (case_id, dispatch_week) rate-limit.
- [ ] Skip Replaced/Terminated stage.

## Tests

- **Unit:** privacy scrub on $ figures; dedup with Skill 05.
- **Integration:** burnout-high + same case → Skill 09 + Skill 05 both fire; rate-limit prevents both dispatching same week.

## Signal definitions involved

Per skill 09 cross-reference: primary `talent_growth_concern_v1`; high-severity cascade `talent_burnout_signal_v1`; read-only `talent_pay_concern_v1`.

## Open questions

Q74 (Talent Dev structure), Q75 (career-pathing data shape), Q76 (Skill 05/09 deconfliction) — disposed.

## What this is NOT

- Not Skill 04 (Skill 04 = check-in cadence; Skill 09 = developmental routing).
- Not Skill 05 (Skill 05 = issues; Skill 09 = growth).

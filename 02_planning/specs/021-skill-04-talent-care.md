# Spec 021 — Skill 04 — talent-care

**Maps to:** §14 Skills (Skill 04); `01_design/skills/04-talent-care.md`; §13.5 row "Quarterly check-ins, no slippage."
**Depends on:** specs 005, 006, 008, 009, 017, 020, 029.
**Effort:** 0.5 day.

## Description

Per `01_design/skills/04-talent-care.md`. Schedule-driven (hourly) — scans Active Associates; fires on talent overdue against cadence (90-day default; tighter for Mid/Enterprise placements) OR on welfare signals from spec 020.

## Inputs

- Hourly schedule trigger.
- `get_talent_context()`, Per-Profile Markdown.
- Welfare signals: `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1`.

## Outputs

- `03_build/pulse/skills/skill_04_talent_care.py`.
- Per overdue talent: `action-suggested` with email draft + SFDC Task.

## Definition of Done

- [ ] Cadence rule + welfare-signal-trigger both work (each tested independently).
- [ ] Rate-limit: one action per Talent per 30 days.
- [ ] Guardrails per Skill 04 spec (no customer-side concerns mentioned to talent; no actions for Replaced/Terminated stage).
- [ ] Tier variants enforced.
- [ ] Langfuse-traced.

## Tests

- **Unit:** cadence calculation; rate-limit enforcement.
- **Integration:** hourly tick fires for a talent overdue by 91 days; action emitted.
- **Negative:** talent with `Stage=Replaced` does not trigger.

## Signal definitions involved

Per skill 04 cross-reference: primary `talent_burnout_signal_v1`; co-consumers `talent_growth_concern_v1`, `talent_pay_concern_v1`.

## Open questions

Q59-Q61 disposed.

## What this is NOT

- Not Skill 09 (coaching handoff is a separate skill, can fire concurrently with Skill 04 per spec 026).

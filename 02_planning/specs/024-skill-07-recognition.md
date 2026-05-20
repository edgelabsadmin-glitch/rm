# Spec 024 — Skill 07 — recognition

**Maps to:** §14 Skills (Skill 07); `01_design/skills/07-recognition.md`; §13.5 row "Recognition + advocacy programs."
**Depends on:** specs 005, 006, 008, 009, 020, 023 (coordination with Skill 06).
**Effort:** 0.5 day.

## Description

Per `01_design/skills/07-recognition.md`. Episode-driven on positive-signal events (Skill 01's `positive_quote` tag), milestone events (placement anniversaries), resolved risk-tagged Cases, and positive customer-reply detection. Drafts short warm recognition notes — three audience types (customer / talent / RM).

## Inputs

- Episode-driven triggers per Skill 07 spec.
- `get_customer_context` / `get_talent_context` / `get_rm_context`.
- Skill 06's shared rate-limit table (per Q67).

## Outputs

- `03_build/pulse/skills/skill_07_recognition.py`.
- Per fire: `action-suggested` with email_draft (audience-specific).

## Definition of Done

- [ ] Three audience types supported; per-audience prompt templates in `prompts/skill_07_*.txt`.
- [ ] Guardrails: no recognition during active risk Cases; no <30d talent recognition; no >1/week RM recognition.
- [ ] Auto-approve at +1h for SMB/Mid; Enterprise customer-facing human-required.
- [ ] Coordination with Skill 06 via shared rate-limit.

## Tests

- **Unit:** trigger filtering; rate-limit; audience-selection.
- **Integration:** ingest a positive_quote-bearing Episode → recognition action emitted; ingest during active risk Case → suppressed.

## Signal definitions involved

Skill 07 reads `recognition_signal_advocacy_candidate_v1` for Skill 06 coordination; otherwise fires on structural events (Q146 disposition).

## Open questions

Q68-Q70 disposed; Q146 (recognition_signal_v1 consolidation) v1.5+.

## What this is NOT

- Not Skill 06 (per Q67 — Skill 06 owns portfolio motions, Skill 07 owns moments).

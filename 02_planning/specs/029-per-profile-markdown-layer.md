# Spec 029 — Per-Profile Markdown Layer

**Maps to:** §14 UI surfaces; Design 06; §13.5 row "Document customer workflows, Talent feedback, success plans"; §13.6 #2.
**Depends on:** specs 001, 008.
**Effort:** 1.0 day.

## Description

Per Design 06. Postgres `profiles` table; auto-regeneration on signal events; RM-edit override with side-by-side diff workflow on re-merge.

## Inputs

- Episodes + signal events from the event log.
- Customer / Talent / RM entities.
- Claude Opus (premium model) for narrative regeneration.

## Outputs

- Migration creating `pulse.profiles` per Design 06 schema.
- `03_build/pulse/core/profiles/loader.py` + `regenerator.py` + `editor.py`.
- API endpoints: `GET /profiles/<type>/<id>`, `PUT /profiles/<type>/<id>` (RM-edit; emits `profile-edited` event).
- Background job (Activepieces flow) for regeneration on event triggers per Design 06 §"Regeneration cadence."

## Definition of Done

- [ ] Three profile types (customer / talent / rm) loadable.
- [ ] Auto-regeneration triggers per Design 06 table (≥5 new episodes / `urgency=high` event / weekly fallback).
- [ ] Override semantics per Design 06 §"Edit semantics" — RM edit preserved; "profile re-merge needed" Action Queue card surfaces when fresh content diverges from `override_source_md`.
- [ ] No staleness signal in Phase 1 UI (Q84 — v1.5+); Phase 1 just renders `last_regenerated_at` on the profile.

## Tests

- **Unit:** override-preservation logic; diff generation.
- **Integration:** ingest 5 Episodes → regenerator fires; assert profile content updated.
- **Edit flow:** RM edits a profile → override_active=true; subsequent regenerator preserves edit until divergence threshold.

## Signal definitions involved

Per `account_silence_pattern_v1` — regenerator fires the data-gap layer-8 event.

## Open questions

Q80-Q84 disposed.

## What this is NOT

- Not where customer-facing emails come from (skills generate; profiles inform).
- Not version-controlled in git (Postgres-stored).

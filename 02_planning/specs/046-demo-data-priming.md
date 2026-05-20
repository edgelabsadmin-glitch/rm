# Spec 046 — Demo data priming script

**Maps to:** §14 Demo deliverables; Design 12 §"Demo-day data priming"; Risk 3 mitigation.
**Depends on:** specs 011-016 (all adapters), 029 (profiles).
**Effort:** 0.5 day.

## Description

Per Design 12 §"Demo-day data priming." Script that ensures the demo storyboard's reference accounts (**DHR Health Clinics + Mendota Insurance + Cirventis (HelixVM)**, recon-verified Session 13) have sufficient signal density for each scene. Phase 1 fallback: synthetic substitute data if production data is sparse. (Anchors swapped from Acrisure + Pinnacle per Session 13 recon — those lacked usable production data.)

## Inputs

- Real production data (preferred per Decision 16).
- Synthetic seed (the Spike 3 dataset is the basis if needed).

## Outputs

- `03_build/scripts/demo_prime.py` — idempotent priming script.
- Documentation in `docs/demo_priming.md` describing what the script does + when to run it.

## Definition of Done

- [ ] Script runs idempotently; running twice doesn't double-seed.
- [ ] Verifies DHR Health Clinics + Mendota Insurance exist and have ≥10 episodes each + a recent renewal Opportunity + ≥1 risk-tagged Case (recon confirmed: DHR 76 talent / 45 cases, Mendota 42 talent). Cirventis (HelixVM) verified for the §13.4 AI-displacement query scene.
- [ ] If any account is missing data, synthesizes plausible Episodes (clearly tagged as synthetic per audit trail).
- [ ] Verifies all 11 skills can fire at least once on the demo data set.

## Tests

- **Manual:** run on demo-day morning; observe Action Queue populated.

## Signal definitions involved

None directly — exercises every signal indirectly via fire-coverage check.

## Open questions

Q109 (live data vs staging — production preferred), Q110 (rehearsal cadence) — disposed.

## What this is NOT

- Not the demo storyboard execution (that's spec 047 + Design 12).
- Not where demo data lives in production — script reads/writes Pulse's own DB; SFDC writes only via §6 rule 6 path.

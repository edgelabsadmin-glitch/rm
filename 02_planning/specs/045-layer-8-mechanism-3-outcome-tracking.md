# Spec 045 — Layer 8 Mechanism 3 — Outcome tracking + action effectiveness

**Maps to:** §14 Layer 8 (Mechanism 3); Decision 37; §13.5 "Track issues, resolutions, outcomes."
**Depends on:** specs 033 (outcome watchers), 044 (Mechanism 1 surface for cross-link).
**Effort:** 1.5 days. *(Revised Session 14 from 1.0d — absorbs the 0.5d synthetic action-outcome seed, formerly proposed as separate spec 045a. See §"Sub-task: Synthetic action-outcome seed (folded from 045a)" below.)*

## Description

Per Decision 37 Option B. Admin surface for outcome tracking + action effectiveness. Powers the demo's "Pulse on day 90 vs day 1" narrative.

**Seeding premise correction (Session 13 recon).** The original Risk-4 mitigation assumed rm-intelligence-agent had ~3 months of *action-outcome* history to seed from. The demo data recon (`00_research/spikes/05_demo_data_recon.md`) disproved this: rm-intelligence-agent is a **one-time snapshot, not a run history, and it never dispatched actions** — so it has *zero* historical action-outcome chains. Mechanism 3 therefore cannot be seeded from real history. It is seeded **synthetically** instead (see sub-task below), with all seeded events tagged `source='synthetic_seed'` so the admin can distinguish synthetic from real. Production cutover stops the synthetic seed and lets real events accumulate.

## Inputs

- `action-executed`, `outcome-recorded`, `outcome-missing` events from spec 033.
- `rm-intelligence-agent/data/meeting_signals.jsonl` — 367 meeting-signal records, 12-month span — used as the *timeline scaffold* for synthetic action-outcome generation (not as real action history).

## Outputs

- Postgres views aggregating per-skill per-week effectiveness metrics.
- Admin surface at `/admin/outcomes` rendering: outcomes-recorded / actions-dispatched ratio per skill; trend over weeks; cross-link to Mechanism 1 for per-signal breakdown.
- The synthetic action-outcome seed script (sub-task below).

## Sub-task: Synthetic action-outcome seed (folded from 045a, Session 13/14)

A seed script (`03_build/scripts/seed_synthetic_outcomes.py`) that:
- Reads `rm-intelligence-agent/data/meeting_signals.jsonl` for timestamps + signal types (the scaffold).
- For each high-severity signal instance, synthesizes a plausible action lifecycle chain at the original timestamp: `action-suggested` → distribution {70% `action-approved`, 20% `action-rejected`, 10% `action-expired`}; for approves, {50% `outcome-recorded`, 50% `outcome-missing`}.
- Maps each signal type to the owning skill per the `01_design/skills/` cross-references, so per-skill effectiveness metrics populate believably.
- Tags every synthetic event `source='synthetic_seed'`.
- Is idempotent (re-running clears prior synthetic events first, keyed on the tag).
- **Excludes the test-account denylist (§6 rule 33)** — `Test Account` (`0016S00003UGpijQAD`) and any future test accounts produce no synthetic events.

## Definition of Done

- [ ] Effectiveness metrics computed per skill across configurable time window.
- [ ] Trend visualization (sparkline per skill).
- [ ] Cross-link from Mechanism 1's "outcome rate" column → Mechanism 3's per-skill detail.
- [ ] **Synthetic seed produces realistic data for demo day** — Mechanism 3 surface is populated, not empty, with clearly-tagged synthetic events.
- [ ] Synthetic events are distinguishable from real (`source='synthetic_seed'`); a single admin toggle hides them.
- [ ] Test-account denylist honored in the seed.
- [ ] Admin-only access.

## Tests

- **Unit:** metric computation; synthetic-seed distribution (70/20/10; 50/50) within tolerance over N samples.
- **Integration:** dispatch a real action → outcome event → metric updated alongside synthetic baseline.
- **Synthetic seed:** verify seeded data renders coherently in the surface; verify `source='synthetic_seed'` tag on every seeded row; verify idempotency (re-run doesn't double-count); verify test-account exclusion.

## Signal definitions involved

Reads outcomes per the action lifecycle; no direct signal-definition role.

## Open questions

None.

## What this is NOT

- Not Mechanism 1 (spec 044 — signal performance, separate surface).
- Not Mechanism 2 (per-RM preference learning — v1.5+).
- Not where outcomes are detected (spec 033).

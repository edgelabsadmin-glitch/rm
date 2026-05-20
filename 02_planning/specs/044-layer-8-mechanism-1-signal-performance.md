# Spec 044 — Layer 8 Mechanism 1 — Signal Performance metrics admin surface

**Maps to:** §14 Layer 8 (Mechanism 1); Decision 37; §6 rule 8 (no black-box — performance metrics complete the inspectability loop).
**Depends on:** specs 008 (event log), 017 (signal library runtime), 042 (admin RBAC).
**Effort:** 1.5 days.

## Description

Per Decision 37 Option B. Admin surface showing per-signal performance: fire rate, action-approval rate, outcome rate, false-positive code rate (from RM rejections coded as "wrong signal"). Powers signal tuning — when an admin sees a signal over-fires + gets rejected ≥3x in 14d, the policy module's dampening rule fires (spec 009 rule 4).

## Inputs

- Event log (spec 008): all `signal-evaluated`, `action-suggested`, `action-approved`, `action-rejected`, `outcome-recorded`, `outcome-missing` events.
- `account_silence_pattern_v1` `layer8_data_gap` events.
- The 14 signal definitions' "Performance metrics" sections (which this surface populates).

## Outputs

- Postgres views aggregating per-signal-per-week metrics.
- Admin surface at `/admin/signal-performance` rendering the metrics.
- A "tune this signal" action that updates the Phase 1 policy module's adjustable parameters per signal definition's "Adjustability" table.

## Definition of Done

- [ ] Per-signal metrics computed correctly from the event log.
- [ ] Surface shows: fire rate, approval rate, outcome rate, false-positive rate, last-tuned timestamp.
- [ ] Layer 8 data-gap events surface in a separate "data gaps" pane.
- [ ] Admin-only access (spec 042).
- [ ] Tuning a signal's parameter emits `signal-tuned` event; new parameter immediately effective on next evaluation.

## Tests

- **Unit:** metric computation correctness.
- **Integration:** seed events for 1 signal across a week → metrics populate correctly.
- **RBAC:** RM-tier user receives 403.

## Signal definitions involved

All 14 — this surface is the canonical writer of the "Performance metrics" section.

## Open questions

None new.

## What this is NOT

- Not Mechanism 2 (per-RM preference learning — v1.5+ per §12 #12).
- Not where signals are *defined* (`02_planning/signals/*.md` is authority).

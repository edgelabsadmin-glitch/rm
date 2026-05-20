# Spec 030 — Dual-Sided account health rollup

**Maps to:** §14 UI surfaces (driver for hero card + Constellation); Design 07; §13.5 "Cohesive customer + Talent experience"; §13.6 #4.
**Depends on:** specs 005, 006, 008, 012, 017, 020.
**Effort:** 0.75 day.

## Description

Per Design 07. Composes per-Account health from customer-side signals + talent-side signals, weighted by tier (α/β per Design 07 §"The composition formula"). Health-tier-change events emit on transitions.

## Inputs

- Customer-side signals: RM_Outreach__c health fields, open risk-tagged Cases (customer-side), churn signals, sentiment trajectory.
- Talent-side signals: replacement rate, talent-Case load, welfare signal severity, talent-care cadence compliance.
- `Account.Segment__c` for α/β weights.

## Outputs

- Migration creating `pulse.account_health` cache table.
- `03_build/pulse/core/health/dual_sided.py` exporting `async def compute(account_id) -> AccountHealth`.
- `health-tier-changed` event emitted on transitions (with ≥24h debounce per Q88).

## Definition of Done

- [ ] Formula per Design 07 §"The composition formula" implemented verbatim.
- [ ] Per-Account `compute()` returns AccountHealth with tier + component scores + top-3 contributing signals.
- [ ] Triggered recompute on event-log fan-out within 5 minutes.
- [ ] Nightly recompute at 02:00 local as safety net.
- [ ] Health-tier-change debouncing (≥24h hold) prevents oscillation noise.
- [ ] Langfuse-traced.

## Tests

- **Unit:** formula correctness across each tier with fixture signals.
- **Integration:** signal fires → health recompute within 5 min → cache updated.
- **Debounce:** rapid signal noise → tier changes only after 24h sustained delta.

## Signal definitions involved

Reads many; primary inputs are the customer-side and talent-side signal families described in Design 07.

## Open questions

Q85-Q89 disposed; Q86 (Customer_Health__c picklist enum) pending Q21.

## What this is NOT

- Not a predictive model (no ML; current-state composite per Design 07).
- Not where the conic-gradient health ring renders (UI specs — 036).

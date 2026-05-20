# Spec 042 — Three-Tier Role Model + RBAC enforcement

**Maps to:** §14 (Three-tier role model with RBAC enforcement); Design 09; §13.5 "Effective communication channels"; §6 rule 7 (SFDC ownership drives scope).
**Depends on:** specs 001, 008, 012 (SFDC Account.OwnerId for RM identification).
**Effort:** 0.75 day.

## Description

Per Design 09. Admin / Manager / RM tiers + Overall view. Scope derived from SFDC ownership via `derive_scope(user)` function. Single chokepoint enforcement via `@scope_required` decorator on every retriever + event-log query.

## Inputs

- Authenticated user identity (spec 043).
- SFDC Account.OwnerId data (spec 012).
- `pulse_managers.yaml` config for Manager → direct-reports mapping (Q95).

## Outputs

- `03_build/pulse/core/auth/scope.py` exporting `derive_scope(user) -> Scope`.
- `@scope_required` decorator wrapping all retrievers.
- Overall-view filter logic per Design 09 §"The Overall view's filtering rules."

## Definition of Done

- [ ] Admin sees all entities; Manager sees direct-reports' books + their own; RM sees own book.
- [ ] Cross-tier disallowed access returns 403.
- [ ] Overall view filters per Design 09 §"The Overall view's filtering rules" (aggregates visible; specific-customer-escalation details RM-scoped).
- [ ] Audit log records every authorized + denied access per Design 09 §"Enforcement layer."
- [ ] Scope refresh latency: ~5 min from SFDC ownership change (per Q99 disposition).

## Tests

- **Unit:** scope derivation for each tier.
- **Integration:** RM-A cannot read RM-B's customer profile (403); RM-A's Manager can.
- **Negative:** non-EDGE-domain user rejected at auth.

## Signal definitions involved

None.

## Open questions

Q95 (manager hierarchy yaml), Q96 (VP-CS role mapping), Q97 (cross-RM collaboration v1.5+), Q98 (audit-log access for Managers), Q99 (departures cadence) — disposed.

## What this is NOT

- Not OAuth (spec 043 — auth identity establishment).
- Not the kill switch (spec 010 — different governance mechanism).

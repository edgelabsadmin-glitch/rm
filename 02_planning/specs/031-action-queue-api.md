# Spec 031 — Action Queue API (back-end routes)

**Maps to:** §14 UI surfaces (Action Queue); Design 03; §13.2 row "Push structured data to Salesforce" (the gated write path); §13.6 #1.
**Depends on:** specs 008, 009, 010, plus all skill specs that emit action-suggested events.
**Effort:** 1.0 day.

## Description

Implement the API surface that the Action Queue UI consumes. List/approve/modify/reject/expire endpoints. Authorization-aware per spec 042 RBAC.

## Inputs

- `action-suggested` events from skills.
- `pulse.events` table for the action-state lifecycle.
- Policy module decisions (which actions need human approval).
- RBAC scope from spec 042.

## Outputs

- FastAPI router `03_build/pulse/api/actions/`:
  - `GET /actions` — list pending actions for the calling user's scope.
  - `GET /actions/{id}` — detail (full reasoning).
  - `POST /actions/{id}/approve` — emits `action-approved` event; triggers dispatch (spec 032).
  - `POST /actions/{id}/modify` — emits `action-modified-and-approved`; dispatches.
  - `POST /actions/{id}/reject` — emits `action-rejected` event with reason picker.

## Definition of Done

- [ ] All endpoints async per ADR-001.
- [ ] Pagination + sorting by ranking-score per Design 03 §"Ranking logic."
- [ ] Filter chips (tier / customer / skill / owner) implemented as query params.
- [ ] Scope enforcement per spec 042 (RM sees own; Manager sees direct reports; Admin sees all).
- [ ] Modify flow: only `modifiable_fields` editable; non-modifiable fields rejected with 400.
- [ ] Audit log: every endpoint call emits an event.
- [ ] Langfuse-traced.

## Tests

- **Unit:** endpoint validation + ranking-score sort.
- **Integration:** suggest → list → approve → action-executed event chain.
- **RBAC:** RM cannot approve another RM's actions; verified by 403 response.

## Signal definitions involved

None directly — the API operates on the action lifecycle.

## Open questions

Q36 (filter persistence — localStorage), Q37 (bulk approve — v1.5+), Q38 (high-urgency notification escalation), Q39 (history depth — 90d in-UI) — disposed.

## What this is NOT

- Not the front-end (spec 035 consumes this API).
- Not the dispatch handlers (spec 032).

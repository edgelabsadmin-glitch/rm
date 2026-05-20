# Spec 010 — Kill switch + admin config plumbing

**Maps to:** §14 Infrastructure; Design 04 §"Kill switch"; §6 rule 14.
**Depends on:** specs 008, 009.
**Effort:** 0.25 day.

## Description

Implement the kill switch per Design 04. Single boolean in `pulse_settings` + per-scope overrides JSONB. When `global == true`, the policy module returns `block` for every suggestion + emits a `policy-decision` event with `decision=block, reason='kill_switch_global'`. Admin UI surface comes later (spec 044); spec 010 ships the backend API (`POST /admin/kill-switch` with auth) + the policy integration.

## Inputs

- `pulse_settings` table from spec 009.
- The policy module from spec 009.

## Outputs

- `03_build/pulse/api/admin/kill_switch.py` — FastAPI router exposing `GET /admin/kill-switch` (read state) and `POST /admin/kill-switch` (toggle, admin-auth-only).
- `03_build/pulse/core/policy/kill_switch.py` — read interface that `policy_decide` calls.
- A `kill-switch-flipped` event emitted on every toggle.

## Definition of Done

- [ ] Endpoint exists, returns state; toggle works (admin-auth-only verified via spec 042/043).
- [ ] Toggle emits `kill-switch-flipped` event with `user_id` + `scope` + `on_or_off`.
- [ ] Per-skill kill switch supported: `{"global": false, "by_skill": {"renewal-watcher": true}}` blocks only that skill.
- [ ] Per-customer kill switch supported (same JSONB structure).
- [ ] Unit test verifies `policy_decide` returns `block` when kill switch is on; emits the right event.

## Tests

- **Unit:** `policy_decide` honors kill switch; toggle emits event.
- **Integration:** `POST /admin/kill-switch` round-trip with admin auth header.
- **Negative:** non-admin caller receives 403.

## Signal definitions involved

None.

## Open questions

None.

## What this is NOT

- Not the admin UI for the kill switch (that's spec 044 Layer 8 admin surface).
- Not a feature flag system (the kill switch is operational, not feature-level).

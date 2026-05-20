# Spec 009 — Policy module + tier-aware approval matrix

**Maps to:** §14 Infrastructure (event log + policy); Design 04 §"Policy module"; §6 rule 4 (tier-aware behavior).
**Depends on:** spec 008.
**Effort:** 0.75 day.

## Description

Implement the policy module per Design 04. Phase 1 = Python code with OPA-shape inputs/outputs (per Design 04 — defers OPA proper to v1.5+). Function signature: `policy_decide(suggestion: ActionSuggested) -> PolicyDecision` returning one of `{auto-approve, require-human, block}` with the thresholds applied. Side effect: emits `policy-decision` event to the event log.

Phase 1 policy rules from Design 04 §"Phase 1 policy rules" implemented verbatim:
1. Enterprise tier → always require-human.
2. Urgency=high → always require-human regardless of tier.
3. Skill `recognition` → auto-approve at +1h delay across tiers.
4. Skill with ≥3 rejections in last 14d → require-human + flag for tuning.
5. Global kill switch on → block.
6. SMB tier AND skill in SMB auto-approve list → auto-approve at +1h.
7. Otherwise → require-human.

## Inputs

- `ActionSuggested` payload from a skill (per Design 04 enum).
- The current global kill-switch state (spec 010).
- The `pulse_settings` table for auto-approve list + dampening counters.

## Outputs

- `03_build/pulse/core/policy/decide.py` exporting `async def policy_decide(suggestion) -> PolicyDecision`.
- A `pulse_settings` table created via Postgres migration (kill switch boolean + per-skill auto-approve list as JSONB + per-skill rejection counter as JSONB).

## Definition of Done

- [ ] All 7 Phase-1 policy rules implemented; each has a dedicated unit test verifying correct decision under each combination of tier + urgency + skill + global state.
- [ ] Function emits `policy-decision` event for every call (verified via integration test).
- [ ] Function is async per ADR-001.
- [ ] Langfuse-instrumented.
- [ ] Rejection counter incremented by `action-rejected` event emission (cross-references Design 04 rule 4); decremented by `action-rejected.expires_at > 14d` cleanup job (spec 045 picks this up).

## Tests

- **Unit:** 7 tests, one per rule; plus combination tests for cascade order.
- **Integration:** suggest a high-urgency Enterprise action → policy returns require-human + emits the event.

## Signal definitions involved

None directly — policy operates on `ActionSuggested` payloads which carry signal references.

## Open questions

- Q44 disposition (Phase 1 = Python, v1.5+ = OPA) is recorded. Phase 1 rule functions are written with OPA-shape signatures for mechanical future migration.

## What this is NOT

- Not the kill switch (spec 010) — policy reads kill switch state; doesn't own it.
- Not the Action Queue (spec 031) — policy decides before the queue sees the action.
- Not OPA (v1.5+ migration).

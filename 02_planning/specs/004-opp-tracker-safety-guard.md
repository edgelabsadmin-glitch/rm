# Spec 004 — opportunity-tracker `sf_tasks.push_to_salesforce()` safety guard

**Maps to:** §14 Phase-4-Day-1 tasks; Q121 (filed during Spike 4).
**Depends on:** none in Pulse's repo (this is a PR against the opportunity-tracker repo).
**Effort:** 0.25 day.

## Description

opportunity-tracker's `src/sf_tasks.py:79::push_to_salesforce()` is a Phase-2 placeholder that, if activated, would create SFDC Tasks directly from the daily scan — violating §6 rule 6 (Salesforce write-back only through Action Queue with explicit approval). Spec 004 adds a runtime safety guard: the function raises `RuntimeError` unless the explicit env var `PULSE_ALLOW_OPP_TRACKER_SFDC_WRITE=true` is set.

Why: the placeholder exists as live code; someone could accidentally activate it. The guard makes accidental activation impossible without a deliberate config flag. PM Spike 4 §Q121 disposition confirms.

This spec executes against the **opportunity-tracker repo** (separate from Pulse's `03_build/`). The result is a PR to that repo, not code in Pulse's repo.

## Inputs

- Write access to the opportunity-tracker repo.
- The current `src/sf_tasks.py` content (read during Spike 4).

## Outputs

- A PR against opportunity-tracker modifying `src/sf_tasks.py::push_to_salesforce()` to:
  1. Check for `os.environ.get("PULSE_ALLOW_OPP_TRACKER_SFDC_WRITE") == "true"` as a precondition.
  2. Raise `RuntimeError("opp-tracker SFDC write disabled per Pulse §6 rule 6; set PULSE_ALLOW_OPP_TRACKER_SFDC_WRITE=true to override")` if the env var is unset or false.
  3. Add a clear docstring noting the deprecation rationale and the Pulse Action Queue as the canonical write path.
- An updated docstring at the module level explaining the design intent.
- A small unit test in opportunity-tracker's test suite asserting the safety guard fires correctly.

## Definition of Done

- [ ] PR opened against opportunity-tracker repo with the above changes.
- [ ] PR merged (user-side approval).
- [ ] CI in opportunity-tracker passes including the new unit test.
- [ ] `PULSE_ALLOW_OPP_TRACKER_SFDC_WRITE` is NOT set in any opportunity-tracker production environment (verified by user).

## Tests

- **Unit (in opp-tracker):** `test_push_to_salesforce_raises_without_guard_flag`; `test_push_to_salesforce_runs_with_guard_flag` (mocked SFDC client).

## Signal definitions involved

None.

## Open questions

None.

## What this is NOT

- Not a removal of the function. The placeholder remains for future re-activation if/when Pulse's Action Queue absorbs opp-tracker outputs and a deliberate decision is made to re-route.
- Not a change to opportunity-tracker's daily scan behavior — only the dormant write path is guarded.

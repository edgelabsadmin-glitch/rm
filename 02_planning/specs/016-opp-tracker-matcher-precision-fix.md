# Spec 016 — opportunity-tracker matcher precision fix

**Maps to:** §14 Signal sources (opportunity-tracker); Spike 4 §Q2 (the three changes); Q118, Q119, Q120.
**Depends on:** none in Pulse's repo (spec 016 is PRs against opportunity-tracker).
**Effort:** 1.0 day.

## Description

Three concrete code-level changes against opportunity-tracker per Spike 4 §2.4, addressing the "Nurse, etc." in-person-only false-positive surface:

**Change A — Catalog schema upgrade.** Promote `config/role-catalog.json` from flat strings to typed objects: `{name, remote_compatible, in_person_disqualifiers, aliases}`. All current 53 roles get `remote_compatible=true` by default; field is future-proofing. Loader update in `src/matcher.py:11-13` and `:40-54`.

**Change B — Posting-level filter via AI prompt.** Extend `src/ai_matcher.py:44-65` prompt to instruct the model to classify `work_arrangement` (`remote`/`hybrid`/`on-site`/`unspecified`) and return `tier='off-scope'` for on-site-only postings. Add `off-scope` as a tier value across `matcher.py`, `state.py`, `dashboard/app.py`.

**Change C — Source narrowing.** `src/scanners/jobboard_scanner.py:77` — change `site_name=["indeed", "linkedin", "glassdoor", "google"]` to `["indeed", "linkedin"]`.

## Inputs

- Spike 4 §2.4's three concrete changes.
- Q118 disposition (sources to keep).
- Q119 disposition (full schema restructure, not parallel file).
- Q120 disposition (off-scope as a fourth tier).

## Outputs

- Three PRs (or one bundled PR with three commits) against opportunity-tracker:
  - Commit 1: catalog schema upgrade.
  - Commit 2: AI prompt + off-scope tier additions.
  - Commit 3: source narrowing.
- Existing opportunity-tracker fixture data refreshed against the new catalog shape.

## Definition of Done

- [ ] All three PR commits merged.
- [ ] opportunity-tracker's CI passes after merge.
- [ ] A re-scan of a sample 5 accounts produces zero `Nurse` / `Dental Assistant in-person` false positives (manual verification by user).
- [ ] `off-scope` tier rows are written to opp-tracker SQLite and (per spec 015's adapter) flow into Pulse's `expansion_intent_signals` with `processed_status='skipped:off-scope'` and emit no Episodes.
- [ ] Activepieces dashboard reflects the new tier (one extra row).

## Tests

- **Unit (in opp-tracker):** updated tests for the catalog loader; new test for `work_arrangement` extraction in `ai_matcher.py`.
- **Manual:** spot-check 5 known-noisy accounts after Phase 4 starts and the changes are deployed.

## Signal definitions involved

- `expansion_signal_job_posting_match_v1` — the signal's `off-scope` suppression rule depends on this fix landing.

## Open questions

- Q119: full restructure committed in Change A.
- Q120: off-scope tier committed in Change B.

## What this is NOT

- Not in Pulse's `03_build/` codebase — these changes execute against opportunity-tracker's repo.
- Not where the Signal Source Adapter lives (spec 015 — Pulse-side).
- Not where Skill 11 lives (spec 028 — Pulse-side; consumes the fixed match output).

## Session 16 update (2026-05-21) — repo adopted; matcher fix NOT yet landed

opportunity-tracker is now **Pulse-owned** at `edgelabsadmin-glitch/pulse-opp-tracker`
(the upstream `DEdge-max/opportunity-tracker` repo is gone — see Q154). The external
coordinated session is no longer needed; these three changes now execute against the
Pulse-owned repo's `main`.

**Status: NOT applied this session.** The prepared Session-16 patch was not present
in the adopted code (only the SPEC-004 guard was), so the three changes (typed
role-catalog, `off-scope` AI tier + `work_arrangement`, source narrowing to
LinkedIn+Indeed) remain **outstanding**. Until they land:

- `pulse.expansion_intent_signals.match_tier` never takes the `off-scope` value, and
  `work_arrangement` / `matched_industry` are written NULL by the `[OPP-015]`
  mirror-write.
- The "Nurse / in-person-only" false-positive surface is unaddressed.

**Next:** reconstruct the three changes from §Description against
`pulse-opp-tracker` and land as `[OPP-016]` (one bundled PR / three commits), then
redeploy the Fly worker (`pulse-opp-tracker.fly.dev`).

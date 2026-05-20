# Spec 015 — opportunity-tracker Signal Source Adapter

**Maps to:** §14 Signal sources (opportunity-tracker); Design 02; §13.5 new row (Session 11) "Proactive expansion-signal detection"; §13.6 new row 10; Spike 4 §3.
**Depends on:** specs 011, 008.
**Effort:** 1.0 day.

## Description

Implement the opportunity-tracker Signal Source Adapter per Spike 4's recommended integration contract (Spike 4 §3.2). Shared Postgres table `pulse.expansion_intent_signals` is the contract surface. Activepieces flow `expansion_intent_poll` polls every 30 minutes for rows with `processed_at IS NULL`; fans out per-row POSTs to `/webhooks/expansion-intent`. The adapter normalizes each row into an Episode + marks `processed_at`.

Per Spike 4 §3.4, the Episode envelope mapping is verbatim:
- `dedup_key = f"oppt:posting:{posting_id}"` (opportunity-tracker's deterministic SHA-256)
- `source = "opportunity-tracker"`
- `tags = ["expansion-intent", match.tier, source_board]`

`off-scope` tier rows are skipped per Q120 (no Episode emitted; `processed_status = 'skipped:off-scope'`).

## Inputs

- `pulse.expansion_intent_signals` Postgres table (written by opportunity-tracker per the Spike 4 contract; spec 015 owns the Pulse-side write of the mirror schema).
- Episode envelope from spec 011.

## Outputs

- A Postgres migration creating `pulse.expansion_intent_signals` per Spike 4 §3.3 schema verbatim.
- `03_build/pulse/core/adapters/opportunity_tracker.py` exporting `OpportunityTrackerAdapter(SignalSourceAdapter)`.
- Activepieces flow `expansion_intent_poll` (in `pulse_workflows/`).
- A coordinated PR against opportunity-tracker's repo to add the mirror-write into its `state.save_postings()` call (so opp-tracker writes to both its local SQLite AND Pulse's Postgres `expansion_intent_signals` in the same transaction). This PR is small (~30 lines) and gated by an env var so opp-tracker continues to function if Pulse's Postgres isn't reachable.

## Definition of Done

- [ ] Migration applied; `\d pulse.expansion_intent_signals` shows the expected 18+ columns from Spike 4 §3.3.
- [ ] opportunity-tracker PR merged with the mirror-write addition.
- [ ] Activepieces flow polls every 30 min; fans out per-row POSTs.
- [ ] `off-scope` rows skipped at adapter level; `processed_status` updated.
- [ ] `hottest`/`warm`/`general` rows produce Episodes (general suppressed for ingestion by default per Skill 11 trigger; see spec 028).
- [ ] After Episode ingestion, the row's `processed_at` + `pulse_episode_id` + `processed_status='ingested'` are updated.
- [ ] Failure modes from Spike 4 §3.5 all handled (Pulse crash mid-ingest → retry; UPDATE fails → re-attempt; opp-tracker re-write → ON CONFLICT update without re-ingest).

## Tests

- **Unit:** mocked Postgres + a fixture row; verify normalization, Episode emit, status update.
- **Integration:** real Postgres + a seed row in `expansion_intent_signals`; assert end-to-end ingestion completes within one poll cycle.
- **Idempotency:** re-run with same row → no double-ingestion; `processed_at` doesn't update twice.

## Signal definitions involved

- `expansion_signal_job_posting_match_v1` (primary — fires on every Episode from this adapter).

## Open questions

- Q118 (source narrowing — LinkedIn + Indeed only) — already disposed in spec 016 (matcher precision fix).
- Q124 (opp-tracker dashboard purple shade — v1.5+).

## What this is NOT

- Not the matcher precision fix (that's spec 016 — works against opportunity-tracker's matcher code).
- Not Skill 11 (spec 028 — consumes Episodes this adapter emits).
- Not where opportunity-tracker runs (its runtime stays on GitHub Actions per Decision 39).

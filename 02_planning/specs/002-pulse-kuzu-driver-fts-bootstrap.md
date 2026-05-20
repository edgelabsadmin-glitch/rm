# Spec 002 — PulseKuzuDriver FTS bootstrap subclass

**Maps to:** §14 Phase-4-Day-1 tasks; Q114 (filed during Spike 3 live run).
**Depends on:** spec 001 (Project bootstrap).
**Effort:** 0.25 day.

## Description

Graphiti 0.29's `KuzuDriver.build_indices_and_constraints()` is a no-op for Kuzu — it does not install the Kuzu FTS extension or create the four FTS indices (`episode_content`, `node_name_and_summary`, `community_name`, `edge_name_and_fact`). Without the bootstrap, the first `add_episode()` call fails with "Table doesn't have an index with name edge_name_and_fact." Spec 002 creates `PulseKuzuDriver(KuzuDriver)` that runs the bootstrap in `__init__`.

The fix surface is small — a single subclass file. Spike 3's working bootstrap code (in `00_research/spikes/03_graphiti/spike.py`) is the reference implementation; spec 002 ports it into the production codebase.

## Inputs

- Graphiti 0.29 installed (per spec 001's `requirements.txt`).
- Kuzu Python binding installed.
- The bootstrap SQL/Cypher from Spike 3.

## Outputs

- `03_build/pulse/core/memory/driver.py` exporting `PulseKuzuDriver`.
- Unit test verifying that constructing `PulseKuzuDriver(db_path)` produces a driver whose initial `add_episode` call succeeds (no FTS-index error).

## Definition of Done

- [ ] `PulseKuzuDriver(KuzuDriver)` exists; its `__init__` runs `INSTALL FTS; LOAD EXTENSION FTS;` + 4 `CREATE_FTS_INDEX` statements with `try/except` for the "already exists" case.
- [ ] Spike 3's harness re-executed against `PulseKuzuDriver` (substituted for the bootstrap-inline version) passes end-to-end with the same 8-episode dataset.
- [ ] Unit test `test_pulse_kuzu_driver_bootstraps_fts` is in CI.
- [ ] All future `core.memory.*` code instantiates `PulseKuzuDriver`, never the upstream `KuzuDriver` directly.

## Tests

- **Unit:** `test_pulse_kuzu_driver_bootstraps_fts` — creates a temp Kuzu DB, instantiates the subclass, asserts the four FTS indices exist via Kuzu's metadata query.
- **Integration:** the Spike 3 harness re-execution against this driver.

## Signal definitions involved

None.

## Open questions

None — Q114 is the filing of this work; spec 002 *is* its resolution.

## What this is NOT

- Not a fork of Graphiti. The subclass is the smallest possible diff against upstream.
- Not a permanent home for the bootstrap — if/when Graphiti accepts an upstream PR, this subclass simplifies.

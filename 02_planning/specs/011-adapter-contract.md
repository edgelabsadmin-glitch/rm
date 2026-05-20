# Spec 011 — Signal Source Adapter contract + Episode envelope

**Maps to:** §14 Signal sources; Design 02 (Signal Source Adapter); §6 rule 30 (Signal Source Adapter pattern).
**Depends on:** specs 005, 008.
**Effort:** 0.5 day.

## Description

Implement the base adapter contract from Design 02 §"The adapter contract." Abstract Python class with five methods (`list_recent_events`, `receive_webhook`, `fetch_full`, `normalize`, `dedup_key`). Plus the `Episode` envelope dataclass (Design 02 §"The Episode envelope") + the ingestion pipeline (`pulse.core.ingest.run_episode`) that all four Phase 1 adapters terminate in.

Idempotency is enforced at the pipeline level via the `pulse.episodes` Postgres table with `UNIQUE(dedup_key)` per Design 02 §"Idempotency contract."

## Inputs

- Design 02's adapter contract specification.
- Spec 008's event log (for emitting `signal-received`, `episode-ingested`, etc.).
- Spec 005's Graphiti instance.

## Outputs

- `03_build/pulse/core/adapters/base.py` exporting the abstract `SignalSourceAdapter` class.
- `03_build/pulse/core/adapters/episode.py` exporting the `Episode` TypedDict.
- `03_build/pulse/core/ingest/pipeline.py` exporting `async def run_episode(episode: Episode) -> bool` — the central ingestion entry point.
- Postgres migration creating `pulse.episodes` table with `UNIQUE(dedup_key)` per Design 02.

## Definition of Done

- [ ] `SignalSourceAdapter` ABC defined with 5 abstract methods matching Design 02 verbatim.
- [ ] `Episode` TypedDict matches Design 02 §"Episode envelope" verbatim.
- [ ] `run_episode()` performs the full Design 02 §"The ingestion pipeline (where the adapter sits)" sequence: dedup check → fetch_full (if needed) → normalize → Graphiti.add_episode → event log emission.
- [ ] Episodes table has the UNIQUE constraint; double-ingest is a no-op (verified by test).
- [ ] Error handling: each stage's failure emits the appropriate error event from Design 02 §"Error & retry semantics."

## Tests

- **Unit:** mocked adapter implementing the contract; `run_episode` exercises all 5 methods + the pipeline.
- **Integration:** real Graphiti — ingest one Episode end-to-end; verify event log + Graphiti both updated.
- **Idempotency:** double-ingest same Episode → second call returns `False` (already ingested); zero new event log entries (beyond the dedup notice).

## Signal definitions involved

None — adapters consume external signals; signal definitions consume Episodes.

## Open questions

None.

## What this is NOT

- Not a specific adapter (those are specs 012-015).
- Not the Activepieces flows (per ADR-002 — flows route to FastAPI endpoints; this spec implements those endpoints' downstream pipeline).

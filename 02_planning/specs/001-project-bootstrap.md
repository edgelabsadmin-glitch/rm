# Spec 001 — Project bootstrap

**Maps to:** §14 Infrastructure ("FastAPI service + Postgres + Kuzu", "Activepieces self-hosted", project bootstrap line of §14 Phase-4-Day-1 tasks); ADR-001, ADR-002, ADR-003.
**Depends on:** none (this is Day-1).
**Effort:** 1.0 day.

## Description

Set up the Pulse project skeleton end-to-end so subsequent specs can build on a known-green baseline. Includes: Python 3.12 virtualenv; FastAPI service skeleton with `/health` endpoint; Postgres connection (Supabase free tier; three schemas — `pulse`, `activepieces`, `langfuse`); Kuzu local DB initialization with the FTS bootstrap subclass from spec 002 pre-wired; pytest skaffold; lint (ruff) + type-check (pyright) configuration; pre-commit hook; CI smoke test on first push; Activepieces deploy on Fly.io with the first flow (`chorus_engagement_completed`) configured; Langfuse deploy on Fly.io with decorators wired into placeholder agent runner.

## Inputs

- `.env` with Day-1 keys (see build-plan §3).
- Supabase project credentials.
- Fly.io account + flyctl.
- The Spike 3 harness (`00_research/spikes/03_graphiti/spike.py`) — used as the CI smoke test.

## Outputs

- A `pulse/` Python package skeleton under `03_build/`.
- A FastAPI app importable as `pulse.api.main:app`.
- A `core/` namespace under `pulse/` with stubs for `core.agent.runner`, `core.memory.driver`, `core.memory.retrievers`, `core.llm.client`, `core.llm.config`, `core.events.log` — each importable but raising `NotImplementedError` on use. Subsequent specs replace the stubs.
- A `tests/` tree with one passing test (`test_health.py::test_health_endpoint_returns_200`).
- `.github/workflows/ci.yml` running lint + type-check + tests + Spike 3 harness on every push.
- Fly.io apps deployed: `pulse-api`, `pulse-flows` (Activepieces), `pulse-langfuse`.

## Definition of Done

- [ ] `cd 03_build && python -m pulse.api.main` starts the FastAPI service; `curl localhost:8000/health` returns `{"status": "ok", "version": "0.1.0"}`.
- [ ] `pytest` exits 0 with at least 1 passing test.
- [ ] `ruff check 03_build` and `pyright 03_build` both exit 0.
- [ ] `pre-commit install` is documented in the README; running `pre-commit run --all-files` passes.
- [ ] CI on the bootstrap commit goes green (lint + test + Spike 3 harness).
- [ ] `flyctl status -a pulse-api` shows running; `flyctl status -a pulse-flows` shows running; `flyctl status -a pulse-langfuse` shows running.
- [ ] Activepieces UI accessible at the `pulse-flows.fly.dev` URL; `chorus_engagement_completed` flow visible with the correct HTTP destination.
- [ ] Langfuse UI accessible at `pulse-langfuse.fly.dev`; the test trace from spec 001's smoke test visible.
- [ ] Three Supabase schemas exist: `pulse`, `activepieces`, `langfuse`. Verified via `psql` or Supabase dashboard.

## Tests

- **Unit:** `test_health_endpoint_returns_200` (FastAPI TestClient).
- **Integration:** the Spike 3 harness re-execution (passes locally and in CI).
- **Smoke:** 50-concurrent-requests test against `/health` (catches event-loop blocking per Risk 2 mitigation).

## Signal definitions involved

None — this spec is pre-signal-runtime.

## Open questions

- **Q148:** Phase 4 region selection for Fly.io. PM recommends a US East region (closest to most EDGE customers' SFDC instance + lowest Anthropic API latency). User to confirm in Week 1.

## What this is NOT

- Not the FTS bootstrap (that's spec 002).
- Not feature code — every `core/*` stub raises `NotImplementedError`.
- Not where production secrets land — `.env` is gitignored.

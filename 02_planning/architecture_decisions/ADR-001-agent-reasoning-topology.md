# ADR-001 — Agent Reasoning Topology

**Status:** Accepted (2026-05-20, Phase 3 Planning)
**Decision-maker:** PM (per §4.11 "go with your leans" delegation for non-load-bearing infrastructure picks)
**Context:** Design 10 places the FastAPI service, the memory layer (Graphiti × Kuzu), and the agent runtime (LangGraph) in the same Python process. A long-running reasoning call from `/actions` or `/profiles/regenerate` could tie up an HTTP worker. We need to pick a topology before Day-1 of Phase 4 because the choice shapes how cancellation, observability, retries, and the eventual AWS migration are wired.

---

## Options evaluated

### A — Async-everything FastAPI with explicit timeout + cancellation
Every `/actions` and `/profiles` handler is `async def`. Agent reasoning runs in the same event loop, awaiting Graphiti retrievals, Anthropic API calls, and downstream dispatch handlers. Long calls get a per-request timeout (e.g. 60s) and a cancellation-token surfaced to the LLM client.

- **Pro:** simplest possible topology — one process, one event loop, no broker, no worker. Phase 1 infra cost stays at $20/month.
- **Pro:** matches Spike 3's measurement profile cleanly. Ingestion P95 9.6s is well below any reasonable HTTP timeout; query 0.3s is trivial; the heaviest reasoning path is "fire skill + retrieve context + LLM call + emit event" which we expect to land in the 5–15s range for typical actions.
- **Con:** async correctness bugs (forgotten `await`, blocking calls inside coroutines, deadlocks on shared resources) are real and easy to introduce. The risk surface scales with the number of skills.
- **Con:** the agent runtime, the HTTP server, and the memory layer all share an event loop. A genuinely long task (e.g. a Skill 10 cross-account weekly run scanning hundreds of episodes) starves API responsiveness until it completes.
- **Con:** cancellation across a multi-step Skill is *implementable* but is harder than it sounds — anthropic-python SDK supports cancellation via httpx; LangGraph node-level cancellation needs explicit token wiring.

### B — Job queue (Redis or Postgres-backed) between API and agent runtime
HTTP handlers enqueue reasoning jobs and return a `task_id`. A separate worker process consumes the queue, runs the agent, writes results. The UI polls or subscribes for completion.

- **Pro:** clean isolation — API responsiveness is independent of reasoning load. Crashing a worker doesn't crash the API.
- **Pro:** horizontal scale is automatic at AWS migration — add worker processes; the queue handles distribution.
- **Pro:** retries are first-class (re-enqueue on failure with exponential backoff).
- **Con:** more moving parts. Need Redis (or commit to Postgres-as-queue with `SKIP LOCKED` patterns). Need worker process management (supervisord, systemd, or Docker Compose worker service). Two services to deploy on the Phase 1 single VPS.
- **Con:** the UI/UX of "your action is being prepared, refresh in a moment" is a strictly worse experience for the dominant Phase 1 path. Most reasoning is 0.3–8s; users do not want a queue placeholder for that.
- **Con:** observability becomes harder — a trace now spans the API request, the queue enqueue, the worker dequeue, and the worker execution. ADR-003 has more work to do.

### C — Hybrid: sync for <2s, queue for longer
HTTP handlers attempt a synchronous reasoning pass with an aggressive timeout (e.g. 2s). If the call returns in time, the response goes straight back. Otherwise, the handler enqueues the remainder and returns a `task_id`.

- **Pro:** best-of-both for the happy path — fast actions feel instant, slow actions don't block.
- **Con:** the hybrid logic *itself* is non-trivial. The 2s budget is hard to honor when agent reasoning is composed of multiple awaits (Graphiti search + LLM call + dispatch handler); any single sub-call exceeding ~1s makes the handler decide "queue it" mid-way, requiring the agent runtime to be cleanly resumable from any await point.
- **Con:** doubles the test surface — every skill has two code paths (sync and queued).
- **Con:** introduces a "did this come back fast or slow?" UX inconsistency that operator users (RMs) will notice and not love.

---

## Decision: **Option A — async-everything FastAPI with explicit timeout + cancellation.**

### Why

1. **Spike 3's measurements are within tolerance for sync handling.** P95 ingestion 9.6s, query 0.3s. Even a worst-case Skill 03 renewal-watcher run consulting 4 retrievers + Claude Haiku extraction + Claude Sonnet synthesis lands in the 8–15s range. A 60s `/actions` handler timeout is conservative and reasonable for an internal-tool MVP serving 7-8 RMs.

2. **The 6-week timeline rewards simpler topology.** Option B is the architecturally cleaner choice, but it adds 1–2 days of plumbing (worker process, queue schema, polling endpoint, UI loading state) that Phase 1 doesn't need to spend. Phase 4 has 30 working days against 21.5 days of measured work + 3.5 days buffer — we are not flush with slack to burn on infra purity.

3. **The §6 rule 14 "no silent failure" requirement is satisfied by the event log, not by the queue.** Every step of every reasoning chain emits an event (Design 04). Whether the call ran sync or via worker is invisible to the audit trail; the trail is intact either way.

4. **Cancellation is implementable in async FastAPI.** `asyncio.wait_for(coro, timeout=60)` propagates `CancelledError`. The `anthropic` SDK's client respects cancellation via httpx's request cancellation. LangGraph node-level cancellation needs a small wrapper — see Implementation contract below.

5. **The "starvation" concern is real but managed.** Skill 10 (cross-account-pattern-finder, weekly Sunday) and the CEO View composition (weekly Friday) are the only Phase 1 reasoning paths that exceed ~20s. Both run on schedule, not on HTTP requests. They are **invoked from Activepieces flows, not from the FastAPI service.** Activepieces calls Pulse's API to fan out per-account, but the long-running aggregation lives in a separate Python process invoked by Activepieces directly (or by a cron-equivalent flow). API responsiveness is preserved.

6. **The AWS migration path stays open.** When Phase 1 demand grows, Option B is additive — introduce a worker pool, route the slow handlers through it, leave the fast handlers untouched. Option A → Option B is a 3–5 day refactor when we have a measured reason. Option B from day 1 is paying that cost up-front for a problem we don't have.

7. **The "horizontal scale" property of Option B is theoretical for Phase 1.** Phase 1 single-VPS deployment is the agreed topology (Design 11 ADR-008). Even with Option B, we deploy one worker process — horizontal scale isn't realized until AWS. The architectural elegance doesn't pay off until v1.5+.

### Implementation contract

The decision implies the following Phase 4 implementation invariants. These appear as DoD lines on specs 001 (Project bootstrap), 005 (Three-Graph implementation), 008 (Event log), and every skill spec (018–028).

1. **Every FastAPI handler is `async def`.** No sync handlers anywhere. Where a blocking library is unavoidable (e.g., `simple-salesforce` is sync), wrap in `asyncio.to_thread()`.
2. **Top-level request timeout = 60 seconds.** Set via FastAPI middleware. Returns HTTP 504 with a structured error payload + an `action-timeout` event in the log.
3. **Per-LLM-call timeout = 30 seconds.** Set on the Anthropic + OpenAI clients explicitly. Lower for Haiku (15s); higher for Opus (45s).
4. **Cancellation propagates.** Every long-running coroutine respects `asyncio.CancelledError` — Graphiti retrievers, skill `reason_and_propose` calls, dispatch handlers. The agent runtime wrapper (`core/agent/runner.py` per the build plan) takes a `cancellation_token` parameter and forwards it through.
5. **No blocking calls inside async code.** Lint rule: `asyncio.run` only in `if __name__ == "__main__"` scripts. `time.sleep` is banned in handlers; `await asyncio.sleep` only. Spec 003 (model-ID pinning module) adds these to the project's `ruff` config.
6. **Scheduled long-running aggregations run *outside* the FastAPI service.** Skill 10's weekly run and the CEO View composer are Activepieces flows that invoke a separate Python entry point (e.g., `python -m pulse.scheduled.skill_10_run`). The FastAPI service remains responsive even when these run.

### Observability hooks (cross-reference ADR-003)

Whichever observability backend ADR-003 picks (Langfuse is the leaning), the instrumentation lives at three layers, all consistent with Option A's single-process topology:

- HTTP layer (FastAPI middleware): request_id, user_id, route, duration, status
- Agent layer (LangGraph node wrapper): skill_id, retrievers_called, LLM model + tokens
- LLM layer (Anthropic / OpenAI client wrapper): per-call latency + token counts

Single trace per HTTP request. No multi-service stitching to debug.

### What we lose by choosing A

- A single misbehaving skill (e.g., an infinite-recursion bug in cross-account-pattern-finder) can starve the API for up to 60s before timeout. Mitigation: Scheduled long-running paths run outside FastAPI per Implementation Contract item 6.
- We will eventually want Option B's queue when production traffic grows. Mitigation: the API is structured behind a `core/agent/runner.py` abstraction that can have its sync call swapped for an enqueue call when the trigger materializes. The decision is reversible.

### Migration trigger

Revisit ADR-001 when **any one** of the following becomes true:
- P95 `/actions` response time exceeds 25 seconds for two consecutive weeks of production telemetry.
- More than 1 in 50 requests time out at the 60s ceiling.
- An RM reports an interactive workflow blocked by another RM's reasoning.
- AWS migration begins (post-Phase-1) and we want horizontal scale across App Runner instances.

The migration is a measured-trigger reactive move, not a scheduled one.

---

## Consequences

- Day-1 task list bakes in the FastAPI async-first skeleton with the 60s middleware timeout.
- Every skill spec includes a "cancellation respected" DoD line.
- Spec 010 (kill switch + admin config) adds a per-skill kill toggle that short-circuits before the LLM call so an admin can stop a misbehaving skill without restarting the service.
- The build plan does not include a worker-process spec for Phase 1.
- ADR-003 (observability) instruments per-HTTP-request traces; no multi-service stitching needed in Phase 1.

## Reversibility

High. The `core/agent/runner.py` abstraction means the API → runner → reasoning call sequence can be swapped for API → enqueue → worker-runs-reasoning when the trigger materializes. Estimated migration cost: 3–5 days. Phase 1 commits do not lock us out of Option B.

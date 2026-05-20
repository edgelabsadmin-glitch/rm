# ADR-003 — Observability Backend

**Status:** Accepted (2026-05-20, Phase 3 Planning)
**Decision-maker:** PM (per §4.11 delegation; documented reasoning below)
**Context:** Pulse runs LLM calls across multiple reasoning layers (entity extraction during episode ingestion; per-skill reasoning; CEO View composition). Without observability, Phase 4 debugging is blind, Phase 4+ skill tuning is anecdotal, and the §6 rule 14 "no silent failure" guarantee is hard to verify. The pick must be made before Day-1 of Phase 4 because instrumentation hooks shape code structure (PM_CONTEXT §12 candidate #6).

---

## Options evaluated

### Langfuse
- **License:** MIT (core).
- **Self-hosting:** First-class. Single Docker container + Postgres backing store. Cloud free tier exists.
- **SDKs:** Python + TypeScript. Decorator-based instrumentation (`@observe()`).
- **Multi-step agent visibility:** Native — nested traces, with the parent span being the user-facing request and child spans being each LLM call, retriever, or tool invocation.
- **LangGraph integration:** Official via OpenInference / LangSmith-compatible exporters.
- **Anthropic integration:** Native — automatic capture of model, tokens, latency, prompt, response.

### LangSmith
- **License:** Commercial (LangChain Inc.). Free tier (5k traces/month) generous for Phase 1 but contractually limiting.
- **Self-hosting:** Enterprise tier only — not Phase 1 feasible.
- **SDKs:** Python + TypeScript. Tightest integration with LangChain / LangGraph (it is the same vendor).
- **Multi-step visibility:** Best-in-class — designed around LangGraph nodes.
- **Anthropic integration:** Via the LangChain Anthropic wrapper.

### Opik (Comet)
- **License:** Apache 2.0.
- **Self-hosting:** First-class. Docker Compose stack (Backend + Redis + Postgres + MinIO + ClickHouse) — heavier than Langfuse.
- **SDKs:** Python. Newer than the others.
- **Multi-step visibility:** Yes; trace tree model.
- **Anthropic integration:** Via Python SDK wrapper.

### Claude-native tracing
- **License:** Anthropic-built; comes with the SDK.
- **Self-hosting:** N/A — Anthropic's hosted service.
- **SDKs:** Anthropic Python/TS SDKs expose per-call metadata; no visualization UI.
- **Multi-step visibility:** None for application-level traces — Anthropic only sees individual API calls, not the agent reasoning chain that composed them.

---

## Decision: **Langfuse, self-hosted on the same Fly.io footprint as Activepieces.**

### Why

**1. License + posture alignment.**
- §6 rule 28 (resourceful open-source posture). Langfuse is MIT-licensed at the core; the whole stack is self-hostable. No commercial-license commitment.
- LangSmith is paid-or-rate-limited. The free tier suffices for Phase 1 traffic but introduces a vendor relationship and contract surface that PM_CONTEXT §5 budget posture would rather avoid for an internal tool.
- Opik is also self-hostable + MIT, but its stack is heavier (ClickHouse + MinIO + Redis + Postgres + Backend). Langfuse runs in a single container + the same Supabase Postgres we already have.

**2. Cost (PM_CONTEXT §5 $20/month target).**
- Langfuse self-hosted on Fly.io: ~$2–3/month for a small Machine; uses the existing Supabase free-tier Postgres for storage. **Net additional cost: ~$2–3/month.**
- LangSmith free tier: $0/month *now*; commercial tier $39/month if we cross 5k traces (likely by week 3 of Phase 4 once skills are firing).
- Opik self-hosted: ~$5–10/month for the heavier stack (separate ClickHouse).
- Claude-native: $0/month — but solves the wrong problem (per-call metadata vs. application traces).

**3. Self-hostability aligns with the AWS-only standing rule (§6 rule 2).**
- Phase 1 ships on Fly.io; post-Phase-1 we migrate to AWS. Langfuse's container runs on App Runner or ECS Fargate the same way it runs on Fly.io — the deployment is unaffected by the migration. LangSmith would either need its commercial cloud (vendor lock) or its enterprise self-host (cost jump).

**4. Multi-step agent visibility is the load-bearing capability.**
- Pulse's reasoning is multi-step by design: a skill fires → consults 3-4 retrievers → emits an LLM call (Haiku for extraction; Sonnet/Opus for synthesis) → drafts an action → emits another LLM call for the inline-tag-voice rendering → returns. **One user-facing action is 5–8 traceable steps.**
- Langfuse's nested-spans model handles this cleanly. LangSmith handles it slightly more elegantly (it's LangChain-native), but the gap is small enough that license + cost considerations dominate.
- Claude-native tracing sees only the individual LLM calls. It cannot reconstruct "this action proposal happened because skill X reasoned over retrievers A/B/C." That is the literal definition of black-box debugging — and §6 rule 8 forbids it.

**5. Phase 4 Day-1 instrumentation cost.**
- Langfuse Python SDK: pip install + 3-line config + `@observe()` decorators on key functions. Realistic Day-1 work: 4 hours to instrument the core abstractions (agent runner, retriever wrapper, LLM client wrapper); incremental work as skills are written.
- LangSmith would be similarly fast (also decorator-based) but adds the vendor-onboarding step.
- Opik would be 1–1.5 days because the deployment stack is heavier and the SDK newer (less battle-tested in production agents).
- Claude-native is "fast" only because there's nothing to instrument — it provides nothing.

---

## Implementation contract

### Phase 1 deployment

Fly.io Machine sized at ~256MB / 1 shared CPU (same as Activepieces; co-located). Persistent volume not needed (Langfuse writes traces to Postgres). Total Fly.io footprint after this ADR: 2 Machines (Activepieces + Langfuse). Both run from the same Fly app config or as siblings.

```
fly.toml (langfuse):
  app: pulse-langfuse
  primary_region: <same as activepieces>
  vm_size: shared-cpu-1x
  services: { internal_port: 3000, protocol: tcp }
  secrets:
    DATABASE_URL  (Supabase Postgres, schema=langfuse)
    NEXTAUTH_SECRET
    SALT
    NEXTAUTH_URL = https://pulse-langfuse.fly.dev
```

Schema isolation in Supabase: `pulse.*`, `activepieces.*`, `langfuse.*` — three non-overlapping schemas on the same Postgres instance.

### What gets instrumented (Phase 4 Day-1)

Three layers, decorated explicitly:

1. **`core/agent/runner.py`** — the central abstraction per ADR-001. The `run_skill` and `compose_action` entry points get `@observe(name="skill_run")` and `@observe(name="action_compose")` decorators. The trace_id propagates from the FastAPI request via middleware.
2. **`core/memory/retrievers.py`** — `get_customer_context`, `get_talent_context`, `get_rm_context`, and the cross-account retriever (per Q77) each get `@observe(name="retriever_<name>")`. The trace captures the retrieval latency and the bundle size.
3. **`core/llm/client.py`** — the wrapped Anthropic + OpenAI clients. Langfuse's Anthropic auto-instrumentation captures model, tokens (input + output), latency, and full prompt/response. Sampling: 100% in Phase 1 (low volume); revisit if cost grows.

### What the trace tree looks like (one Action Queue proposal)

```
trace: "/internal/skill/renewal-watcher/run"  ──── 9.4s total
  ├── span: skill_run (skill_id=renewal-watcher)  ──── 9.3s
  │     ├── span: retriever_get_customer_context  ─── 0.3s
  │     │     └── span: graphiti.search  ──────── 0.2s
  │     ├── span: retriever_get_recent_episodes  ── 0.2s
  │     ├── span: claude.haiku.extract_signals  ── 2.1s
  │     │     model: claude-haiku-4-5-20251001
  │     │     tokens_in: 4280, tokens_out: 320
  │     ├── span: claude.sonnet.synthesize_brief  6.4s
  │     │     model: claude-sonnet-4-6
  │     │     tokens_in: 6890, tokens_out: 1240
  │     └── span: action_compose  ──────────────── 0.3s
  └── event_log: action-suggested  ─── action_id=abc123
```

The Senior Developer sees the whole reasoning chain in one trace. The PM and VP-CS can spot-check specific spans in the Langfuse UI. The §6 rule 8 (no black-box detection) and rule 14 (no silent failure) requirements are auditable: every span maps to a Signal Definition ID where applicable.

### Sampling, retention, PII

- **Phase 1 sampling:** 100% of traces captured. Volume estimate at week-4 of Phase 4: ~1k-2k traces/day across 7-8 RMs. Well within Langfuse self-hosted capacity (the Postgres impact is manageable; trace data is partitioned per Langfuse's standard schema).
- **Retention:** 90 days hot, then prune via Langfuse's standard retention job. Aligned with Q41 in the event-log retention disposition.
- **PII:** Spike 4 + Session 11 confirmed no PHI in RM calls. Reasoning prose may include customer/talent names + verbatim quotes; these are EDGE-internal-only data and acceptable in the Langfuse store running on Supabase. White-label rule (§6 rule 1) does not apply to internal infrastructure.

### Connection between Langfuse and the event log (Design 04)

Two distinct stores with complementary purposes:

- **Event log (Pulse Postgres `events` table)** — the canonical audit trail. Every `action-suggested`, `action-approved`, `episode-ingested`, `policy-decision` event lands here. Queryable by RM, customer, skill, time. The system of record for "what happened in Pulse."
- **Langfuse traces** — the debugging surface. Every LLM call, every retriever invocation, every skill run, with full prompt + response visible. The system of record for "*why* the agent made the call it did at the LLM level."

They cross-link via `trace_id` and `action_id`: the event log carries `trace_id` as a column; Langfuse carries `action_id` as a tag. An admin investigating "why did Skill 03 propose this Acrisure action?" goes event_log → trace_id → Langfuse → see the full reasoning chain + LLM responses.

---

## What we lose by choosing Langfuse (vs. LangSmith)

- **Slightly less tight LangGraph integration.** LangSmith is LangChain Inc.'s own tool; its LangGraph node visualization is more polished. Langfuse handles LangGraph nodes well via OpenInference but the UI is generic-trace-tree rather than purpose-built. Acceptable tradeoff — the underlying data is the same.
- **Smaller community.** LangSmith has wider adoption; Langfuse is growing but smaller. The MIT license + self-hosting offset this for an internal-tool MVP — we own the deployment.

## What we lose by choosing Langfuse (vs. Opik)

- **Newer SDK ecosystem.** Opik has slightly more bake time; Langfuse is comparable in production-readiness for typical agent workloads. Acceptable.
- **Less analytical depth out-of-box.** Opik markets itself with stronger eval features; Langfuse has basic eval support. Phase 1 doesn't depend on evals (golden-trace tests live in Pulse's own pytest suite per §6 rule 10); evals matter more post-Phase-1.

## Reversibility

The instrumentation surface is **three Python modules** (runner, retrievers, llm client) with `@observe()` decorators. Swapping the backend means changing the decorator import and the SDK config — estimated 1 day for a backend swap. The decision is reversible.

### Migration trigger

Revisit ADR-003 when **any one** of the following becomes true:
- Phase 1 trace volume exceeds Langfuse self-hosted comfort (>50k traces/day) — unlikely until v1.5+.
- Eval-driven skill tuning becomes a primary workflow — Opik or LangSmith may earn the eval-tooling premium then.
- AWS migration timing — at that point the deployment story for Langfuse is unchanged (it runs on App Runner / ECS / EKS). LangSmith would force a vendor reevaluation; we don't want that surprise.

---

## Consequences

- Day-1 task list adds `langfuse` to `requirements.txt` and a `LANGFUSE_*` block to `.env.example`.
- Spec 001 (Project bootstrap) provisions the Langfuse Fly.io Machine + Supabase schema.
- Spec 005, 006 (memory layer + retrievers), every skill spec (018–028), and the LLM client wrapper carry `@observe()` decorators.
- Event log schema (Design 04 + spec 008) adds a `trace_id` column so traces can be cross-walked from audit log to Langfuse.
- ADR-001's Implementation Contract item 1 (every handler `async def`) is automatically picked up by Langfuse's async-aware tracing.

## What this is NOT

- **Not application-level monitoring.** Pulse uses standard `/health` endpoint for liveness; Fly.io's built-in metrics for uptime. Langfuse is for LLM/agent traces specifically.
- **Not the event log.** Langfuse complements the event log; it does not replace it. The event log is canonical for "what happened"; Langfuse is canonical for "what the agent thought."
- **Not user-facing.** Per §6 rule 1, Langfuse never appears in user-facing copy.
- **Not where production-grade observability ends up.** PM_CONTEXT §12 candidate #6 reserves a v1.5+ evolution slot (managed observability vendor, larger-scale infra). Phase 1 Langfuse may be replaced or augmented at that point.

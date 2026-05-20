# Findings: Multi-Agent-Enterprise-CRM

## What it is
An ambitious, MIT-licensed open-source reference architecture for an AI-native CRM in which Sales, Support, Compliance, and Analytics agents are first-class system actors alongside humans. The stack is event-driven (Apache Kafka in KRaft mode with a transactional outbox and CQRS+event sourcing), the agents are orchestrated with LangGraph, vector search runs on Weaviate, the LLM is Ollama/Llama 3.1 (privacy-first local inference), and **policy is enforced by Open Policy Agent (OPA) with explicit approval/kill-switch rules**. The frontend is Next.js 14 with a governance dashboard, real-time event timeline, and approval queue. Multi-tenant isolation is via PostgreSQL Row-Level Security.

## License
**MIT.** Yes — EDGE Pulse can use, fork, embed, and redistribute under closed-source commercial terms with attribution. No copyleft. **Caveat:** the LICENSE file is signed by "AI Test Engineer Agent" rather than a named human/org, and the README marks the project "Under Active Development." Treat the code as a *reference architecture* to learn from, not as a battle-tested dependency. If we adopt any specific module, we should re-vendor and re-review it.

## Maturity signal
- Last commit date: 2026-02-04 (recent; "cleanup build artifacts and add new schemas").
- Stars (if external repo): Not pulled in this session.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: None observed.
- Subjective maturity: **Active development but unproven in production.** The architectural blueprint is sophisticated (Kafka + CQRS + outbox + OPA + LangGraph + observability) but several signals (vague copyright, README "under active development" disclaimer, 2,225 files for what amounts to a reference repo) suggest this is closer to an architecture *demo* than a production-grade product. Reference the *shape*, verify the *implementation* before copying any module.

## Data model / schema
- **Event-sourced** — domain state is rebuilt from an immutable event log on Kafka.
- **CQRS** — separate read and write paths; projections materialize views in PostgreSQL.
- **Multi-tenant** at the row level via PostgreSQL RLS.
- Event topics observed under `schemas/events/`:
  - `lead.created`, `lead.updated`
  - `ticket.created`, `ticket.updated`
  - `journey.updated`
  - **`productivity.signal`** (interesting — explicit signal event type)
  - **`productivity.action-suggested`**, **`productivity.action-approved`**, **`productivity.action-rejected`** (the action-queue contract, explicit)
  - `analytics.prediction-generated`
  - `user.query`, `search.performed`, `search.clicked`, `search.abandoned`
- Agents observed (`agents/src/agents/`): `sales.py`, `support.py`, `compliance.py`, `analytics.py`, all extending `base.py`.

## Architectural patterns worth stealing
- **Explicit `action-suggested` / `action-approved` / `action-rejected` event triplet.** This is *exactly* the Pulse action queue contract. The event-shape gives us a ready-made vocabulary for the hero UI surface (PM_CONTEXT §6 design rule 15). See `schemas/events/productivity.action-*`.
- **OPA-based governance.** `.rego` policy files (`policies/agents/approval.rego`, `policies/agents/core.rego`, `policies/approval.rego`, `policies/twins.rego`) externalize approval rules from code. This is the answer to the tier-aware-behavior standing rule (PM_CONTEXT §6 product rule 4): SMB auto-approve thresholds vs. Enterprise require-human-approval thresholds live in policy, not in agent code.
- **Kill-switch + explainability engine as first-class.** Every agent action carries reasoning, every action is reversible via the event log, the kill switch can halt agent activity globally. Maps onto our "no silent failure" engineering rule (PM_CONTEXT §6 rule 10).
- **Transactional outbox** for exactly-once event publishing between database writes and Kafka. Critical pattern if we ever need durable agent-action publication; less critical for Phase 1 if we use a simpler queue.
- **Time-travel debugging.** Replay events and rebuild state at any point — useful for CEO-demo storytelling ("here's what the agent saw on March 3rd, here's what it recommended, here's what the RM approved") and for incident review.
- **Schema-first event contracts** in `schemas/events/` with a folder per topic. Easy to version, easy to grep, agent-friendly.
- **LangGraph as the multi-agent orchestrator** with a router pattern (`agents/src/orchestrator/router.py`). One precedent for "real agent framework" item in PM_CONTEXT §12 v1.5+ candidates.

## Specific code modules to reference later
- `schemas/events/productivity.action-*/` — adopt this naming/shape for Pulse's action-queue events.
- `policies/agents/approval.rego`, `policies/approval.rego` — adopt the OPA approach for tier-aware approval thresholds.
- `agents/src/agents/base.py` — base agent class with reasoning capture.
- `agents/src/orchestrator/router.py` — LangGraph routing pattern.
- `agents/src/governance/`, `agents/src/policy/`, `agents/src/replay/` — directories named for the governance/explainability surface; valuable to read before Phase 2 architecture work.
- `docker-compose.yml` and `docker-compose.chaos.yml` — chaos-engineering harness for the agent layer is unusually mature.

## What we explicitly are NOT taking from this
- **The whole stack as a starting point.** Far too heavy for Phase 1. Kafka + KRaft + Weaviate + OPA + LangGraph + Ollama + Next.js + Prometheus + Grafana + Loki + OPA + multi-tenant Postgres RLS is a year of work to operate, never mind build.
- **Ollama / local-LLM-only inference.** Pulse needs Claude API (per PM_CONTEXT user-context locks) for quality on healthcare/HIPAA-sensitive reasoning. Self-hosted LLM is interesting for a future PHI-strict mode (post-AWS migration) but not for Phase 1.
- **Weaviate as the vector store.** We can stay inside Graphiti's embedding facility for Phase 1 and revisit a dedicated vector store only if recall demands it. One fewer dependency.
- **Kafka as the bus.** Overkill for Phase 1. n8n (already locked in PM_CONTEXT §3) carries us until volumes justify Kafka.
- **Any production guarantees from this codebase.** Treat as reference, re-implement what we adopt, do not vendor.

## Relevance to EDGE Pulse
**High — primarily as the governance + action-queue blueprint.** This repo's most important contribution is *vocabulary*: the `productivity.action-suggested/approved/rejected` event triplet, the OPA policy files, the kill switch as a system primitive, the time-travel replay surface. These map directly onto PM_CONTEXT's hero-surface requirement (action queue), the "no silent failure" rule, the tier-aware-behavior rule, and the Senior Developer's anticipated scrutiny of governance. The *implementation* is too heavy to copy wholesale and too unverified to depend on, but the *shape* should heavily influence Phase 2 design. Specifically: adopt the event-triplet for actions, adopt OPA-or-equivalent for tiered approval thresholds, adopt explicit reasoning capture per action. Skip Kafka, Weaviate, Ollama, and the chaos harness for Phase 1.

## Open questions raised by this repo
- **OPA vs. inline policy code for Phase 1.** OPA is the right long-term answer but adds operational complexity. Could Phase 1 use a thin Python/TypeScript policy module with the same *shape* (input: proposed action + context, output: allow/deny/require-approval) and migrate to OPA later? Filed for Phase 2.
- **Event bus choice for Phase 1.** n8n is locked, but n8n is a workflow engine, not an event bus. Need a clear decision on whether agent-action events go on a real bus (Postgres LISTEN/NOTIFY, Redis Streams, NATS, etc.) or are written directly to the database with read-side projections. Filed for Phase 2.
- **Reasoning capture format.** Should agent reasoning be stored as freeform text, structured JSON, or a hybrid? The event triplet pattern needs a concrete payload schema before Build.

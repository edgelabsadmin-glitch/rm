# Design 11 — Tech Stack Decisions (ADRs)

**Phase:** 2 (Design)
**Tier:** 3 — late Phase 2 / extending into Phase 3
**Status:** Draft, Phase 2

---

## Purpose

The load-bearing stack picks for Phase 1, recorded as small Architecture Decision Records (ADRs). Each ADR states: the decision, alternatives considered, rationale, consequences, and reversibility horizon. This is the document the Senior Developer reads when asking "why did you pick X."

Decisions already locked in PM_CONTEXT §8 are not re-litigated; they're referenced and (where applicable) refined with Phase 2 detail. New decisions are made here.

---

## ADR-001 — Workflow engine: Activepieces (recommend) vs. self-hosted n8n

**Status:** PM recommendation; user-decisive call pending.

**Context.** PM_CONTEXT Decision 9 deferred this. Both candidates run on $5–10/month VPS, both are open-source-friendly, both have visual editors that the maintenance-friendliness rule (§6 rule 19) requires. The choice is between equally-viable options.

**Comparison.**

| Dimension | Activepieces | Self-hosted n8n |
|---|---|---|
| License | MIT for the open-source edition | Fair-code (Sustainable Use License) |
| Operational footprint | Single Docker container | Single Docker container |
| Integration breadth | 280+ pre-built integrations; smaller community than n8n | 500+ integrations; larger community |
| Custom-code blocks | TypeScript-first; clean serverless-style functions | JavaScript code nodes; works but feels less native |
| Webhook signature validation | Built-in for major providers | Built-in for major providers |
| Deployment maturity | Earlier-stage product (active 2024+) | Mature; widely deployed |
| EDGE familiarity | None | Some (mentioned across PM-CONTEXT) |

**Decision.** **Self-hosted n8n** for Phase 1.

**Rationale.**
- **Maturity premium.** n8n has run in production at scale for years; Activepieces is younger. Phase 1 demo deadline (4 weeks) discourages picking the less-battle-tested option.
- **Community + integration breadth.** When the Phase 2+ Zoom / Slack / Jira adapters land, n8n almost certainly has prebuilt connectors; Activepieces may not.
- **License acceptable for EDGE-internal.** n8n's Sustainable Use License permits internal use without compensation; the AGPL-tolerant posture (§6 rule 18) already accepted similar terms.
- **Reversibility:** the Signal Source Adapter pattern (Design 02) means the workflow engine sits in front of typed adapter code. Switching workflow engines later is a one-week migration, not a redesign.

**Consequences.**
- Pulse documents reference "n8n" in internal docs only; user-facing surfaces never name it (§6 rule 1).
- A `pulse_workflows/` directory holds the n8n workflow JSON exports, version-controlled.

**Reversibility horizon.** Reversible mid-Phase-1; difficult after Phase 4 wires multiple workflow files.

---

## ADR-002 — Agent runtime: LangGraph (Python)

**Status:** Confirmed in PM_CONTEXT Decision 10.

**Context.** LangGraph is locked in PM_CONTEXT. This ADR refines the *flavor*: Python vs. TypeScript.

**Comparison.**

| Dimension | Python (langgraph) | TypeScript (langgraph.js) |
|---|---|---|
| Maturity | Reference implementation; most documentation | Newer; smaller community |
| Ecosystem alignment | `rm-intelligence-agent`, `opportunity-tracker` are Python | Pulse front-end is TS, but back-end is independent |
| LLM-client maturity | First-class Anthropic, OpenAI, Voyage SDKs | All three SDKs exist but feel earlier |
| Graphiti integration | First-party Python | No first-party TypeScript |

**Decision.** **Python (`langgraph` v0.2+)** for Phase 1.

**Rationale.**
- Graphiti is Python-only; co-locating the agent runtime in Python avoids a cross-language IPC layer.
- Existing EDGE Python code (`rm-intelligence-agent`, `opportunity-tracker`) is the codebase Pulse builds *from*; Python is the path of least friction.
- TypeScript is for the front-end only (React).

**Consequences.**
- Pulse API service is Python (FastAPI + LangGraph).
- Front-end is TypeScript (React); communicates via REST/JSON.
- Skills (Design 05) are Python modules.

**Reversibility horizon.** Reversible at v1.5+ if the team materially prefers TS, but expensive after Phase 4 ships.

---

## ADR-003 — Database: Postgres (managed) + Kuzu (embedded)

**Status:** Refines PM_CONTEXT decisions (Graphiti × Kuzu lock; fast-stack-first allows Supabase/Neon).

**Context.** Pulse needs (a) a relational store for the event log, episodes table, profiles, health cache, settings, identity map — and (b) the temporal graph store. Phase 1 budget ($20/month) caps the database spend.

**Decision.** **Managed Postgres (Supabase or Neon free tier) + Embedded Kuzu (Apache 2.0) on local volume.**

**Rationale.**
- Postgres = standard, well-known, multi-instance-ready when needed.
- Supabase free tier is generous (500MB DB, 2GB transfer/month); Neon's free tier is similar. Either works for Phase 1.
- Kuzu is locked by PM_CONTEXT for the graph layer; embedded means zero ops cost.
- **Why not just Postgres** (e.g., with pgvector or AGE)? Graphiti is built around its native drivers; pgvector lacks the bi-temporal model; AGE is less battle-tested than the dedicated graph stores Graphiti targets.
- **Why not a separate vector store** (Weaviate, Pinecone)? Embeddings live inside Graphiti's hybrid search; no separate vector store is needed in Phase 1.

**Consequences.**
- Two storage substrates. The id_map in Postgres bridges them (Design 01).
- Backup discipline: nightly Postgres dump + nightly Kuzu file snapshot to S3-compatible store.

**Reversibility horizon.** Postgres choice (Supabase vs. Neon vs. self-hosted) is reversible anytime via `pg_dump`/`pg_restore`. Kuzu → Neo4j swap is a one-day exercise via Graphiti's driver abstraction.

**Pick between Supabase and Neon: Supabase.** Has auth + RLS out of the box; the auth in particular saves us building OAuth scaffolding from scratch. Neon is the fallback if Supabase's free-tier limits constrain.

---

## ADR-004 — LLM provider: Claude (primary) + OpenAI embeddings

**Status:** Refines PM_CONTEXT Decision 13 (OpenAI → Claude migration) + Spike 3 §C recommendation.

**Decision.** **Anthropic Claude as primary LLM. OpenAI `text-embedding-3-small` as the embedder.**

**Rationale.**
- Claude is locked by PM_CONTEXT; covers all reasoning, extraction, synthesis.
- Anthropic does not ship a public embedding model. Graphiti's first-party embedders are OpenAI and Voyage.
- OpenAI `text-embedding-3-small` is cheapest ($0.02/1M tokens), highest-recall public model, first-party Graphiti-supported. Embeddings are vectors, not user-facing content — using OpenAI here does not strain the white-label rule (§6 rule 1).
- Voyage is a viable alternative; OpenAI wins on cost + maturity for Phase 1.

**Two-tier model strategy:**
| Use case | Model |
|---|---|
| Bulk per-episode extraction (Skill 01 + Graphiti's entity extraction) | `claude-haiku-4-5` |
| Per-action reasoning + narrative synthesis | `claude-sonnet-4-6` or `claude-opus-4-7` |
| CEO View weekly composition | `claude-opus-4-7` |

**Consequences.**
- Two LLM API keys (Anthropic + OpenAI) in `.env`. Rotation per §4.9.
- Migration of `rm-intelligence-agent` prompts from OpenAI to Claude is in scope for Phase 4 lift.
- AWS migration (§12 #3) revisits self-hosted embeddings for full provider-internalization.

**Reversibility horizon.** Embedder swap is a Graphiti config change. Primary LLM swap (Claude → another) is harder due to prompt-tuning specificity.

---

## ADR-005 — Front-end stack: React + Vite + TailwindCSS + Linaria-or-similar zero-runtime CSS

**Status:** New decision.

**Decision.** **React 18 + Vite + TailwindCSS for utility-first styling**, with a small amount of CSS-in-JS where component-scoped dynamic styles are needed.

**Rationale.**
- Vite for dev speed and zero-config build.
- React because the labor market is deepest; future Pulse contributors are most likely React-familiar.
- Tailwind because the design lock (Linear + Granola, dark mode, restrained palette) maps well to utility classes; no separate design-token system needed for Phase 1.
- **Why not Twenty's Linaria + Jotai stack** (per `findings/twenty.md`): Twenty is AGPL; we adopt the *engineering bar* not the *exact toolchain*. Tailwind delivers similar performance with broader team familiarity.

**Consequences.**
- Front-end deploys to Vercel free tier.
- **Component library: shadcn/ui as substrate, not a runtime dependency** (per Tier-0 §12). shadcn components are *copied into the repo* (we own the source), so this is still "in-house" code — but we do not hand-roll generic primitives (button, card, dialog, dropdown, input, select, badge) from scratch. We take shadcn's accessible, unstyled primitives and **re-token them** to the Tier-0 design language (§2 tokens; never the default shadcn look — §12 #1). No runtime component framework (no MUI/Antd/Chakra; the design language is too specific and those carry opinionated styling we'd fight). Brand-signature components (HealthRing, PulseBar, HeroCard, QueueCard, etc.) are fully custom — see Tier-0 §8 and `03_build/front/src/components/README.md` (spec 034 deliverable) for the substrate-vs-custom boundary.

**Reversibility horizon.** Reversible to Next.js or Astro if SSR is needed. Phase 1 is fully client-side fetching + auth.

---

## ADR-006 — Auth: OAuth via Google Workspace (or Microsoft fallback)

**Status:** Refines Design 09.

**Decision.** **Google Workspace OAuth as the primary identity provider; Microsoft OAuth as fallback if EDGE is on Outlook.**

**Rationale.**
- EDGE is a small US-based company; one of these two SSO providers is essentially universal.
- Implementation cost is low (Supabase Auth handles the heavy lifting if ADR-003's Supabase pick stands).
- §4.9 (auth-key discipline) directly applies.

**Consequences.**
- Only `@onedge.co`-domain emails are admitted in Phase 1 (single-tenant assumption).
- MFA is delegated to the SSO provider.

**Reversibility horizon.** Reversible by switching Supabase Auth providers; trivial.

---

## ADR-007 — Observability stub for Phase 1; full pick deferred to Phase 3

**Status:** Stub-only Phase 1; full pick is §12 #6.

**Decision.** **Phase 1 ships structured stdout JSON logs + the event log (Design 04).** No external observability backend in Phase 1.

**Rationale.**
- The event log already captures every meaningful agent step (Design 04); a generic observability backend would duplicate this.
- Phase 1 traffic is tiny (~hundreds of episodes/day); structured logs + occasional Postgres queries are sufficient.
- Deferring the pick to Phase 3 lets us evaluate against actual Phase 1 traffic shape.

**Phase 1 minimum:** stdout JSON; capture via Docker; rotate via standard log-rotate. A `/health` endpoint exposes recent event-log throughput.

**Phase 3 pick candidates** (defer): Langfuse (OSS, self-hostable), LangSmith (paid, full LLM observability), Opik (newer Comet entrant), or Anthropic-native tracing. Phase 3 decision per §12 #6.

**Reversibility horizon.** Phase 1 → Phase 3 transition is additive (instrument once-needed). No path-dependence.

---

## ADR-008 — Hosting topology — single VPS Phase 1, AWS migration after demo

**Status:** Refines Design 10 + PM_CONTEXT §12 #3.

**Decision.** **Phase 1: single VPS (Hetzner or DigitalOcean $5–10/month tier).** AWS migration triggers after demo-validated product shape locks.

**Rationale.**
- $20/month Phase 1 budget cap (PM_CONTEXT §5).
- 8 RMs of traffic does not warrant Kubernetes / multi-region / managed services beyond Postgres.
- EDGE's eventual production hosting target is AWS; Phase 2+ migration is already booked.

**Phase 1 stack on the VPS:**
- One Docker container: Pulse API + LangGraph + Graphiti + dispatch handlers (Python).
- One Docker container: n8n.
- docker-compose for orchestration (Q101).
- nginx as reverse proxy + Let's Encrypt for TLS.

**Reversibility horizon.** Migration to AWS is the booked Phase 2+ trigger.

---

## Roll-up: the Phase 1 stack at a glance

| Layer | Pick |
|---|---|
| Front-end framework | React 18 + Vite + Tailwind |
| Hosting (front) | Vercel free tier |
| API service | Python + FastAPI |
| Agent runtime | LangGraph (Python) |
| Memory layer | Graphiti × Kuzu (embedded) |
| Relational store | Postgres (Supabase free tier) |
| Workflow engine | self-hosted n8n |
| Primary LLM | Anthropic Claude (Haiku + Sonnet/Opus two-tier) |
| Embedder | OpenAI text-embedding-3-small |
| Auth | OAuth via Google Workspace (Supabase Auth) |
| Hosting (back) | Single VPS (Hetzner/DO) running docker-compose |
| Object store | Backblaze B2 free tier (snapshots, exports) |
| TLS | Let's Encrypt via nginx |
| Observability | Stdout JSON + event log; full backend deferred to Phase 3 |

---

## EDGE Coverage references

ADRs are not directly mapped to §13 rows — they implement the picks that the other design artifacts (which carry §13 coverage) require. The Coverage Map walk (Phase 2 final step) reads §13 against Designs 01–10; this artifact provides the substrate.

---

## Open questions

- **Q105** — n8n vs. Activepieces final call. PM recommends n8n; user-decisive.
- **Q106** — Supabase vs. Neon final call. PM recommends Supabase (auth bundled).
- **Q107** — Hetzner vs. DigitalOcean. PM proposes: Hetzner (cheaper); user-decisive.
- **Q108** — Static site host: Vercel vs. Cloudflare Pages vs. Netlify. PM proposes: Vercel (familiar, generous free tier).

---

## What this is NOT

- **Not a vendor lock-in.** Every pick is reversible at a defined horizon.
- **Not an exhaustive stack inventory.** Smaller picks (logging library, test framework, lint config) are implementation detail for Phase 3+ Build planning.
- **Not a buy-build evaluation.** Phase 1 is build-on-OSS exclusively. Commercial vendor evaluation revisits at AWS migration.
- **Not where AWS-specific architecture lives.** That's a Phase 2+ migration plan, deferred per §12 #3.

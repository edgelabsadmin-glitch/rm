# Design 10 — Architecture Overview

**Phase:** 2 (Design)
**Tier:** 3 — late Phase 2 / extending into Phase 3
**Status:** Draft, Phase 2

---

## Purpose

The canonical system architecture for EDGE Pulse Phase 1. One diagram, one narrative, one table of "where does X live." This is the document the Senior Developer will spend the most time on. It ties together every other design artifact and answers the only question that matters at the system level: **does this thing hang together?**

Lower-level decisions (workflow engine choice, specific database brand, agent runtime flavor) are deferred to Design 11. This document is the **shape**, not the **picks**.

---

## Inputs

All other Design artifacts (01–09, 11, 12). Plus PM_CONTEXT §3 locked architecture decisions (Graphiti, Option C, fast-stack-first, n8n/Activepieces, LangGraph, AWS-eventual).

## Outputs

A coherent system architecture readable in 10 minutes.

---

## Behavior

### One-diagram view

```
                              ┌────────────────────────────────────┐
                              │       Pulse front-end (React)      │
                              │  Action Queue (hero) · CEO View ·  │
                              │  Profile views · Admin console     │
                              └─────────────┬──────────────────────┘
                                            │ HTTPS, OAuth-authed
                                            ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                       Pulse API service (Python)                      │
   │   FastAPI · async · single-tenant Phase 1                             │
   │                                                                       │
   │   Routes:                                                             │
   │     /actions          (queue read / approve / modify / reject)        │
   │     /profiles         (read / edit Per-Profile Markdown)              │
   │     /ceo              (CEO View page)                                 │
   │     /admin/*          (policy, kill switch, event log explorer)       │
   │     /webhooks/<src>   (signal-source webhook receivers)               │
   │                                                                       │
   │   Cross-cutting:                                                      │
   │     scope_required decorator (Design 09)                              │
   │     event_log emitter (Design 04)                                     │
   └──────┬────────────────────────────────────────────────────┬──────────┘
          │                                                    │
          │ retriever calls                                    │ dispatches actions
          ▼                                                    ▼
┌──────────────────────────────┐                  ┌──────────────────────────────┐
│  Memory & Reasoning Layer    │                  │  Action Dispatch Handlers    │
│                              │                  │                              │
│  ┌────────────────────────┐  │                  │  ┌────────────────────────┐  │
│  │  Named Retrievers      │  │                  │  │  Email (Gmail / Outlook │  │
│  │  (Design 01 §"X-graph  │  │                  │  │  OAuth on behalf of RM) │  │
│  │  query interface")     │  │                  │  └────────────────────────┘  │
│  └────────────┬───────────┘  │                  │  ┌────────────────────────┐  │
│               │              │                  │  │  Salesforce Task /     │  │
│               ▼              │                  │  │  Record Write (§6 r.6) │  │
│  ┌────────────────────────┐  │                  │  └────────────────────────┘  │
│  │  Graphiti × Kuzu       │  │                  │  ┌────────────────────────┐  │
│  │  embedded graph        │  │                  │  │  Calendar Hold         │  │
│  │  (Design 01)           │  │                  │  │  (Google / MS Graph)   │  │
│  └────────────────────────┘  │                  │  └────────────────────────┘  │
│  ┌────────────────────────┐  │                  │  ┌────────────────────────┐  │
│  │  Agent runtime         │  │                  │  │  Jira ticket           │  │
│  │  (LangGraph, Decision  │  │                  │  │  (v1.5+; Phase 1: SFDC │  │
│  │  10) running skills    │  │                  │  │  Task + email alias)   │  │
│  │  from 01_design/skills │  │                  │  └────────────────────────┘  │
│  └────────────────────────┘  │                  └──────────────────────────────┘
└──────────────────────────────┘                                ▲
                                                                │ on approve
                                                                │
   ┌──────────────────────────────────────────────────────────────────────┐
   │                     Postgres (single instance Phase 1)                │
   │                                                                       │
   │   - events            (Design 04 event log — append-only)             │
   │   - episodes          (Design 02 dedup + processing state)            │
   │   - episodes_failed   (dead-letter)                                   │
   │   - profiles          (Design 06 Markdown layer)                      │
   │   - account_health    (Design 07 health composition cache)            │
   │   - pulse_settings    (kill switch, policy config)                    │
   │   - id_map            (cross-graph identity, Design 01)               │
   └───────────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────────┐
   │                      Workflow engine (Phase 1)                        │
   │   Activepieces OR self-hosted n8n — pick in Design 11                 │
   │                                                                       │
   │   Jobs:                                                               │
   │     - Schedule heartbeat (skill triggers per Design 05)               │
   │     - Webhook routing (validate signature, route to /webhooks/<src>)  │
   │     - SFDC polling (CDC fallback per Q32)                             │
   │     - Profile regenerator (per Design 06 cadence)                     │
   │     - Health recompute (per Design 07 cadence)                        │
   │     - CEO View weekly composition (per Design 08)                     │
   │     - Outcome detection watchers (per Design 03)                      │
   └───────────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────────┐
   │                Signal sources (external; READ-ONLY ingest)            │
   │   Chorus v3 API · Salesforce (sf CLI + SOQL + CDC) ·                  │
   │   Google/MS Calendar  ·  (v1.5+: Zoom, Slack, Jira, email, news)      │
   └───────────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────────┐
   │                       LLM provider — Claude API                       │
   │   Primary: extraction, reasoning, narrative composition               │
   │   Two-tier: Haiku (cheap bulk extraction) + Sonnet/Opus (synthesis)   │
   │   (Embedder: OpenAI text-embedding-3-small per Spike 3 §C / Q25)      │
   └───────────────────────────────────────────────────────────────────────┘
```

### Narrative — read this once

**Pulse runs as four logical services in Phase 1**, hosted on a single small VPS (the resourceful-OSS posture, §6 rule 18; under-$20/month per PM_CONTEXT §5):

1. **The Pulse API service.** Python + FastAPI. Single entry point for the React UI, webhook receivers, and internal cron-driven tasks. Lives behind the OAuth chokepoint. Everything readable or writable in Pulse flows through here.
2. **The memory and reasoning layer.** Graphiti × Kuzu for the temporal context graph (one embedded file under the API service's home dir). The agent runtime (LangGraph) is co-located: same process, same OS. Skills live in `03_build/skills/` and are loaded at API startup.
3. **The action dispatch handlers.** Small Python functions that translate an approved action card into a concrete external call (Gmail draft, SFDC Task, Calendar hold). Each handler emits `action-executed` events.
4. **The workflow engine.** Activepieces or self-hosted n8n (Design 11). Owns: scheduled triggers (heartbeat, profile regenerator, health recompute, CEO View weekly), signal-source webhook routing (signature validation), and the polled-SFDC fallback for CDC.

**Why these four and not three or five:**
- Folding action dispatch into the API service would conflate request/response code with side-effecting handlers — bad isolation.
- Folding the workflow engine into the API service would force us to write all the cron + webhook + retry plumbing ourselves — exactly the maintenance pain the workflow-engine standing rule (§6 rule 19 + `workflow_engine_and_agent_framework_are_different_layers_dont_collapse_them`) avoids.
- Splitting the memory layer from the API service is a Phase 2+ optimization once volumes justify network hops; Phase 1 keeps it embedded for zero ops.

### Data flow — the standard happy path

A typical end-to-end flow (Acrisure Chorus call → RM approval → SFDC Task creation):

```
1. Chorus call ends; Chorus fires webhook → Workflow engine validates signature
2. Workflow engine POSTs to /webhooks/chorus on the Pulse API
3. Pulse API → Chorus Signal Source Adapter (Design 02):
     - receive_webhook() → RawEvent
     - dedup_key check (Postgres episodes table) — new event
     - fetch_full() pulls transcript from Chorus v3
     - normalize() → Episode envelope
     - emit signal-received, signal-normalized events (Design 04)
4. Memory layer ingest:
     - Graphiti.add_episode() — entity extraction, dedup, edge creation
     - emit episode-ingested event with extraction summary
5. Signal-extractor skill (01-detect-talent-signal) fires:
     - reads ContextBundle for Acrisure
     - extracts signals → bi-temporal edges in Graphiti
     - emit reasoning-completed event
6. Health recompute (Design 07) detects new signals:
     - Acrisure customer_side_score drops; tier transitions Stable → Watch
     - emit health-tier-changed event
7. Renewal-watcher skill (03) fires on health-tier-changed:
     - composes action card (email draft + SFDC Task)
     - emit action-suggested event
8. Policy module (Design 04) routes:
     - Acrisure is Mid-Market tier → require-human
     - emit policy-decision event
9. Action card surfaces in RM's Action Queue (Design 03)
10. RM clicks Approve:
      - emit action-approved event
      - dispatch handler creates SFDC Task (via §6 rule 6 write path)
      - emit action-executed event
11. Outcome watcher monitors for SFDC Task closure within 14d:
      - on closure: emit outcome-recorded event
      - on no-close: emit outcome-missing event
12. CEO View's weekly composition (Design 08) folds the outcome into next Friday's narrative
```

**Every step emits to the event log.** This is what §6 rule 12 ("no silent failure") looks like in practice.

### Hosting topology — Phase 1

Single VPS (Hetzner, DigitalOcean, or equivalent — pick a $5–10/month tier per PM_CONTEXT §5 budget posture).

| Component | Host |
|---|---|
| Pulse API + memory + agent runtime + dispatch handlers | One Docker container |
| Workflow engine (Activepieces or n8n) | Second Docker container, same VPS |
| Postgres | Managed (Supabase or Neon free tier; under-$0/month) |
| Kuzu DB file | Mounted volume on the Pulse API container |
| Static front-end | Vercel free tier (one project) |
| Object store for static-HTML demo exports + profile-export PDFs | S3-compatible (Backblaze B2 free tier) |
| Secrets | `.env` on VPS; rotated before AWS migration per §4.9 |

**Reliability posture:** the VPS is a single point of failure in Phase 1. **This is acceptable** for an internal-tool MVP serving 8 RMs. The eventual AWS migration (§12 #3) addresses reliability via App Runner + RDS + EBS.

### Where the "three graphs" actually live (Design 01 reconciliation)

Single Kuzu file. Three logical lenses via node-type / edge-type filters. The `id_map` table in Postgres is the cross-system identity lookup, *not* a fourth graph store.

### Observability — the Phase 1 minimum

- **Application logs:** structured JSON to stdout, captured by Docker logging.
- **Event log** (Design 04) is the system's audit trail; Admin Console (Design 09) exposes a filterable view.
- **Agent telemetry (LLM-call tracing):** placeholder for Phase 1; full pick (LangSmith / Langfuse / Opik / Claude-native) is Phase 3 per §12 #6.
- **Health endpoint** `/health` returns service liveness + recent event-log throughput summary.

### Scaling assumptions

| Surface | Phase 1 capacity | Pressure point |
|---|---|---|
| Signal ingestion | ~500 episodes/day | Chorus + SFDC are bounded; safe |
| Action queue volume | ~100 cards/day across all RMs | Linear in episode rate × skill count |
| LLM tokens | ~$30–60/month for 8 RMs | Two-tier model strategy keeps this within budget |
| Kuzu DB size | Hundreds of MB to ~5GB | Embedded; well within Kuzu's comfort |
| Postgres rows in `events` | ~tens of thousands/year | Single table easily handles this; cold-archive at v1.5+ |
| Concurrent UI users | 8–12 | Single VPS is plenty |

---

## EDGE Coverage references

This artifact ties together every other design artifact. Coverage is by construction:
- §13.2 Workflow 1: Signal Source Adapter (Design 02) + Memory layer (Design 01) + Action Queue (Design 03) + SFDC write path (§6 rule 6).
- §13.3 Workflow 2: Calendar adapter + Skill 02 + Action Queue.
- §13.4 queries: Memory retrievers + Skill 10 + CEO View.
- §13.5 JD areas: Skills 03–10 + Per-Profile Markdown + Dual-Sided Health + Three-Tier Role Model + CEO View.

---

## Open questions

- **Q100** — Single VPS vs. small Kubernetes from day one. PM proposes: single VPS — Kubernetes is over-engineering for Phase 1.
- **Q101** — Container orchestration on the VPS: docker-compose vs. nomad vs. bare Docker. PM proposes: docker-compose for simplicity.
- **Q102** — Backup cadence for the Kuzu DB file. PM proposes: nightly snapshot to S3-compatible store, retain 30 daily + 12 monthly.
- **Q103** — Database migration path to AWS. PM proposes: at AWS migration (§12 #3), Postgres → RDS, Kuzu → migrate to Neo4j on EBS or stay on Kuzu with backups. Decision deferred.
- **Q104** — `simple-salesforce` vs. `sf` CLI choice. `rm-intelligence-agent` and `reference_sfdc_access` lock `sf` CLI. opportunity-tracker uses simple-salesforce. PM proposes: standardize on `sf` CLI in Pulse, leave opportunity-tracker as-is; Phase 1 Pulse subprocess-calls the `sf` CLI exactly like `rm-intelligence-agent` does.

---

## What this is NOT

- **Not a Kubernetes architecture.** Not a microservices architecture. Not a "we'll need Kafka." This is an internal tool for 8 RMs; the architecture is right-sized.
- **Not multi-region.** Single region in Phase 1. AWS migration revisits.
- **Not multi-tenant.** Single tenant (EDGE). Q43 addresses if/when multi-tenant becomes a thing.
- **Not where workflow engine choice is made.** That's Design 11.
- **Not where individual table schemas live.** Schemas appear in the design artifact that owns them (Design 04 has the events schema; Design 06 has profiles; Design 07 has account_health; Design 02 has episodes).
- **Not where observability backend is picked.** Deferred to Phase 3 per §12 #6.

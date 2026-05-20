# ADR-002 — Workflow Engine

**Status:** Pre-locked Session 11 (per PM_CONTEXT Decision log entry 39); rationale + deployment topology documented Phase 3.
**Decision-maker:** User declared per "your senior experienced opinion." PM committed.
**Context:** Pulse needs a workflow engine layer to handle scheduled triggers (heartbeats, profile regeneration, weekly CEO View composition), webhook routing (Chorus engagement events, Calendar push notifications), polled-table fan-out (opportunity-tracker integration's `expansion_intent_signals` table), and orchestration of multi-step jobs that should be visually editable by non-engineers (the maintenance-friendliness rule, §6 rule 29).

---

## Decision: **Activepieces, self-hosted on Fly.io.**

The platform choice (Activepieces vs. self-hosted n8n) was pre-locked Session 11. This ADR documents the **deployment topology** that Phase 4 implements against.

---

## Why Activepieces (vs. self-hosted n8n)

Per Decision log entry 39 (Session 11):

1. **User has Vercel/GitHub-Actions deployment familiarity.** Activepieces's Docker-based deployment maps cleanly onto a Vercel-or-equivalent target without the operational quirks of self-hosted n8n's queue-mode + Redis dependency for production setups.
2. **MIT license** — cleanest possible licensing posture for an internal-tool MVP. Aligned with §6 rule 28 (resourceful open-source posture) but without the Sustainable-Use-License friction n8n carries when org policy reviews come up.
3. **Cleaner UI** — the flow editor is more approachable than n8n's; non-engineers (PM, VP of CS) can read flows without orientation.
4. **~200 integrations cover Phase 1 needs** — Chorus, Salesforce, Slack, Email (SMTP), Postgres, HTTP/Webhooks, Cron. None of Pulse's Phase 1 integrations require an exotic connector that Activepieces lacks.
5. **opportunity-tracker stays on GitHub Actions** — we don't migrate it. Pulse and opportunity-tracker are deliberately separate runtimes; their integration contract (Spike 4) is the shared Postgres `expansion_intent_signals` table, not a shared workflow runtime.

---

## Deployment topology

### Version

**Activepieces Community Edition, latest stable** (currently `v0.x` line; pin to the most recent stable tag at Phase 4 Day-1). Community Edition is MIT-licensed and includes everything Pulse Phase 1 needs (cron triggers, HTTP triggers, code blocks, Postgres connector, scheduled flows).

### Deployment target: **Fly.io**

**Recommended target: Fly.io** (a single small Machine sized at ~256MB / 1 shared CPU, ~$2-3/month at idle plus minimal traffic costs).

**Why Fly.io over the alternatives:**

| Target | Pros | Cons | Verdict |
|---|---|---|---|
| **Fly.io** | $2-3/month idle; persistent volumes for Activepieces's local DB; global anycast; Dockerfile-native deploy via `fly launch`; clean secrets management; HTTPS + custom domain free | Less consumer-grade than Vercel/Railway | **Recommended.** Cheapest persistent-stateful host; aligns with PM_CONTEXT §5 $20/month target. |
| Railway | Familiar Docker deploy; clean UI | $5/month floor; less flexible volumes | Acceptable fallback if user prefers Railway's UX. |
| Render | Free tier exists but stateless; persistent disks add to floor cost | Free tier sleeps after inactivity (a workflow trigger fires at 06:00 and the engine is asleep — bad) | Reject — sleep behavior breaks scheduled flows. |
| Vercel | Best-in-class for stateless front-ends | **Not stateful** — Activepieces needs a persistent DB; Vercel functions are ephemeral | Reject for Activepieces specifically. Vercel does host Pulse's front-end (per Design 11 ADR-005). |

**Operational shape on Fly.io:**

```
fly.toml:
  app: pulse-flows
  primary_region: <closest-to-EDGE>
  vm_size: shared-cpu-1x  (256MB RAM)
  services: { internal_port: 80, protocol: tcp }
  mounts: [{ source: "ap_data", destination: "/data" }]  # persistent volume for Activepieces DB

Dockerfile: official activepieces/activepieces:latest

Secrets (via `fly secrets set`):
  AP_ENCRYPTION_KEY (Activepieces flow encryption)
  AP_JWT_SECRET
  AP_POSTGRES_URL   (points at Supabase free-tier Postgres — same instance as Pulse's events/episodes tables)
  ANTHROPIC_API_KEY (for any code-block needing LLM)
  CHORUS_API_TOKEN
  PULSE_API_URL     (the FastAPI service URL — Activepieces flows call back to Pulse)
  PULSE_API_TOKEN   (shared-secret auth)
```

### How Activepieces connects to Postgres

The same Supabase free-tier Postgres instance that hosts Pulse's `events`, `episodes`, `profiles`, `account_health`, and `expansion_intent_signals` tables (per Design 10) is also used by Activepieces — but in two distinct schemas:

- **Schema `pulse`** — Pulse's domain tables (events, episodes, profiles, etc.)
- **Schema `activepieces`** — Activepieces's internal tables (flow definitions, run history, connections). Activepieces writes here exclusively.

This is the standard Postgres multi-schema pattern. Single connection string per service; two non-overlapping schemas; clean backup story (`pg_dump --schema=pulse` and `pg_dump --schema=activepieces` independently).

**The `expansion_intent_signals` table is in schema `pulse`.** Activepieces reads it via a Postgres connection (configured once in the Activepieces UI as a Connection), polling for `processed_at IS NULL` every 30 minutes (per Spike 4 §3.5). When new rows surface, the flow POSTs to Pulse's `/webhooks/expansion-intent` endpoint with the row payload.

### Trigger types Phase 1 uses

| Trigger | Frequency | Use case |
|---|---|---|
| **Schedule (cron)** | every 30 min | Poll `expansion_intent_signals` for unprocessed rows |
| **Schedule (cron)** | daily 06:00 local | Skill 03 renewal-watcher; Skill 06 advocacy (weekly Monday); Skill 04 talent-care (hourly) |
| **Schedule (cron)** | weekly Sunday 10:00 | Skill 10 cross-account-pattern-finder |
| **Schedule (cron)** | weekly Friday 16:00 | CEO View composition |
| **HTTP webhook (POST)** | event-driven | Chorus engagement-completed; Calendar 24h-ahead; Salesforce CDC fallback poll |
| **Postgres trigger / poll** | as above | Polled — Activepieces does not use Postgres LISTEN/NOTIFY in Phase 1 (simpler poll suffices) |

All triggers terminate in an **HTTP call to the FastAPI service** (see next section). Activepieces is the orchestration shell; Pulse is the reasoning runtime.

### How Pulse's agent runtime is invoked from Activepieces

**Single pattern: Activepieces flows POST to FastAPI endpoints.**

Activepieces flows do **not** invoke the agent runtime directly via Python import — that would couple deployment runtimes and lose the API-level audit trail. Instead:

```
Activepieces flow:
  ── trigger (cron / webhook) ──▶
  ── Postgres read / fan-out logic in Activepieces ──▶
  ── HTTP POST to https://pulse-api.fly.dev/internal/skill/<skill_id>/run
       with: {episode_id?, account_id?, scope?, idempotency_key}
       headers: Authorization: Bearer ${PULSE_API_TOKEN}
  ── handle response (success / failure / retry per Activepieces's built-in retry logic)
```

Pulse's FastAPI service exposes a small `internal/` namespace of endpoints (gated by shared-secret auth — Activepieces is internal infra, not a public client). Each endpoint is `async def`, runs the skill via the `core/agent/runner.py` abstraction (per ADR-001), and returns JSON. The flow handles transport-layer retries (3 attempts, exponential backoff, configured in the flow).

**Long-running aggregation paths (Skill 10 weekly, CEO View weekly) call a separate dedicated entry point** that is *not* the FastAPI service:

```
Activepieces flow (weekly Sunday 10:00):
  ── HTTP POST to https://pulse-api.fly.dev/internal/jobs/run-skill-10
       (returns 202 Accepted immediately; the job runs in a separate Python process)
  ── flow ends; the long-running job's outcome is reported via the event log
```

This satisfies ADR-001's Implementation Contract item 6 — long-running scheduled work runs outside the FastAPI service's request loop.

### Backup-and-restore: workflow definitions as code

Activepieces stores flows as DB rows in its own schema. This is operationally convenient for editing but creates a version-control gap. Phase 1 mitigates by:

1. **Periodic export.** Every Friday (Phase 4 onwards), an admin runs `ap flows export > pulse_workflows/{date}.json` and commits to git. The folder `pulse_workflows/` lives alongside Pulse's code under git.
2. **Phase 4 Day-1 task:** the build plan adds a small script `scripts/ap_export.sh` that wraps the Activepieces API export call. CI runs it weekly on a schedule and opens a PR with the new export.
3. **Restore path:** on a fresh Activepieces instance, `ap flows import < pulse_workflows/{date}.json` rehydrates the full flow set. Disaster recovery time: ~10 minutes.
4. **Schema migration safety:** Activepieces handles its own schema migrations; the export/import is at the flow-definition level, not the DB-schema level. Activepieces version upgrades use the official upgrade path (`flyctl deploy` with the new image tag).

### Phase 1 flow inventory (committed to `pulse_workflows/`)

The build plan provisions seven flows at Day-1 of Phase 4:

| # | Flow name | Trigger | Action |
|---|---|---|---|
| 1 | `chorus_engagement_completed` | HTTP webhook | POST to `/webhooks/chorus` |
| 2 | `calendar_24h_ahead` | HTTP webhook (Google/MS) | POST to `/webhooks/calendar` |
| 3 | `sfdc_poll_changes` | cron every 5 min | Poll SFDC, fan out POSTs to `/webhooks/sfdc` |
| 4 | `expansion_intent_poll` | cron every 30 min | Poll `pulse.expansion_intent_signals WHERE processed_at IS NULL`; fan out to `/webhooks/expansion-intent` |
| 5 | `daily_heartbeat` | cron daily 06:00 | Fan out skill-fire requests (Skill 03, 04, 06) |
| 6 | `weekly_skill_10` | cron weekly Sunday 10:00 | POST to `/internal/jobs/run-skill-10` |
| 7 | `weekly_ceo_view` | cron weekly Friday 16:00 | POST to `/internal/jobs/compose-ceo-view` |

Each flow is documented inline (the flow's `description` field) with the skill or signal source it serves; admins reading the Activepieces UI can map flow → spec → §13 row without leaving the engine.

---

## Consequences

- Phase 4 Day-1 spec adds `Fly.io account + flyctl install + Activepieces deploy` to the bootstrap checklist.
- Spec 011 (Adapter contract) consumes the shared-Postgres pattern documented here.
- Specs 012–015 (the four Signal Source Adapters) each ship with an accompanying Activepieces flow JSON exported into `pulse_workflows/`.
- The build plan reserves ~0.5 days for "Activepieces Fly.io deployment + 7 flows authoring" within Week 1.
- ADR-003 (observability) instruments the Pulse FastAPI side; Activepieces's own flow runs are visible in its built-in UI (sufficient for Phase 1 — no separate observability backend for the workflow engine itself).

## Reversibility

The flow→HTTP→FastAPI pattern is workflow-engine-agnostic. If we ever swap Activepieces for self-hosted n8n or any other workflow engine, the 7 flows port directly (same triggers, same HTTP destinations). Estimated migration cost: ~1 day. The decision does not lock us in.

## What this is NOT

- **Not where agent reasoning lives.** Activepieces orchestrates *when* reasoning happens; Pulse's FastAPI + LangGraph runtime does *what* the reasoning is.
- **Not the source of truth for signal definitions.** Signal definitions live in `02_planning/signals/` (PR'd via git). Activepieces flows reference signals by ID but don't define them.
- **Not user-facing.** Activepieces UI is admin-only. Per §6 rule 1 (white-label), the workflow engine never surfaces in user-visible copy.
- **Not opportunity-tracker's runtime.** opportunity-tracker stays on GitHub Actions cron per Decision log entry 39.

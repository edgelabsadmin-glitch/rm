# `03_build/deploy/` — infrastructure (ADR-002, ADR-003)

Phase 1 infra is three Fly.io Machines + Supabase Postgres, ~$5/mo total (under the $20/mo target).

> **Deploy status (Phase 4 Day-1):** the config files here are authored and ready.
> The actual `flyctl deploy` + Supabase project creation + secret-setting are **operator
> steps that require credentials** (Fly.io account/token, Supabase project, Google OAuth
> client). They are NOT executed by Claude Code — they need the user's accounts. See the
> Day-1 status report for the exact handoff list.

## Components

| App | Image | Purpose | ADR |
|---|---|---|---|
| `pulse-api` | this repo's Dockerfile.api | FastAPI service (memory + agent + dispatch) | ADR-001 |
| `pulse-flows` | `activepieces/activepieces:latest` | Workflow engine | ADR-002 |
| `pulse-langfuse` | `langfuse/langfuse:latest` | LLM observability | ADR-003 |

All three share one Supabase Postgres instance via three schemas: `pulse`, `activepieces`, `langfuse`.

## Operator deploy checklist (user-side)

1. `flyctl auth login`
2. Create Supabase project; create 3 schemas; capture `DATABASE_URL`.
3. `pulse-api`: `flyctl launch --no-deploy` (uses `fly.api.toml`), then `flyctl secrets set` from `.env`, then `flyctl deploy`.
4. `pulse-flows`: `flyctl launch` with `activepieces/activepieces` image + a persistent volume `ap_data`; set `AP_*` secrets; import the 7 flows from `pulse_workflows/` once authored.
5. `pulse-langfuse`: `flyctl launch` with `langfuse/langfuse` image; set `LANGFUSE_*` + `DATABASE_URL` (schema=langfuse).
6. Configure GitHub repo secrets `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` so the CI graphiti-harness job runs.

Once deployed, the `chorus_engagement_completed` Activepieces flow points at `https://pulse-api.fly.dev/webhooks/chorus`.

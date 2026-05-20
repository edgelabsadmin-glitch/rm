# Deploy `pulse-flows` — Activepieces (Pulse workflow engine)

Self-hosted Activepieces per **ADR-002**. Runs the 7 Phase-1 flows (Chorus
webhook, SFDC poll, calendar 24h-ahead, expansion-intent poll, daily heartbeat,
…) that route into the FastAPI service. One Fly Machine in **Singapore (`sin`)**,
co-located with the Supabase pooler; shares the Supabase Postgres via the
`activepieces` schema.

> **Operator step — requires your Fly.io account.** Not run by Claude Code.

## Prerequisites
- `flyctl auth login`
- The Supabase `DATABASE_URL` already in `ai-rm/.env` (the transaction pooler:
  `aws-1-ap-southeast-1.pooler.supabase.com:6543`).
- One-time DB prep (in the Supabase SQL editor) — create the schema + a role
  whose default `search_path` keeps Activepieces' tables out of `public`:
  ```sql
  CREATE SCHEMA IF NOT EXISTS activepieces;
  -- Activepieces has no schema env var; isolate via the connection role's search_path.
  -- Reuse the pooler user and scope it, OR create a dedicated user:
  ALTER ROLE "postgres.uckyovidaajhqkcuxaiz" SET search_path = activepieces, public;
  ```
  (If you prefer not to alter the shared pooler role, let Activepieces use
  `public` — its tables are clearly prefixed — and skip the `ALTER ROLE`.)

## Deploy
```bash
cd 03_build/deploy/activepieces

# 1. Create the app from this fly.toml (no deploy yet).
flyctl launch --copy-config --no-deploy --name pulse-flows --region sin

# 2. Create the persistent volume the [[mounts]] block expects.
flyctl volumes create ap_data --region sin --size 1   # 1 GB

# 3. Secrets. Source the Postgres user/password from DATABASE_URL in ai-rm/.env
#    (DATABASE_URL=postgresql://<USER>:<PASSWORD>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres).
flyctl secrets set \
  AP_POSTGRES_USERNAME="postgres.uckyovidaajhqkcuxaiz" \
  AP_POSTGRES_PASSWORD="<password from DATABASE_URL>" \
  AP_ENCRYPTION_KEY="$(openssl rand -hex 16)" \
  AP_JWT_SECRET="$(openssl rand -hex 32)"

# 4. Deploy.
flyctl deploy
```

Host/port/database and the non-secret flags (`AP_FRONTEND_URL`, `AP_QUEUE_MODE`,
`AP_EXECUTION_MODE`, `AP_POSTGRES_USE_SSL`) are already in `fly.toml [env]`.

## After deploy
1. Open `https://pulse-flows.fly.dev`, create the admin user.
2. Import the 7 flows from `pulse_workflows/` (authored as the adapter specs land).
3. Point the `chorus_engagement_completed` flow's HTTP step at
   `https://pulse-api.fly.dev/webhooks/chorus`; the `sfdc_poll_changes` flow at
   `/webhooks/sfdc`; the calendar flow at `/webhooks/calendar`; the
   expansion-intent flow at `/webhooks/expansion-intent`.

## Secret reference
| Secret | Source |
|---|---|
| `AP_POSTGRES_USERNAME` | user component of `DATABASE_URL` (`postgres.<project-ref>`) |
| `AP_POSTGRES_PASSWORD` | password component of `DATABASE_URL` in `.env` |
| `AP_ENCRYPTION_KEY` | `openssl rand -hex 16` (32 hex chars / 16 bytes) |
| `AP_JWT_SECRET` | `openssl rand -hex 32` |

## Notes
- **Queue mode MEMORY** (no Redis) is the Phase-1 single-Machine choice (ADR-002
  lean posture). If flow volume grows, add a Redis Machine and switch
  `AP_QUEUE_MODE=REDIS`.
- **No auto-stop** — scheduled (cron) flows must keep the Machine awake.
- Pin the image tag in `Dockerfile` (replace `:latest`) once you've validated a
  version, for reproducible redeploys.

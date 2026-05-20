# Deploy `pulse-langfuse` — Langfuse (Pulse LLM observability)

Self-hosted Langfuse **v2** per **ADR-003** — the trace tree behind every
`@observe`-decorated LLM call (skills, retrievers, signal evaluation). One Fly
Machine in **Singapore (`sin`)**, sharing the Supabase Postgres via the
`langfuse` schema (Langfuse uses Prisma, which supports `?schema=`).

> **Operator step — requires your Fly.io account.** Not run by Claude Code.

## Prerequisites
- `flyctl auth login`
- The Supabase `DATABASE_URL` in `ai-rm/.env` (pooler:
  `aws-1-ap-southeast-1.pooler.supabase.com:6543`).
- One-time DB prep (Supabase SQL editor):
  ```sql
  CREATE SCHEMA IF NOT EXISTS langfuse;
  -- Langfuse's Prisma migrations run on first boot into this schema.
  ```

## Deploy
```bash
cd 03_build/deploy/langfuse

# 1. Create the app from this fly.toml (no deploy yet).
flyctl launch --copy-config --no-deploy --name pulse-langfuse --region sin

# 2. Secrets. Build LANGFUSE's DATABASE_URL from the .env one, adding the schema
#    + pgbouncer flag (required for Prisma against the transaction pooler):
#       <DATABASE_URL>?pgbouncer=true&schema=langfuse
flyctl secrets set \
  DATABASE_URL="postgresql://postgres.uckyovidaajhqkcuxaiz:<password>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true&schema=langfuse" \
  NEXTAUTH_SECRET="$(openssl rand -base64 32)" \
  SALT="$(openssl rand -base64 32)" \
  ENCRYPTION_KEY="$(openssl rand -hex 32)"

# 3. Deploy (Prisma migrations apply automatically on boot).
flyctl deploy
```

## After deploy — wire the Pulse API to it
1. Open `https://pulse-langfuse.fly.dev`, create the admin user → an organization
   → a project.
2. In the project's **API Keys**, create a key pair (public `pk-lf-…`,
   secret `sk-lf-…`).
3. Set them on the **pulse-api** app so `@observe` starts exporting traces:
   ```bash
   flyctl secrets set --app pulse-api \
     LANGFUSE_HOST="https://pulse-langfuse.fly.dev" \
     LANGFUSE_PUBLIC_KEY="pk-lf-…" \
     LANGFUSE_SECRET_KEY="sk-lf-…"
   ```
   (Until these are set, Pulse's `_current_trace_id()` short-circuits and emits
   no Langfuse warnings — instrumentation is opt-in by env.)

## Secret reference
| Secret | Source |
|---|---|
| `DATABASE_URL` | `.env` `DATABASE_URL` + `?pgbouncer=true&schema=langfuse` |
| `NEXTAUTH_SECRET` | `openssl rand -base64 32` |
| `SALT` | `openssl rand -base64 32` |
| `ENCRYPTION_KEY` | `openssl rand -hex 32` (64 hex chars / 32 bytes) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | generated in the Langfuse UI after deploy; set on **pulse-api** |

## Notes
- **v2, Postgres-only** is deliberate (ADR-003 lean). Langfuse v3 self-host adds
  Clickhouse + Redis + S3 — out of scope for Phase 1.
- `pgbouncer=true` is required: the Supabase transaction pooler doesn't support
  the prepared statements Prisma would otherwise use (same reason pulse-api sets
  `prepare_threshold=None`).
- Pin the image tag in `Dockerfile` (replace `:2` with a dated v2 tag) once
  validated.

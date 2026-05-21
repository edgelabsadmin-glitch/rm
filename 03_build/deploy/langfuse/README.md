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

# 2. Secrets. Two Postgres URLs are required (see "Why two DB URLs" below):
#    - DATABASE_URL: runtime queries via the TRANSACTION pooler (:6543, pgbouncer).
#    - DIRECT_URL:   Prisma migrations via the SESSION pooler (:5432, no pgbouncer).
#    Both add ?schema=langfuse.
flyctl secrets set \
  DATABASE_URL="postgresql://postgres.uckyovidaajhqkcuxaiz:<password>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true&schema=langfuse" \
  DIRECT_URL="postgresql://postgres.uckyovidaajhqkcuxaiz:<password>@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?schema=langfuse" \
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
| `DATABASE_URL` | `.env` `DATABASE_URL` (`:6543`) + `?pgbouncer=true&schema=langfuse` |
| `DIRECT_URL` | same creds on the **session** pooler `:5432` + `?schema=langfuse` |
| `NEXTAUTH_SECRET` | `openssl rand -base64 32` |
| `SALT` | `openssl rand -base64 32` |
| `ENCRYPTION_KEY` | `openssl rand -hex 32` (64 hex chars / 32 bytes) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | generated in the Langfuse UI after deploy; set on **pulse-api** |

## Notes
- **v2, Postgres-only** is deliberate (ADR-003 lean). Langfuse v3 self-host adds
  Clickhouse + Redis + S3 — out of scope for Phase 1.
- **Why two DB URLs.** The image's entrypoint runs `prisma migrate deploy` (and a
  `prisma db execute` cleanup) on every boot, *before* it starts the web server —
  if migrations fail the entrypoint exits, the Node process never launches, and a
  later `flyctl ssh` shows only `/fly/init`. Prisma's migration engine ignores
  `pgbouncer=true` and uses prepared statements, which the transaction pooler
  (`:6543`) can't route — boot dies with `ERROR: prepared statement "s0" does not
  exist`. Migrations need a connection that keeps a statement on one backend, so
  `DIRECT_URL` must point at the **session** pooler (`:5432`, no `pgbouncer`).
  Without `DIRECT_URL` the entrypoint defaults it to `DATABASE_URL` and hits this.
- `pgbouncer=true` is required on `DATABASE_URL`: the transaction pooler doesn't
  support the prepared statements Prisma's query engine would otherwise use (same
  reason pulse-api sets `prepare_threshold=None`).
- The Dockerfile deliberately sets **no `CMD`/`ENTRYPOINT`** — Fly carries the
  upstream image's `dumb-init -- ./web/entrypoint.sh … node ./web/server.js`
  forward correctly (visible in `flyctl logs` as `Preparing to run: …`). Adding
  one here is unnecessary and would risk masking the entrypoint's migration step.
- Pin the image tag in `Dockerfile` (replace `:2` with a dated v2 tag) once
  validated.

# Infrastructure inventory — Session 19 late-late stream extended further v2

**Compiled:** 2026-05-22
**Compiler:** Claude Code (codebase verification; no code/spec/env changed)
**Purpose:** Phase-0 reconnaissance before spec 043 Step 1. Grounds PM_CONTEXT + spec 043 in verified codebase reality.
**Branch:** `dz-001`
**Method:** read-only `git ls-files`, `grep`, file reads. No Supabase/Fly/Google authentication performed (env-var existence acknowledged only).

---

## Summary

The codebase is a single git repo rooted at `/Users/dabeerazaheen/Documents/ai-rm` with the buildable product under `03_build/` (FastAPI backend + Vite/React frontend). Reconnaissance confirms **no authentication code exists yet** — spec 043 builds the entire OAuth flow, JWT lifecycle, login route, and audit table from scratch. Several spec 043 / PM_CONTEXT assumptions are **inaccurate** and are catalogued in §8; the most consequential are the **`/api`-prefix proxy-strip** (backend routes mount without `/api`), the **`GOOGLE_OAUTH_CLIENT_*` env-var names** (spec/operator referenced other names), the **dev port 5173** (operator believed 3000), and the **ADR-006 "OAuth via Supabase Auth"** intent that spec 043's hand-rolled flow supersedes. One **security-relevant architectural gap** was found — the `/profiles` endpoints are unguarded (no auth dependency) — but **no secrets are committed to git** (only `.env.example` with placeholders is tracked). No HALT-blocking issue surfaced; one process deviation (commit-msg hook) is noted in §9.

---

## §1 — Repository structure

Top-level (prod-relevant dirs only; sibling reference repos `SDRbot-main`, `b2b-sdr-agent-template-main`, `opportunity-tracker`, `rm-intelligence-agent` are external clones, not part of the Pulse build):

```
00_research/   audits, findings, spikes, reference_repos  (+ inventories/ created by this memo)
01_design/     design language system, presence variants, skills
02_planning/   specs/ (031–045), architecture_decisions/, signals/
03_build/      ← THE PRODUCT
  api/         FastAPI app: main.py, actions.py, dispatch.py, profiles.py, admin/kill_switch.py, middleware/timeout.py
  core/        domain logic: db, llm, memory, ingest, adapters, dispatch, outcomes, agent, policy
  front/       Vite + React 18 + TS frontend (pulse-front)
  migrations/  forward-only SQL (0001–0008)
  scripts/     db_migrate.py, outcome_watch.py, sfdc_bench.py, harness_three_graph.py
  deploy/      fly.api.toml
  skills/      skill specs/runtime
  tests/       pytest suite
  pyproject.toml, uv.lock
```

- **Frontend framework:** Vite `^5.4.8` + React `^18.3.1` + react-router-dom `^6.26.2` + @tanstack/react-query `^5.59.0` (`03_build/front/package.json`, name `pulse-front`). **Confirms spec 042's Vite+React** assumption (NOT Next.js).
- **Frontend dev port:** **5173** — pinned in `vite.config.ts` (`server.port: 5173`). Scripts: `dev: vite`, `build: tsc -b && vite build`, `test: vitest run`.
- **Backend framework:** **FastAPI `>=0.115`** (confirms spec 031). App factory `create_app()` in `api/main.py`.
- **Other deployable services:** none in-repo beyond the FastAPI app. Background work is driven by **Activepieces crons** (self-hosted, external) that call FastAPI webhook/endpoint paths — see §7. No in-process scheduler/worker.

---

## §2 — Environment variables

**Tracked in git:** only `.env.example` (root) — placeholders, safe. `.env`, `rm-intelligence-agent/.env`, `opportunity-tracker/.env` exist on disk and are **gitignored** (`.gitignore`: `.env`, `.env.*`, `!.env.example`).

**Root `.env` keys present (names only, values not read):**
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`.

**Vars actually read by backend code** (`os.getenv`/`os.environ`): `ANTHROPIC_API_KEY`, `CHORUS_API_TOKEN`, `CHORUS_WEBHOOK_SECRET`, `DATABASE_URL`, `GOOGLE_CALENDAR_TOKEN`, `GOOGLE_CALENDAR_WEBHOOK_TOKEN`, `LANGFUSE_PUBLIC_KEY`, `PULSE_DISPATCH_DRY_RUN`, `PULSE_INTERNAL_API_TOKEN`, `PULSE_KUZU_PATH`, `PULSE_SFDC_TARGET_ORG`.

**Auth-relevant findings:**
- Google OAuth secrets are named **`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`** (both `.env` and `.env.example`).
- **No code currently reads** `GOOGLE_OAUTH_CLIENT_*` — they are provisioned but unused (confirms no OAuth code).
- **No** `PULSE_JWT_SECRET`, `PULSE_COOKIE_*`, `GOOGLE_CLIENT_ID` (non-OAUTH form) exist yet — spec 043 introduces JWT/cookie vars.
- `.env.example` drift: lists `ACTIVEPIECES_*`, `SF_*`, `CHORUS_API_TOKEN`, `PULSE_INTERNAL_API_TOKEN`; the live root `.env` omits some of these and adds `SUPABASE_PUBLISHABLE_KEY`. Minor; PM may reconcile the template.

---

## §3 — Database state (Supabase Postgres)

- **DB library:** **psycopg3** — `psycopg[binary,pool]>=3.2` (pyproject). Async connection pool. **No** SQLAlchemy, Alembic, asyncpg, or supabase-py. → **Validates spec 043 H1 (psycopg3 idiom).**
- **Migrations live at `03_build/migrations/`** (NOT `api/migrations/` as the recon task assumed). Files:
  - `0001_pulse_events.sql` — event log
  - `0002_pulse_episodes.sql` — ingest episodes
  - `0003_pulse_settings.sql` — settings/kill-switch
  - `0004_associate_stage_history.sql`
  - `0005_expansion_intent_signals.sql`
  - `0006_pulse_profiles.sql`
  - `0007_pulse_account_health.sql`
  - `0008_dispatch_failed.sql`
  - → **Next available is `0009`** (validates spec 043 EDIT 1 `0009_auth_audit_log.sql`).
- **Migration runner:** `scripts/db_migrate.py` — forward-only, applies `migrations/*.sql` in lexical order exactly once, tracks applied files in **`pulse.schema_migrations`**, creates `CREATE SCHEMA IF NOT EXISTS pulse`. Plain idempotent SQL (ADR-008, "Phase-1 simplicity over Alembic"). Run manually: `python scripts/db_migrate.py` (with `DATABASE_URL` set). → **Confirms the `pulse.` schema exists and auto-creates; spec 043's `pulse.auth_audit_log` will be picked up automatically.**
- **No existing auth/session/oauth/token/user tables** in any migration (only events, episodes, settings, profiles, health, signals, dispatch).
- `gen_random_uuid()` availability not directly verifiable without DB auth; **moot** — spec 043 H1 already switched to app-generated `str(uuid.uuid4())` matching the existing migration pattern (the audit log table uses `TEXT PRIMARY KEY`, no DB-side default).

---

## §4 — Existing authentication scaffolding

**Definitive answer to "does any login/auth code exist?": NO.**

- **Frontend:** no `Login` page, no `/login` route, no `signin`/`oauth`/Google integration. Every match for those terms is a **comment or spec-043 forward-reference** (App.tsx header comment "Login is pre-shell … real OAuth in spec 043"; main.tsx; api.ts; demo_characters.ts). The only `useAuth` is spec 042's AuthContext.
- **Backend:** no `/api/auth/*` (or `/auth/*`) endpoint registered. `api/main.py` includes exactly four routers: `kill_switch`, `profiles`, `actions`, `dispatch`, plus a `/health` GET. Every `oauth`/`jwt`/`cookie` match is a **TODO/comment** (e.g., `actions.py:70` "TODO(spec 042): replace with Google-Workspace OAuth"; `core/dispatch/email.py` "actual OAuth send is spec 043").
- **No partial scaffolding, stub endpoints, or commented-out auth code** beyond forward-reference comments.
- **Spec 043 builds the full surface from scratch:** `/login` (frontend), `/auth/*` (backend), JWT mint/verify, cookie handling, audit table.

---

## §5 — Deployment + infrastructure

- **Fly.io:** one app declared — `03_build/deploy/fly.api.toml`: **`app = "pulse-api"`**, `primary_region = "iad"`, `[http_service] internal_port = 8000`. Matches operator's `pulse-api.fly.dev`. **No frontend Fly app** in-repo (frontend deploy is Vercel per build history; not in this toml).
- **Supabase:** acknowledged via `SUPABASE_URL` / `DATABASE_URL` in `.env` (not authenticated). Schemas per `.env.example`: `pulse` / `activepieces` / `langfuse`.
- **Langfuse:** `LANGFUSE_HOST=https://pulse-langfuse.fly.dev` (default in `.env.example`). **Actively used** — `langfuse>=2.0,<3` (v2 SDK), `@observe` decorators in `core/llm/client.py` and `core/memory/retrievers.py` (4+ retriever traces). ADR-003.
- **Google Cloud / OAuth:** **no Google API SDK in code** — `google-auth`/`google-cloud-*`/`googleapiclient` appear only in `.venv` typeshed stubs, never imported. Calendar adapter uses bare tokens (`GOOGLE_CALENDAR_TOKEN`), not the OAuth SDK. → **Validates spec 043 A2: `pyjwt` + `google-auth` must be added to pyproject.**

---

## §6 — Frontend infrastructure for auth UI

- **`App.tsx` route tree** (under `<AppShell>`): `index`→role default, `/accounts`, `/accounts/:id` (AccountScopeGuard), `/actions`, `/constellation` (lazy), `/executive`, `/settings/users`, `/submit`, `/admin` (+ `/admin/signals|outcomes|settings`), `*`→`/accounts`. **No `/login`, no `/admin/audit`** — both are spec 043 additions. The `/admin` route nests via `<AdminLayout>` with child sub-routes (an `/admin/audit` sibling fits the existing pattern cleanly).
- **Header** (`components/Header.tsx`): brand tile, role-gated nav links, Queue button (hidden for Executive), a **dev persona switcher `<select>`** (added spec 042 Step 9, gated `import.meta.env.DEV`), and a **static avatar `<div>`** (initials, `title` tooltip). **No dropdown/menu/popover pattern exists** — spec 043's logout dropdown is **net-new UI** (no `aria-haspopup`, no Radix/headless menu in the file).
- **Redirect-on-unauthenticated:** none today. AuthProvider currently always resolves a non-null user from `DEMO_USERS`. Spec 043's `AsyncAuthProvider`→`/login` redirect (revised §3.3) is the first such logic; no conflict with existing code.
- **API client** (`lib/api.ts`): sends **`X-User-Id` / `X-User-Role`** headers from the caller; `ApiError.detail` is typed **`string`** (validates spec 043 A3 — the field already silently carries the structured executive-403 object today).

---

## §7 — Cross-spec hidden coupling

- **Unguarded endpoint (auth-bypass surface): `api/profiles.py`.** `router = APIRouter(prefix="/profiles")`; both `GET /profiles/{type}/{id}` (`read_profile`) and `PUT /profiles/{type}/{id}` have **no `Depends(require_caller)`** — anyone who can reach the API can read/write profile markdown. **Spec 043 should add a guard** (or PM explicitly accepts the gap for Phase 1A). Flagged for §8/§9.
- **`/health`** GET — unauthenticated by design (Fly health check). Acceptable; note it as a known bypass.
- **Service-to-service auth (must NOT migrate to user JWT):**
  - `api/dispatch.py` — `POST /dispatch/{action_id}` guarded by `Depends(require_internal_token)` → checks `PULSE_INTERNAL_API_TOKEN`. Called by the **Activepieces dispatch flow**.
  - `api/admin/kill_switch.py` — `GET/POST /admin/kill-switch` guarded by `Depends(require_admin)` → **also** checks `PULSE_INTERNAL_API_TOKEN` (same shared secret).
  - These are correct machine-to-machine guards; spec 043's user-OAuth flow must leave them intact. Their **string-detail 403s are spec 043 §7.3 normalization targets** (A1).
- **Crons / background callers:** Activepieces drives `outcome_watch_daily` (`scripts/outcome_watch.py` → `core/outcomes/watchers.py`), calendar polling, SFDC webhook fan-out (`/webhooks/sfdc`), and expansion-intent (`/webhooks/expansion-intent`). These call FastAPI with the **internal token**, not user JWTs. (Note: the webhook routers are referenced in `core/adapters/*` but are **not currently included in `api/main.py`** — only 4 routers are mounted; webhook wiring appears to be Phase-1B.)
- **`X-User-Id`/`X-User-Role` references:** confined to 4 files — `api/actions.py` (Caller), `front/src/lib/api.ts` (sender), `tests/test_rbac_executive.py`, `tests/test_actions_api_db.py`. **No stray README/dev-tooling examples.** Clean migration surface for spec 043's cookie+JWT swap.

---

## §8 — Discrepancy report (most important for PM)

| # | Spec 043 / PM_CONTEXT assumes | Reality | Impact on spec 043 |
|---|---|---|---|
| **D1** | Backend auth routes at `/api/auth/*`; redirect URI `…/api/auth/google/callback` (spec lines 65, 71, 173-174, 359-364) | Vite proxy **strips `/api`** before forwarding (`rewrite: /^\/api/ → ''`); all existing backend routers mount **without** `/api` (e.g. `/actions`). Operator separately stated the configured Google redirect URI is **`/auth/callback`**. | **Reconcile before Step 1.** Backend auth router should mount at `/auth/*` (frontend calls `/api/auth/*`, proxy strips to `/auth/*`). The **Google redirect URI registered in Google Cloud must match what actually resolves** — confirm whether it's `/api/auth/google/callback` (proxied) or the operator's `/auth/callback`. Spec's redirect-URI examples need updating to the agreed value. |
| **D2** | (Operator belief) frontend on **port 3000** | `vite.config.ts` pins **5173**; spec 043 dev redirect URI already uses `localhost:5173`. | Spec is internally correct (5173); PM_CONTEXT should record 5173, not 3000. No code impact. |
| **D3** | Google env vars (operator: "different names than spec assumes") | Codebase canonical: **`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`**. | Spec 043 + Step 1 code must read these exact names (not `GOOGLE_CLIENT_ID`). Add `PULSE_JWT_SECRET` + cookie vars to `.env.example`. |
| **D4** | ADR-006: "Google Workspace OAuth **via Supabase Auth**" | Spec 043 builds a **custom FastAPI OAuth + self-minted JWT** flow; Supabase is used only as plain Postgres. | Design divergence PM should consciously acknowledge: spec 043 supersedes ADR-006's Supabase-Auth path (hand-rolled gives full control + matches the `Caller` model, at the cost of building token lifecycle). Note in PM_CONTEXT / ADR-006. |
| **D5** | Migrations at `api/migrations/` (recon-task phrasing) | Migrations at **`03_build/migrations/`**, runner `scripts/db_migrate.py`, tracked in `pulse.schema_migrations`. | None for spec (EDIT 1 already says `0009`); update PM_CONTEXT path reference. |
| **D6** | `/profiles` participates in RBAC | `/profiles` GET+PUT are **unguarded** (no `require_caller`). | Spec 043 §7 should add a guard or PM explicitly defers. Currently an open read/write surface. |
| **D7** | (implicit) infra is minimal/local | **Provisioned + deployed:** Supabase Postgres, Langfuse v2 on Fly (`pulse-langfuse.fly.dev`, actively traced), pulse-api on Fly (`pulse-api`, iad:8000), Activepieces crons. | PM_CONTEXT lacks an infra section; §9 recommends adding one. |

---

## §9 — Recommended actions

**PM_CONTEXT updates (add an "Infrastructure" section):**
1. Frontend dev port **5173** (correct the 3000 belief); Vite proxy `/api`→`localhost:8000` with `/api` strip.
2. Backend on Fly `pulse-api` (iad, internal 8000); frontend on Vercel.
3. Supabase Postgres (single instance; schemas `pulse`/`activepieces`/`langfuse`); migrations forward-only via `scripts/db_migrate.py`, tracked in `pulse.schema_migrations`; next = `0009`.
4. Langfuse v2 on `pulse-langfuse.fly.dev`, active via `@observe` (ADR-003).
5. DB driver = **psycopg3** async pool (no ORM/Alembic).
6. Auth env vars are `GOOGLE_OAUTH_CLIENT_ID/SECRET`; no OAuth/JWT code exists yet.
7. Service-to-service auth = `PULSE_INTERNAL_API_TOKEN` (dispatch + kill-switch); preserved across spec 043.

**Spec 043 adjustments before Step 1:**
1. **D1 (highest):** settle the auth route prefix + Google redirect URI. Recommendation: mount backend auth router at `/auth/*`; register the redirect URI that actually resolves through the proxy; update spec lines 65/71/173-174/359-364 to the agreed value.
2. **D3:** confirm spec/Step-1 reads `GOOGLE_OAUTH_CLIENT_ID/SECRET`; add `PULSE_JWT_SECRET` + cookie vars to `.env.example`.
3. **D4:** add a one-line ADR-006 note that spec 043 supersedes the Supabase-Auth path with a custom FastAPI flow.
4. **D6:** decide whether spec 043 guards `/profiles` (recommend yes — add `require_caller`) or PM defers it explicitly.
5. Confirm the `0009` migration number is still free at implementation time (it is today).

**No HALT-blocking issue.** One process deviation (commit-msg hook) is recorded with the commit (see report).

---

*End of infrastructure inventory — Session 19 late-late stream extended further v2. Read-only reconnaissance; no code, spec, or env modified.*

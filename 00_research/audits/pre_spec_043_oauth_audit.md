# Pre-spec audit — Spec 043 OAuth + audit observability

**Audited:** 2026-05-22
**Auditor:** Claude Code (read-only codebase verification; this memo is the only artifact)
**Spec under audit:** `02_planning/specs/043-oauth.md` (DRAFT)
**Audit version:** 1
**Branch:** `dz-001`
**Cross-referenced:** `03_build/api/{actions.py, dispatch.py, profiles.py, admin/kill_switch.py}`, `core/db.py`, `migrations/0001–0008`, `scripts/db_migrate.py`, `pyproject.toml`, `03_build/front/src/{main.tsx, lib/api.ts, lib/auth/AuthContext.tsx, components/Header.tsx, routes/AdminLayout.tsx, App.tsx, features/queue/{hooks.ts, WhyDetailPanel.tsx, QueueCard.tsx}}`, `tests/` (40+ pytest modules), the spec 042 audit memo + closed spec 042.

## Summary

Spec 043 is **architecturally sound and well-aligned with the closed spec 042 contract** — the OAuth-flow shape, two-token cookie pattern, error taxonomy, allowlist-only provisioning, and the `Caller`-from-JWT plan are all coherent and inherit cleanly from the existing AuthContext + `Caller` models. The error-observability emphasis is well-specified and the demo-day debugging rationale is real.

Two findings rise to **HALT**, both at the implementation-substrate level rather than the design level: (H1) the §8 audit-log code is written in **asyncpg dialect** (`await conn.execute(...)` with `$1` placeholders, unqualified table name, `DEFAULT gen_random_uuid()`), but the codebase is **psycopg3** (`%s` placeholders, `async with pool.connection()/cursor()`, tables under the `pulse.` schema, app-generated UUIDs); and (H2) the §3.3/§11.1 claim that the AuthContext "interface remains unchanged" is **not achievable as drafted** — moving from synchronous fixture hydration to an async `GET /api/auth/me`-on-mount introduces a loading/null user state that every current consumer (and the 525-test baseline) assumes never exists, and the spec does not define that loading contract. Both are reconcilable with modest spec edits, not redesigns.

**Findings: 2 HALTs · 7 advisories · 9 informationals. Verdict: PROCEED WITH MODIFICATIONS** (0–2 HALTs → normal disposition flow).

---

## Findings

### HALTs (substantive — require spec revision before implementation)

**🚦 H1 — §8 audit-log code is asyncpg dialect; the codebase is psycopg3 with a `pulse.` schema and app-generated UUIDs.**

- *Spec specifies* (§8.2): `await conn.execute("INSERT ... VALUES ($1,$2,...)", attempted_email, ...)` — positional `$N` placeholders, a bare `conn.execute`, and (§8.1) `CREATE TABLE auth_audit_log (... id UUID PRIMARY KEY DEFAULT gen_random_uuid() ...)`.
- *Codebase shows* (`core/ingest/pipeline.py`, `core/db.py`): the established pattern is psycopg3 — `async with pool.connection() as conn: async with conn.cursor() as cur: await cur.execute("... WHERE x = %s;", (val,))`. Placeholders are `%s`; access is via a cursor; the pool comes from `await get_pool()`. Every existing table is created under `CREATE SCHEMA IF NOT EXISTS pulse;` and named `pulse.<table>` (e.g. `pulse.events`, `pulse.episodes`, `pulse.profiles`). Existing migrations declare `UUID PRIMARY KEY` **without** a DB-side default — UUIDs are generated app-side and passed in.
- *Impact:* the §8.2 write function will not run against this stack as written; the migration diverges from the schema-prefix + UUID conventions.
- *Disposition options:*
  - **A (recommended, ~0 extra effort):** rewrite §8.2 in psycopg3 idiom (`%s`, cursor, `(params,)` tuple), name the table `pulse.auth_audit_log`, and keep `DEFAULT gen_random_uuid()` (available on Supabase PG — see I1) **or** generate the UUID app-side to match the existing convention. Migration becomes `migrations/0009_auth_audit_log.sql`.
  - **B:** introduce asyncpg as a second driver — rejected (two DB drivers, no benefit).

**🚦 H2 — "AuthContext interface remains unchanged" (§3.3, §11.1) is not achievable as drafted; async hydration introduces an unspecified loading/null state.**

- *Spec specifies:* `AuthProvider` (no `initialUserId` in production) "calls `GET /api/auth/me` on mount … The AuthContext interface remains unchanged (`user`, `accountScope`, `switchUser`). Only the population mechanism shifts. Spec 042 implementation work is preserved."
- *Codebase shows* (`AuthContext.tsx`): `AuthContextValue.user` is **always a non-null `DemoUser`** — the provider resolves `DEMO_USERS.find(...)` synchronously at render and *throws* if the id is unknown. Every consumer (`Header`, `ExecutiveView`, `Constellation`, `SettingsUsersPanel`, `RoleGuard`, `AccountScopeGuard`) reads `useAuth().user.*` assuming it exists. The 525-test baseline mounts `AuthProvider initialUserId=...` and asserts synchronous presence.
- *Impact:* an async mount-fetch means `user` is undefined between mount and the `/api/auth/me` resolution. As drafted, that either (a) makes `user` nullable — a real interface change forcing edits + null-guards across every consumer and many tests, or (b) requires a loading boundary that gates app render until hydration resolves. The spec defines neither, so "no breaking change / work preserved" is optimistic.
- *Disposition options:*
  - **A (recommended):** add a loading/redirect boundary at the provider level — `AuthProvider` renders a loading state (or nothing) until `/api/auth/me` resolves, then renders children with a guaranteed-present `user`; on failure it redirects to `/login`. This preserves the non-null `user` contract for all consumers. Spec §3.3 must specify this gate explicitly. Keep the `initialUserId` prop for DEV/test synchronous hydration (the spec already keeps the DEV switcher, so the prop must survive).
  - **B:** widen the contract to `user: DemoUser | null` + audit every consumer for null-handling — higher blast radius; not recommended.

---

### Advisories (worth PM disposition; not blocking)

**⚠️ A1 — §7.3 #37 normalization is under-scoped: string-detail 403s exist outside the actions.py "scope" path.** Spec says "convert existing scope 403s in `api/actions.py`." Codebase 403 inventory: `actions.py:139` "action outside your scope" (string), `actions.py:73` "valid X-User-Id and X-User-Role required" (string), `actions.py:82` executive block (**already structured** — spec 042 Step 6), `dispatch.py:28` "internal token required" + `dispatch.py:39` `str(e)` (string), `admin/kill_switch.py:34` "admin token required" (string). *Disposition: decide normalization breadth — at minimum the two `actions.py` string 403s; ideally also `dispatch.py` + `kill_switch.py` for a consistent error contract. State the target set explicitly so #37 closes against a defined surface, not "scope 403s" ambiguously.*

**⚠️ A2 — Spec introduces new dependencies (JWT mint/verify + Google ID-token verification) without naming them or sizing the add.** `pyproject.toml` has **no** `python-jose` / `pyjwt` / `authlib` / `google-auth`. It does have `httpx>=0.27` (sufficient for the `/token` code exchange) and `psycopg[binary,pool]`. Spec §10 mandates HS256 JWTs and §3.2 ID-token signature verification, both requiring a new library (e.g. `pyjwt[crypto]` for HS256 + `google-auth` or manual JWKS fetch for Google's RS256 ID token). *Disposition: name the chosen libs in §1/§12, add them to `pyproject.toml` in Step 1, and re-confirm the Step-1 ~45 min estimate covers dependency selection + Google JWKS verification wiring (see A7).*

**⚠️ A3 — `ApiError.detail` is typed `string` but already receives structured objects; §7.2 401/§5 banner need `.code`.** `lib/api.ts` `request()` does `detail = body.detail ?? detail` and stores it on `ApiError(status, detail: string)`. Spec 042's executive 403 already returns a **dict** `detail`, so this field already silently holds objects in that path. Spec 043's structured 401 (§7.2) and the login banner / refresh logic (§5, §6.2) need to read `detail.code`. *Disposition: §6.2 should specify a typed parse path (e.g. an `AuthError` shape) and the `ApiError.detail` type widened to `string | AuthError`, so the front end can branch on `code` rather than string-matching.*

**⚠️ A4 — Several spec-043 backend tests require the `db` marker (Postgres) and Google mocking; the "~550–557" close target conflates default-run and db-marked counts.** `pyproject.toml` sets `addopts = "-m 'not integration and not db'"`; `db` = "needs a reachable Postgres … skipped when unreachable." The default suite is **284** (48 deselected); the "525 baseline" = 241 front-end + 284 default backend. Audit-log write/read tests + the OAuth callback-success path touch Postgres → must be `db`-marked and won't run in the default suite (mirrors `test_actions_api_db.py`). The pure 401/403/state-mismatch tests can run DB-free (like `test_rbac_executive.py`). No httpx-mock/respx dependency is named for stubbing Google's `/token` + JWKS. *Disposition: split §14's count into "default-run (DB-free, like `test_rbac_executive`)" vs "`db`-marked"; name the Google/httpx mocking approach; re-baseline the close target against the default-run number.*

**⚠️ A5 — Cookie/topology: dev works via the Vite proxy, but production same-origin + `Secure`/SameSite must be ratified.** In dev, the front end calls `/api` and `vite.config` proxies to FastAPI, so cookies are same-origin and attach to callback redirects; `Secure` must be disabled for `localhost` (spec provides `PULSE_COOKIE_INSECURE_DEV`). SameSite=Lax does allow the top-level Google→callback navigation cookie attach (correct). Production assumes a single domain / reverse proxy (§17.2). *Disposition: ratify the production topology (single-domain reverse proxy vs split origin + CORS) at audit time, and confirm the Vite dev proxy forwards `Set-Cookie` (it does by default, but the callback issues a 302 with `Set-Cookie` — verify the proxy preserves it).*

**⚠️ A6 — Audit IP capture behind a proxy: `request.client.host` returns the proxy IP, not the client IP.** Production deploy is likely behind a reverse proxy (§17.2); §8.2 stores `request.client.host`, which in that topology is the proxy/load-balancer address. The spec does not mention `X-Forwarded-For` / `Forwarded`. *Disposition: add a note to §8.2 to read the left-most `X-Forwarded-For` hop (when present and trusted) for `ip_address`, falling back to `request.client.host`; minor, but it directly affects the demo-day "see where the failed login came from" value.*

**⚠️ A7 — Retention back-of-envelope omits the dominant row source (refresh-success).** §8.4/§17.4 estimate "<1000 rows" from login attempts. But §8.3 logs **refresh success** (every ~1h per active session). Worst case: 11 users × ~8 active hours/day × ~25 working days ≈ 2,200 refresh rows alone, before failures. Realistic demo traffic is far lighter, but the <1000 figure rests on counting only logins. *Disposition: either reconcile the estimate to include refresh rows (still small, low thousands — index on `ts DESC` keeps reads fast, so no functional risk), or downgrade refresh-success logging to Phase 2 if the row volume/noise isn't worth it. Informational-adjacent; no blocker.*

---

### Informationals (FYI; no disposition needed)

- **ℹ️ I1 — `gen_random_uuid()` is available.** Supabase Postgres (the deploy target per `core/db.py`) is PG 13+, where `gen_random_uuid()` is built into core (no `pgcrypto` extension needed). It diverges from the codebase's app-generated-UUID convention but works; folded into H1's disposition.
- **ℹ️ I2 — Migration framework confirmed.** `scripts/db_migrate.py` runs numbered raw-SQL files `migrations/0001…0008`. The audit table lands as `0009_auth_audit_log.sql`. No new framework needed.
- **ℹ️ I3 — Expandable-row UI has precedent.** `WhyDetailPanel.tsx` + `QueueCard.tsx` (queue expand) and `account/CollapsibleSection.tsx` establish the expand/collapse pattern §9.2 needs — not net-new UI.
- **ℹ️ I4 — React Query is present and compatible.** `features/queue/hooks.ts` uses `useQuery`/`useMutation` (10s polling via `useActions`). A 401→refresh→retry implemented inside `lib/api.ts request()` is transparent to React Query (it sees only the resolved promise). Caveat: `listActions` already catches **all** errors in DEV to serve the fixture, so the refresh path is effectively production-only — acceptable.
- **ℹ️ I5 — Production `AuthProvider` already takes no prop.** `main.tsx` renders `<AuthProvider>` (no `initialUserId`); the default `'pulse-admin'` is internal. §3.3's "becomes `AuthProvider()`" is already true at the call site — only the provider internals change (see H2 for the real nuance).
- **ℹ️ I6 — Header has no dropdown primitive today.** The avatar is a static `<div>` with a `title` tooltip; §6.3's "Header dropdown gains Sign out" is new UI (a small menu). Minor; the DEV persona switcher (`<select>`, spec 042 Step 9) is unaffected and coexists.
- **ℹ️ I7 — Error taxonomy is comprehensive vs the flow.** Walking initiate → consent → callback (state/exchange/verify/domain/provision) → session (no/invalid/expired) → refresh covers every realistic boundary; `no_session` correctly logs nothing (avoids per-visit noise), `rate_limited` is wired-but-Phase-2. No missing code path identified. Granularity is appropriate (close to OAuth2 `error_description` norms, not over-split).
- **ℹ️ I8 — CSRF posture is adequate for Phase 1A.** httpOnly + SameSite=Lax cookies + the OAuth `state` nonce cover the callback; refresh/logout are POST with `Path`-scoped cookies. No separate CSRF token is required Phase 1A given SameSite=Lax (note for awareness; Phase 2 may add double-submit tokens if a SameSite=None scenario arises).
- **ℹ️ I9 — Backend + frontend already anticipate spec 043.** `api/admin/kill_switch.py` ("placeholder admin guard … in specs 042/043"), `lib/api.ts` ("spec 043 replaces these with a real bearer token at the same chokepoint"), and `main.tsx` ("spec 043 OAuth hydrates") all name this spec — the seams are pre-marked.

---

## Suggested audit focus per spec §19

- **§3 architecture** — Flow + cookie pattern are right for this context (dev = Vite proxy same-origin; prod = same-domain reverse proxy per §17.2, to be ratified — A5). Google callback shape (state nonce in query + cookie compare) is handled. **JWT library is NOT present — new dependency (A2).** Refresh recursive-retry is React-Query-compatible (I4). **One real gap: AuthContext async hydration (H2).**
- **§4 multi-domain** — Single OAuth client over `onedge.co` + `edgeonline.co` is valid; the spec's §17.6 mitigation already calls out the Google Cloud domain-verification pre-flight. `normalize_email` handles whitespace + case (`.strip().lower()`); Google returns lowercase, so the defensive path is for completeness. Nothing to flag beyond confirming domain verification is an operator pre-flight (already in §17.6).
- **§5 error taxonomy** — Comprehensive; no missing path (I7).
- **§7 backend** — `Caller` model unchanged; `get_caller()` header→cookie+JWT refactor is contained. `require_queue_caller` (spec 042 Step 6) gates **after** identity, so it composes correctly with a JWT-populated `Caller`. 401-vs-403 split is correctly applied (identity-unverified = 401; scope = 403). **#37 normalization scope is under-specified — string 403s also live in `dispatch.py` + `kill_switch.py` + `actions.py:73` (A1).**
- **§8 audit schema** — Indexes (`ts DESC`, partial on `attempted_email`, partial on `error_code`) are appropriate. A partial index on `success = false` would speed the common "show me failures" query but isn't required at <few-thousand rows. JSONB `diagnostics` is small (state nonces + Google error subset + optional trace) — no unbounded-row risk. **Driver dialect + schema prefix + UUID default all diverge (H1); retention estimate omits refresh rows (A7); proxy IP (A6).**
- **§9 admin viewer** — AdminLayout supports sub-routes via `<Outlet/>` + nested `App.tsx` routes; adding `/admin/audit` to `ADMIN_NAV` is trivial. **Note:** §9.1 describes the existing sub-nav as "/admin (admin home) + /admin/audit"; the actual `ADMIN_NAV` is `signals` / `outcomes` / `settings` (and `/admin` index *redirects* to `/admin/signals` — there is no "admin home" item). Cosmetic doc inaccuracy. Chip tokens for success (good-on-brand) / failure (risk-on-brand) exist (used across Executive View / chips). Expandable-row precedent exists (I3).
- **§11 cross-spec** — AuthContext signature preserved *modulo* H2's loading contract; `Caller` preserved; DEV switcher + `initialUserId` prop must be retained for tests/dev (spec keeps the switcher, so the prop must survive — make explicit). No existing assertion breaks **provided** H2's loading gate keeps `user` non-null.
- **§12 sequence** — Ordering is sound; Step 4 (login page, mostly static + a redirect link) can parallel Step 5 (AuthContext refactor) since they touch different files and Step 5's dependency is the Step-2 backend, not Step 4. **Step 1 ~45 min is tight** once dependency selection + Google JWKS verification + the `0009` migration are included (A2/A7 feed this); ~60 min is more realistic. Step 2 ~75 min for 5 endpoints + code exchange + taxonomy is plausible.

---

## Cross-spec coordination verification (spec 043 §11)

- **§11.1 spec 042 AuthContext** — interface (`user`, `accountScope`, `switchUser`) preserved in *shape*; the async-population change needs the H2 loading contract to keep `user` non-null. DEV switcher (spec 042 Step 9) + `initialUserId` prop must be retained for the test harness — verified the 525 baseline depends on synchronous `initialUserId` hydration.
- **§11.2 spec 031 Caller** — `Caller` shape unchanged; `get_caller()` source swap (header→cookie+JWT) is isolated to one dependency; `X-User-*` retired at Week-4 cutover. `require_queue_caller` composes correctly (gates post-identity). Verified against `api/actions.py`.
- **§11.3 pulse-api Week-4 pairing** — audit-log writes + real `Caller`-from-JWT + real Action Queue cards all land in the same window; operator must ratify `DATABASE_URL` / `PULSE_JWT_SECRET` / `GOOGLE_CLIENT_*` / `PULSE_COOKIE_INSECURE_DEV` at audit time (already in §12/§17.1). No code conflict.
- **§11.4 Settings panel** — `/settings/users` (spec 042) and `/admin/audit` are distinct routes/surfaces; no overlap. Verified.

---

## Audit-time HALTs

None. No decision was required from the PM before this memo could be completed, and codebase verification surfaced **no** undocumented/partially-built OAuth flow that would materially change audit scope. The deployment env-var + Google Cloud client provisioning are operator action items the spec already flags (§12, §17.1/§17.6), not memo blockers.

## Conclusion + recommended next steps

The design is ratifiable; the two HALTs are substrate reconciliations, not redesigns:

1. **PM disposes H1** — direct §8 to psycopg3 idiom (`%s` + cursor), `pulse.auth_audit_log`, and a UUID-generation choice consistent with the codebase (recommended: keep `gen_random_uuid()` since it's available, or app-side to match convention). Migration = `0009_auth_audit_log.sql`.
2. **PM disposes H2** — add an explicit AuthContext **loading/redirect boundary** to §3.3 so `user` stays non-null for all consumers; retain `initialUserId` for DEV/tests.
3. **PM applies advisories** — A1 (define the 403-normalization target set), A2 (name + add JWT/Google libs; revisit Step-1 estimate), A3 (typed `AuthError` parse path + widen `ApiError.detail`), A4 (split test counts default-run vs `db`-marked; name Google mocking), A5 (ratify prod topology + verify proxy `Set-Cookie`), A6 (`X-Forwarded-For` for IP), A7 (reconcile retention estimate or defer refresh-success logging).
4. **Informationals** need no action; I1–I9 are confirmations + minor doc nits (notably §9.1's sub-nav description).
5. After the spec is revised + re-committed on `dz-001`, the ratified Step-1 prompt (env config + JWT helpers + `0009` migration) is the lowest-risk start. All work continues on `dz-001`; merge to `main` awaits separate operator authorization.

*End of pre-spec 043 audit. Read-only; no spec or code modified.*

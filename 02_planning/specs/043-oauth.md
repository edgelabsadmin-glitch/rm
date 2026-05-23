# Spec 043 — OAuth via Supabase Auth (Path A)

**Status:** DRAFT v3.2 (Session 19 late-late stream extended further v3)
**Architecture:** Supabase Auth with **asymmetric JWT signing (RS256 or ES256)** verified via Supabase JWKS endpoint
**Branch:** `dz-001`
**Honors:** ADR-006 v1.1 (`02_planning/architecture_decisions/ADR-006-authentication.md`)
**Depends on:** Spec 042 RBAC CLOSED; Phase-0 infrastructure reconnaissance `acc6ed1`; ADR-006 v1.1; operator-verified asymmetric JWT signing keys live in Supabase Project Settings
**Closes watched concerns:** #30 (multi-domain SSO), #37 (403 detail normalization), #40 (auth observability), #41 (profiles unguarded)
**Estimated effort:** ~3 hours Claude Code

---

## §1 Framing + ADR honor

This spec implements production-grade Google Workspace OAuth authentication for EDGE Pulse, **honoring ADR-006 v1.1 "Authentication via Supabase Auth"**.

**JWT signing is asymmetric (RS256 or ES256), verified locally by pulse-api via Supabase JWKS public keys.** This is Supabase's recommended algorithm for OAuth use cases and matches the operator's live Supabase Project Settings → JWT Signing Keys configuration (asymmetric ES256, legacy HS256 retired).

**Reference:** `02_planning/architecture_decisions/ADR-006-authentication.md` v1.1. **Reconnaissance:** `00_research/inventories/infrastructure_inventory_session19_v2.md`. **Pre-spec audits:** `pre_spec_043_oauth_audit_v2.md` (`5f82914`), `pre_spec_043_oauth_audit_v3.md` (`c57a15f`), `pre_spec_043_oauth_audit_v4.md`.

**What Supabase Auth provides (no spec 043 work needed):**
- Google Workspace OAuth 2.0 flow (authorization code + PKCE)
- JWT minting with **asymmetric algorithm (RS256 or ES256)** — private key managed internally by Supabase; never exposed
- Public keys published at JWKS endpoint `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
- Refresh token rotation (90-day default)
- Session cookie management (httponly, secure, samesite=lax)
- `auth.users` table (Supabase managed schema)
- `auth.audit_log_entries` table (auto-populated; closes #40)
- Email domain allowlist (optional dashboard config; backend DEMO_USERS check is authoritative regardless — closes #30)

**What this spec builds (~3h):**
- Frontend: `/login` page + Supabase Auth client + AsyncAuthProvider (loading state across all 12 `useAuth` consumers) + logout flow with Header dropdown
- Backend: `require_caller` rewrite (in `api/actions.py`) — validates Supabase asymmetric JWTs via JWKS + DEMO_USERS allowlist enforcement
- Backend: `/profiles` endpoint guarding (closes #41)
- Backend: `/admin/audit` viewer querying `auth.audit_log_entries`
- 403 detail format normalization across all guards (closes #37)
- Automated multi-domain (onedge.co + edgeonline.co) JWT integration tests

**What this spec does NOT touch:**
- `PULSE_INTERNAL_API_TOKEN` service-to-service auth (preserved unchanged)
- `/health` GET (unauthenticated by design)
- Existing 4 routers in `api/main.py` (no new backend auth router — Supabase Auth callback goes to Supabase, not pulse-api)

---

## §2 Architecture overview

### 2.1 Auth flow (production)

1. User navigates to any protected route
2. Frontend `AsyncAuthProvider` checks for Supabase session via `supabase.auth.getSession()`
3. If no session → redirect to `/login`
4. `/login` renders "Sign in with Google" → calls `supabase.auth.signInWithOAuth({ provider: 'google' })`
5. Supabase Auth redirects to Google OAuth consent screen
6. Google redirects to **Supabase Auth callback** (`https://uckyovidaajhqkcuxaiz.supabase.co/auth/v1/callback`) — NOT pulse-api
7. Supabase Auth exchanges code, creates/finds `auth.users` row, mints **asymmetric (RS256 or ES256) JWT**, sets httponly cookie, redirects to **Pulse frontend** `/auth/callback`
8. Frontend `/auth/callback` confirms session, redirects to `/` (role-defaulted)
9. Subsequent API calls: frontend sends JWT in `Authorization: Bearer <jwt>` header
10. Backend `require_caller` (in `api/actions.py`) validates JWT via **Supabase JWKS public keys** (cached in-process; algorithm allowlist `["RS256", "ES256"]`; rejects HS256) → looks up email in DEMO_USERS → populates `Caller` → request proceeds

### 2.2 Auth flow (dev)

Same as production, but Supabase redirects to `http://localhost:5173/auth/callback`. Backend on `localhost:8000`; Vite proxy strips `/api` prefix.

Dev user-switcher (Header `<select>` from spec 042) PRESERVED for non-OAuth dev workflows; gated `import.meta.env.DEV` AND `!supabase.auth.session()`.

### 2.3 Multi-domain SSO (closes #30)

- Iffi Wahla on `edgeonline.co`; all other DEMO_USERS on `onedge.co`
- **Backend DEMO_USERS check (authoritative):** `require_caller` looks up JWT email in DEMO_USERS; user with valid Google account NOT in DEMO_USERS → 403 with structured detail per §2.5
- Supabase Auth dashboard email domain allowlist: skipped this iteration (not exposed in operator's tier); backend check is sufficient
- Google Cloud OAuth consent screen Internal user type: configured; supports both domains under `onedge.co` Google org
- **Automated test coverage:** Step 9 integration test includes 2 multi-domain cases (`onedge.co` JWT happy path + `edgeonline.co` JWT happy path)

### 2.4 Audit observability (closes #40)

Supabase writes to `auth.audit_log_entries` automatically on every auth event. Spec 043 builds `/admin/audit` viewer (admin-only) querying this table via Supabase service-role client.

### 2.5 403 detail format normalization (closes #37)

All 403 responses return JSON body:
```json
{
  "detail": {
    "code": "FORBIDDEN_NOT_IN_ALLOWLIST" | "FORBIDDEN_INSUFFICIENT_ROLE" | "FORBIDDEN_OUT_OF_SCOPE" | "FORBIDDEN_INVALID_TOKEN",
    "message": "...",
    "context": { /* optional */ }
  }
}
```

Affected sites: `require_caller` (`api/actions.py`), `require_admin` (`api/admin/kill_switch.py`), `require_internal_token` (`api/dispatch.py`), spec 042 executive-403 (`api/actions.py`). Frontend `ApiError.detail` type updated to discriminated union with legacy string fallback.

---

## §3 Step-by-step implementation

### Step 0 — Pre-implementation operator config (Supabase + Google Cloud)

**Operator-executed.** Reference: `00_research/operator_prework/043-v3-prework.md`.

**Seven tasks total** (operator confirmation status as of placement):

| Task | Description | Status |
|---|---|---|
| 1 | Supabase: Enable Google OAuth provider; paste GOOGLE_OAUTH_CLIENT_ID + SECRET | ✅ Done |
| 2 | Supabase: Configure Site URL + Redirect URLs | ✅ Done |
| 3 | Supabase: Email domain allowlist | ⏭️ Skipped (free tier; backend authoritative) |
| 4 | Supabase: Email templates | ⏭️ Skipped (OAuth-only) |
| 5 | Google Cloud: Add Supabase callback URI to pulse-web-client | ✅ Done |
| 6 | Local .env vars present | ✅ Done |
| 7 | **NEW v3.2:** Verify Supabase asymmetric JWT signing keys | ✅ Done (ES256 confirmed) |

Task 7 detail: Open Supabase dashboard → Project Settings → JWT Signing Keys. Verify current signing key is asymmetric (RS256 or ES256), NOT legacy HS256. Operator verified ES256 live Session 19 late-late stream extended further v3. If a future operator finds legacy HS256, Supabase one-click migration to asymmetric (~5 min) MUST complete before Step 1.

**Validation:** All 7 tasks dispositioned. Claude Code Step 3 begins unblocked.

### Step 1 — Supabase client setup + env vars

**Backend (`03_build/api/`):**
- Add `supabase>=2.3.0` to `pyproject.toml`
- Add `pyjwt[crypto]>=2.8.0` to `pyproject.toml` — `[crypto]` extras required for asymmetric algorithm support (RSA/EC)
- New file `api/auth/__init__.py` (empty)
- New file `api/auth/supabase_client.py`: factory for Supabase service-role client. Reads `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` from env.
- New file `api/auth/jwt_verify.py`:
  - Uses pyjwt `PyJWKClient` to fetch and cache Supabase JWKS public keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
  - Validates incoming JWTs with **explicit algorithm allowlist `["RS256", "ES256"]`** — rejects HS256 (defense against algorithm-substitution attacks)
  - Verifies signature (asymmetric, with JWKS public key matching `kid` claim), expiry, audience (`"authenticated"` per Supabase convention)
  - Async-safe; refreshes JWKS cache on unknown `kid` (handles Supabase key rotation)
  - Cache TTL: 1 hour default; configurable via `PULSE_JWKS_CACHE_TTL_SEC` env var (default `3600`)
  - Fail-fast on unreachable JWKS endpoint at startup

  Reference implementation pattern (per Supabase docs):
  ```python
  from jwt import PyJWKClient
  import jwt as pyjwt

  jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")

  def verify_token(token: str) -> dict:
      signing_key = jwks_client.get_signing_key_from_jwt(token)
      return pyjwt.decode(
          token,
          signing_key.key,
          algorithms=["RS256", "ES256"],  # NO HS256
          audience="authenticated",
      )
  ```

**Frontend (`03_build/front/`):**
- `npm install @supabase/supabase-js@^2.39.0` (explicit; not transitive)
- New file `front/src/lib/supabase.ts`: factory for browser Supabase client. Reads `import.meta.env.VITE_SUPABASE_URL` + `import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY`
- Update `.env.example`: add `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `PULSE_JWKS_CACHE_TTL_SEC` (default 3600), `PULSE_AUTH_DEV_BYPASS` (default false)

**Validation tests (9 net new):**
- `pytest tests/test_jwt_verify.py` — 7 cases:
  1. JWKS fetch happy path
  2. JWKS fetch failure on cold start (fail-fast)
  3. RS256 signature validation success
  4. ES256 signature validation success
  5. Expired-token rejection
  6. Wrong-audience rejection
  7. **HS256 token rejection** (algorithm-substitution attack defense — verifies allowlist enforced)

  Bonus 8: JWKS cache refresh on unknown `kid` (key rotation handling)
- `npm test -- supabase.test.ts` — 2 cases: client factory shape; throws on missing env vars

**DoD:** Supabase clients installed; `pyjwt[crypto]` installed; 9 tests green; 525 existing tests preserved.

### Step 2 — Backend `require_caller` rewrite + `/profiles` guard (closes #41)

**Rewrite `require_caller` in `api/actions.py`** (audit-verified location — NOT `api/dependencies.py` which does not exist):
- Old: reads `X-User-Id` + `X-User-Role` headers; constructs Caller from header values
- New: reads `Authorization: Bearer <jwt>` header; validates JWT via `jwt_verify.py` (asymmetric RS256/ES256 + JWKS); extracts email from JWT claims; looks up email in `DEMO_USERS` (from `core/auth/demo_users.py` per spec 042); if found → constructs Caller from DEMO_USERS row; if not found → raises HTTPException(403, detail={code: "FORBIDDEN_NOT_IN_ALLOWLIST", message: "Your account is not authorized for Pulse.", context: {email}})
- Preserves spec 042 Caller shape exactly
- **DEV BYPASS:** If `os.getenv("PULSE_AUTH_DEV_BYPASS") == "true"` AND header `X-User-Id` present, fall back to spec 042 header behavior. Default off. Production Fly secrets MUST keep this `false`.

**Add guard to `/profiles`:**
- `api/profiles.py`: add `dependencies=[Depends(require_caller)]` to router
- Verify GET `/profiles/{type}/{id}` and PUT `/profiles/{type}/{id}` both require auth

**Validation tests (12 net new + ~30 existing updated):**
- `pytest tests/test_require_caller_jwt.py` — 8 cases: valid RS256 JWT in DEMO_USERS; valid JWT not in DEMO_USERS; expired JWT; malformed JWT; missing Authorization header; dev bypass enabled with X-User-Id; dev bypass disabled with X-User-Id (rejected); valid JWT with manager role (Caller.executive=false)
- `pytest tests/test_profiles_auth.py` — 4 cases: GET without auth → 401; GET with auth → 200; PUT without auth → 401; PUT with auth → 200
- ~30 existing backend tests using `X-User-*` headers updated to set `PULSE_AUTH_DEV_BYPASS=true` env var (±5 range allowance)

**DoD:** `require_caller` validates Supabase asymmetric JWTs; `/profiles` guarded; 12 net new tests green; existing 284 backend tests preserved via dev bypass.

### Step 3 — Frontend `/login` page + Supabase Auth integration

**New file `front/src/pages/Login.tsx`:**
- Renders Pulse brand + "Sign in with Google" button
- Button click → `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin + '/auth/callback' } })`
- Error state: display "Sign-in failed. Try again." with retry button
- Loading state: button spinner during OAuth redirect
- Design: matches spec 041 Constellation visual language (Tier-0 design tokens, brand `#4a0f70`)

**New file `front/src/pages/AuthCallback.tsx`:**
- On mount: call `supabase.auth.getSession()`
- If session → redirect to `/` (role-defaulted per spec 042)
- If no session after 3s → redirect to `/login?error=callback_failed`
- Loading state: full-screen "Signing you in..." with Pulse breathing orb

**Update `front/src/App.tsx`:**
- Add `<Route path="/login" element={<Login />} />` (outside `<AppShell>`)
- Add `<Route path="/auth/callback" element={<AuthCallback />} />` (outside `<AppShell>`)

**Validation tests (6 net new):**
- `npm test -- Login.test.tsx` — 3 cases
- `npm test -- AuthCallback.test.tsx` — 3 cases
- Manual smoke: `npm run dev` → `localhost:5173/login` → Google button → consent screen → land at `/`

**DoD:** Routes functional; 6 tests green; manual smoke passes.

### Step 4 — Frontend `AsyncAuthProvider` refactor (12 useAuth consumers)

**Rewrite `front/src/contexts/AuthContext.tsx`:**
- Old: synchronous resolver from `localStorage.pulse_dev_user_id`
- New: `AsyncAuthProvider` with loading state:
  - On mount: call `supabase.auth.getSession()`
  - While loading: `user = null, loading = true`
  - After resolution: `user = <DEMO_USERS lookup by JWT email>, loading = false`
  - On `supabase.auth.onAuthStateChange`: re-resolve user
  - Logout: `supabase.auth.signOut()` + clear `localStorage.pulse_dev_user_id`
- **All 12 useAuth consumers** (audit v2 verified; spec 042 close-out added 4 to original 8) must handle `loading === true` state
- Dev user-switcher (`Header.tsx`): preserved; gated `import.meta.env.DEV` AND `!supabase.auth.session()`

**Validation tests (8 net new + ~16 existing updated):**
- `npm test -- AuthContext.test.tsx` — UPDATE + 6 new cases: loading state initial; loading false after session resolves; user populated from Supabase email; logout clears session; onAuthStateChange re-resolves; dev switcher disabled when real session present
- `npm test -- AppShell.test.tsx` — UPDATE + 2 new cases: shows loading state while AuthContext loading; redirects to /login if user null after loading false

**DoD:** AsyncAuthProvider live; `grep -rn "useAuth\|useAuthContext" front/src/` returns 12 sites all updated; 8 net new tests green.

### Step 5 — Frontend logout flow + Header dropdown UI

**Update `front/src/components/Header.tsx`:**
- Current: static avatar `<div>` with initials
- New: clickable avatar opens dropdown menu (net-new UI — no existing dropdown pattern per reconnaissance)
- **Explicit npm install:** `npm install @radix-ui/react-popover@^1.0.7` (audit-verified NOT transitive)
- Menu: user name + email (read-only), divider, "Sign out" button → calls AuthContext `logout()` → redirects to `/login`
- Accessibility: `aria-haspopup`, `aria-expanded`, keyboard navigation (Esc closes, Tab cycles)

**Validation tests (4 net new):**
- `npm test -- Header.test.tsx` — UPDATE + 4 new cases

**DoD:** Logout end-to-end functional; `@radix-ui/react-popover` in package.json + lockfile; 4 net new tests green.

### Step 6 — `/admin/audit` viewer (closes #40)

**Backend `api/admin/audit.py` (NEW file):**
- New router: `APIRouter(prefix="/admin/audit", dependencies=[Depends(require_admin_role)])`
- `require_admin_role` (NEW dependency): wraps `require_caller`, checks `caller.role == "admin"` BEFORE service-role query (prevents privilege escalation). If not admin → 403 with `code: "FORBIDDEN_INSUFFICIENT_ROLE"`
- GET `/admin/audit`: queries `auth.audit_log_entries` via Supabase service-role client. Query params: `?event_type=`, `?email=`, `?limit=` (default 100, max 1000), `?offset=` (default 0)
- Returns JSON: `[{ timestamp, event_type, email, ip_address, user_agent }, ...]`
- Register router in `api/main.py` (5 routers total post-Step-6)

**Frontend `front/src/pages/AdminAudit.tsx` (NEW file):**
- Route `/admin/audit` (inside `<AdminLayout>` sub-route)
- Table view with event-type + email filter dropdowns; pagination
- Admin-only route guard

**Validation tests (10 net new):**
- `pytest tests/test_admin_audit_api.py` — 6 cases
- `npm test -- AdminAudit.test.tsx` — 4 cases

**DoD:** `/admin/audit` route live; 10 net new tests green; manual smoke: admin sign-in → /admin/audit → see login events.

### Step 7 — 403 detail format normalization (closes #37)

**Backend updates:**
- `require_caller` (Step 2): already uses new format
- `require_admin` (`api/admin/kill_switch.py`): `{code: "FORBIDDEN_INSUFFICIENT_ROLE", message: "..."}`
- `require_internal_token` (`api/dispatch.py`): `{code: "FORBIDDEN_INVALID_TOKEN", message: "..."}`
- Spec 042 executive-403 (`api/actions.py`): `{code: "FORBIDDEN_INSUFFICIENT_ROLE", message: "...", context: {required_role: "manager_or_above"}}`
- `require_admin_role` (Step 6): uses new format

**Frontend update `front/src/lib/api.ts`:**
- `ApiError.detail` type → discriminated union with legacy string fallback:
  ```typescript
  type ApiErrorDetail =
    | { code: 'FORBIDDEN_NOT_IN_ALLOWLIST'; message: string; context: { email: string } }
    | { code: 'FORBIDDEN_INSUFFICIENT_ROLE'; message: string; context?: { required_role: string } }
    | { code: 'FORBIDDEN_OUT_OF_SCOPE'; message: string }
    | { code: 'FORBIDDEN_INVALID_TOKEN'; message: string }
    | string; // legacy fallback for unknown codes
  ```
- Update 4 consumer sites per reconnaissance grep

**Validation tests (10 net new + ~4 existing updated):**
- `pytest tests/test_403_format.py` — 5 cases
- `npm test -- api.test.ts` — UPDATE + 5 new cases

**DoD:** All 403 responses structured; 10 net new tests green.

### Step 8 — Service-to-service auth preservation verification

**Verification only — no code changes.**
- `pytest tests/test_dispatch_internal_token.py` — verify `POST /dispatch/{action_id}` still requires `PULSE_INTERNAL_API_TOKEN`
- `pytest tests/test_kill_switch_internal_token.py` — verify `GET/POST /admin/kill-switch` still requires `PULSE_INTERNAL_API_TOKEN`
- Manual: simulate Activepieces cron call with `PULSE_INTERNAL_API_TOKEN` header → 200 (not 401, not redirected)

**DoD:** Existing service-to-service tests green; Activepieces integration paths preserved.

### Step 9 — Integration + close-out

**Integration test (`pytest tests/test_auth_integration.py` — 5 cases, NEW):**
1. Unauthenticated request to `/actions` → 401 (no Authorization header)
2. Valid JWT for DEMO_USERS user → `/actions` returns 200 with caller-scoped data
3. Valid JWT for non-DEMO_USERS user → `/actions` returns 403 with structured FORBIDDEN_NOT_IN_ALLOWLIST detail
4. **Valid RS256/ES256 JWT for `onedge.co` DEMO_USERS user (e.g., Sidra Zia)** → `/actions` returns 200; verifies onedge.co domain accepted
5. **Valid RS256/ES256 JWT for `edgeonline.co` DEMO_USERS user (Iffi Wahla)** → `/actions` returns 200 with executive=true; verifies edgeonline.co domain accepted

Cases 4 + 5 close #30 automated coverage (manual smoke retained for end-to-end).

**Manual smoke test (operator-executed):**
1. Sign in as Iffi Wahla (`iffi.wahla@edgeonline.co`) → executive view
2. Sign in as Sidra Zia (`sidra.zia@onedge.co`) → action queue
3. Sign in as `test@onedge.co` (not in DEMO_USERS) → "Your account is not authorized for Pulse" error
4. Click avatar → Sign out → land at `/login`
5. As admin → `/admin/audit` → see all 4 login events

**DoD criteria (13 rows):**

| # | Criterion | Verification |
|---|---|---|
| 1 | ADR-006 v1.1 honored (Supabase Auth, asymmetric, not hand-rolled) | Code review: no JWT minting in pulse-api |
| 2 | No backend `/auth/*` router mounted | `grep "/auth" api/main.py` returns no router registration |
| 3 | `/login` + `/auth/callback` frontend routes functional | Manual smoke steps 1-2 |
| 4 | AsyncAuthProvider with loading state live | npm test AuthContext.test.tsx green |
| 5 | All 12 useAuth consumers handle loading state | `grep -rn "useAuth" front/src/` returns 12; no flash-of-unauthenticated |
| 6 | `/profiles` guarded (closes #41) | pytest test_profiles_auth.py green |
| 7 | `/admin/audit` viewer functional (closes #40) | Manual smoke step 5 |
| 8 | 403 detail format normalized (closes #37) | pytest test_403_format.py green |
| 9 | Multi-domain SSO works (closes #30) | Manual smoke + integration cases 4+5 (automated) |
| 10 | `PULSE_INTERNAL_API_TOKEN` preserved | pytest service-to-service tests green |
| 11 | Logout flow end-to-end | Manual smoke step 4 |
| 12 | All 525 existing tests preserved | full pytest + vitest green |
| 13 | **JWT verification asymmetric only** | `grep "HS256" 03_build/api/` returns zero matches in production code paths; `jwt_verify.py` algorithm allowlist = `["RS256", "ES256"]`; `pyjwt[crypto]` in pyproject.toml |

**Close-out commit:** `[SPEC-043] Step 9 DoD close-out — Supabase Auth (asymmetric JWT) integration CLOSED`. Updates this spec §17 with full DoD report + watched-concerns closures.

---

## §4 Test count summary

| Step | Net new tests | Updates to existing tests |
|---|---|---|
| 1 | 9 (7 pytest + 2 vitest) | 0 |
| 2 | 12 (8 + 4) | ~30 spec 042 backend tests (PULSE_AUTH_DEV_BYPASS setup; ±5 range) |
| 3 | 6 (0 + 6) | 0 |
| 4 | 8 (0 + 8) | ~4 AppShell + ~12 useAuth consumer tests (±5 range) |
| 5 | 4 (0 + 4) | 0 |
| 6 | 10 (6 + 4) | 0 |
| 7 | 10 (5 + 5) | ~4 ApiError consumer tests |
| 8 | 0 | 0 |
| 9 | 5 (5 + 0) | 0 |
| **Total** | **~64 new** | **~50 updated (±5 range)** |

**Final test posture target:** ~589 tests green (525 existing + ~64 new). Range allowance ±5 for implementation discovery.

---

## §5 Files touched

**Backend (new):** `api/auth/__init__.py`, `api/auth/supabase_client.py`, `api/auth/jwt_verify.py`, `api/admin/audit.py`, 6 new test files

**Backend (modified):** `pyproject.toml` (add `supabase`, `pyjwt[crypto]`), `api/actions.py` (rewrite `require_caller`), `api/main.py` (register admin/audit router), `api/profiles.py` (add `require_caller` guard), `api/admin/kill_switch.py` (403 format), `api/dispatch.py` (403 format), ~30 existing backend tests (PULSE_AUTH_DEV_BYPASS setup)

**Frontend (new):** `front/src/lib/supabase.ts`, `front/src/pages/Login.tsx`, `front/src/pages/AuthCallback.tsx`, `front/src/pages/AdminAudit.tsx`, 4 new test files

**Frontend (modified):** `package.json` + lockfile (add `@supabase/supabase-js@^2.39.0` + `@radix-ui/react-popover@^1.0.7` — both explicit installs), `src/contexts/AuthContext.tsx`, `src/components/Header.tsx`, `src/components/AppShell.tsx`, `src/lib/api.ts`, `src/App.tsx`, all 12 useAuth consumers, ~4 existing tests

**Config:** `.env.example` (add `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `PULSE_AUTH_DEV_BYPASS=false`, `PULSE_JWKS_CACHE_TTL_SEC=3600`)

**No migration files needed** (Supabase manages `auth.*` schema).

---

## §6 Environment variables required

**Already in operator's local `.env` (verified Session 19 late-late stream extended further v3):**
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` (frontend-safe; aka anon key)
- `SUPABASE_SERVICE_ROLE_KEY` (backend admin operations; sensitive)
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `PULSE_INTERNAL_API_TOKEN` (operator added 2026-05-23 per audit v4 correction; previously absent from local `.env` despite reconnaissance framing; **production Fly secret must also be set at Step 9 close**; Activepieces must send matching value)

**New in spec 043 v3.2 (operator adds at Step 1):**
- `VITE_SUPABASE_URL` (frontend build-time mirror of `SUPABASE_URL`)
- `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend build-time mirror of `SUPABASE_PUBLISHABLE_KEY`)
- `PULSE_AUTH_DEV_BYPASS` (default `false`; MUST stay `false` in Fly production secrets)
- `PULSE_JWKS_CACHE_TTL_SEC` (default `3600`; optional tuning)

**Explicitly NOT needed under asymmetric path:**
- ❌ `SUPABASE_JWT_SECRET` — not needed; asymmetric verification uses public keys from JWKS endpoint, not a shared secret. Setting this env var would be a no-op and a security smell.
- ❌ `PULSE_JWT_SECRET` (legacy from hand-rolled v1/v2 drafts)
- ❌ `PULSE_COOKIE_INSECURE_DEV`, `PULSE_COOKIE_DOMAIN` (Supabase manages cookies)

---

## §7 Operator pre-work

**File:** `00_research/operator_prework/043-v3-prework.md` (placed by operator Session 19 late-late stream extended further v3).

**Status:** Seven tasks dispositioned (see §3 Step 0 status table). All confirmed by operator. Step 3 unblocked.

Production Fly secrets to set at Step 9 close:
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (on Vercel project, not Fly — frontend env)
- `PULSE_AUTH_DEV_BYPASS=false` (Fly pulse-api)
- `PULSE_JWKS_CACHE_TTL_SEC=3600` (Fly pulse-api, optional)
- Verify `PULSE_INTERNAL_API_TOKEN` set on Fly pulse-api + matching value sent by Activepieces

---

## §8 Watched concerns closure tracking

Closes at Step 9 DoD: #30 (multi-domain SSO via backend DEMO_USERS check + automated integration cases 4+5), #37 (403 format normalization), #40 (`/admin/audit` viewer + Supabase audit log), #41 (`/profiles` guard).

Does NOT close: #42 (ADR-supersession process — codified as standing rule), #43 (AWS migration scope — Path C deferred post-demo).

---

## §9 Rollback strategy

If implementation surfaces post-deploy blocker:

1. Frontend rollback: revert AuthContext to spec 042 synchronous resolver; remove `/login` + `/auth/callback` routes; revert Header dropdown. Dev user-switcher remains functional. ~30 min.
2. Backend rollback: `fly secrets set --app pulse-api PULSE_AUTH_DEV_BYPASS=true` → Fly auto-restarts → spec 042 X-User-* header behavior resumes. `/profiles` guard remains active (no functional regression). ~5 min.
3. Supabase Auth state: leave configured (no rollback needed at Supabase layer).

**Acceptance:** All 525 spec 042 tests green; 11 demo personas usable via dev switcher.

---

## §10 Audit pointers for any future re-audit

Any future audit should verify:

1. ADR cross-reference: spec cites `ADR-006-authentication.md` v1.1
2. Reconnaissance grounding: infrastructure claims trace to `acc6ed1`
3. Service-to-service preservation: `PULSE_INTERNAL_API_TOKEN` integrity (Step 8)
4. Test count claims within ±5 range allowance
5. Operator pre-work completeness (7 tasks including Task 7 asymmetric verification)
6. Dev-bypass safety: production Fly secrets keep `PULSE_AUTH_DEV_BYPASS=false`
7. **JWT signing algorithm asymmetric:** `grep "HS256" 03_build/api/` returns zero matches in production code paths; `jwt_verify.py` algorithm allowlist is `["RS256", "ES256"]`; `pyjwt[crypto]` listed in pyproject.toml
8. **NO `SUPABASE_JWT_SECRET` env var read by backend code:** asymmetric verification uses JWKS public keys only
9. JWKS caching strategy: refresh on unknown `kid`; cache TTL configurable
10. Multi-domain test coverage: integration cases 4-5 cover both onedge.co + edgeonline.co
11. 403 discriminated union safety with legacy string fallback
12. No hand-rolled JWT remnants: zero `jwt.encode()` calls in `03_build/api/`
13. `require_caller` correct file location: `api/actions.py`
14. useAuth consumer count: 12
15. `@radix-ui/react-popover` explicit install in package.json + lockfile

---

*End of Spec 043 v3.2.*

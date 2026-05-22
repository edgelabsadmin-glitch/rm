# Spec 043 — OAuth + Production-Grade Auth + Audit Observability

**Status:** Ratified Session 19 late-late stream extended further v2 per pre-spec audit (memo at `00_research/audits/pre_spec_043_oauth_audit.md`, commit `b7b90b3`). PM dispositions applied this commit: H1 + H2 + A1-A7 + I-items reviewed; 9 edits landed. Awaiting Step 1 implementation prompt next. Lands on `dz-001` (or successor branch per operator merge decision); merge to `main` awaits separate operator authorization.

**Author:** PM (Senior Product Advisor)
**Date drafted:** 2026-05-22 (Session 19 late-late stream extended further)
**Estimated effort:** ~5-6h Claude Code across 7 steps + ~30 min pre-spec audit
**Demo target:** 2026-06-30
**Supersedes:** Dev `X-User-*` header convention (spec 031 Phase 1A pattern)
**Closes watched concerns:** #29 (retired dev JWT injector), #30 (multi-domain SSO), #37 (403 detail format), #40 (NEW — auth observability per operator-stated load-bearing concern)

---

## 1. Why this spec

Spec 042 closed Phase 1A RBAC with a working AuthContext + Caller model populated from dev-mode `X-User-*` headers. That convention enabled fixture-based persona switching during local development but is not production-suitable: anyone with knowledge of the header names can spoof identity. Phase 1B production requires real authenticated identity.

**Spec 043 replaces dev headers with Google Workspace OAuth** for the two EDGE domains (`onedge.co` primary, `edgeonline.co` secondary), populates AuthContext from verified JWT claims, and populates backend `Caller` from the same source — eliminating the spoofing surface and making the production session lifecycle real.

**Additionally — and this is load-bearing per operator feedback** — the spec elevates auth observability to a primary deliverable. Operator-stated concern from prior agent builds: thin error messages on OAuth failures ("can't login", "account not connected") cost hours of debugging time because no structured trail exists. Spec 043 addresses this by:

1. **Structured error codes at every auth failure boundary** — front-end and backend return well-typed errors with `{code, message, remediation}` shape, not opaque strings.
2. **Auth audit log table** writing every login attempt (success and failure) with sufficient diagnostic context to debug a failure without reproducing it.
3. **Admin-accessible audit viewer at `/admin/audit`** — operator can see real-time auth events during demo or production without leaving the app.

Scope per operator ratification (Hybrid disposition Session 19 late-late stream extended further):
- ✓ Structured errors (front-end + backend)
- ✓ Audit log table + write path
- ✓ Minimal admin viewer (reverse-chronological, last 100 events, expandable rows)
- ✗ Real-time alerting (Phase 2 — watched concern carry-forward)
- ✗ Replay capability (Phase 2)
- ✗ Anomaly detection (Phase 2)

---

## 2. Audience + framing

This spec is for the operator + future contributing engineers. It documents what we build, why we make specific architecture choices, what we don't build (and why), and what carries forward to Phase 2.

The product surface this spec touches: every page (login required), Header (logout flow), AdminLayout (new audit sub-route), backend `Caller` model population.

---

## 3. Architecture overview

### 3.1 OAuth flow (high level)

```
[User]
  │
  ▼
GET /                                  # initial visit
  │
  ▼
AuthContext checks for valid session   # cookie-based; httpOnly
  │
  ├─ valid → hydrate AuthContext from JWT claims → render app
  │
  └─ invalid/missing → redirect to /login
     │
     ▼
GET /login                             # shows "Sign in with Google" button
  │ click
  ▼
GET /api/auth/google                    # backend redirects to Google OAuth
  │
  ▼
Google Workspace consent screen
  │ user authorizes
  ▼
GET /api/auth/google/callback           # Google redirects back with code
  │
  ├─ verify state nonce
  ├─ exchange code for tokens
  ├─ verify ID token signature + claims
  ├─ check domain in {onedge.co, edgeonline.co}
  ├─ lookup user in DEMO_USERS by email
  ├─ write pulse.auth_audit_log row (success or specific failure code)
  │
  ├─ success → set httpOnly session cookie → redirect to /
  │
  └─ failure → redirect to /login?error=<code>
```

### 3.2 Token storage

**httpOnly, Secure, SameSite=Lax session cookie** containing a server-signed JWT. Two-token pattern:

- **`pulse_session`** (~1h lifetime) — short-lived access token used by API
- **`pulse_refresh`** (~30d lifetime) — refresh token used to renew access token

Stored as httpOnly cookies (not localStorage) to mitigate XSS exfiltration. SameSite=Lax allows OAuth callback redirect from Google while preventing CSRF on cross-origin API.

Refresh happens on access-token 401 from any API call: front-end calls `POST /api/auth/refresh`; if refresh token still valid, get new access token + retry original API call; if refresh token expired, force logout.

### 3.3 AuthContext hydration (replaces spec 042 dev-header convention)

Spec 042 currently:
- `AuthProvider({initialUserId = 'pulse-admin'})` reads from `DEMO_USERS` directly
- Dev-mode user switcher in Header lets operator pick any DemoUser
- `useAuth().user` is always non-null `DemoUser` — every consumer downstream of AuthProvider assumes this

Spec 043 changes (PRESERVING non-null user contract — H2 disposition):
- `AuthProvider` accepts optional `initialUserId` (retained for DEV + tests; bypasses async fetch)
- In production (no `initialUserId`), AuthProvider calls `GET /api/auth/me` on mount
- WHILE async fetch is in flight: AuthProvider renders a loading boundary INTERNALLY (loading state never escapes to consumers)
- On success: AuthProvider hydrates `user` + `accountScope` → renders children with non-null `user`
- On failure (401, network error): AuthProvider redirects to `/login` → never renders children
- Dev-mode user switcher remains gated `import.meta.env.DEV` for local development only — production build omits it

The AuthContext **interface remains unchanged for consumers**: `useAuth().user` is always non-null `DemoUser` when consumer code runs. The loading/redirect concerns are encapsulated within AuthProvider itself.

Implementation pattern:

```typescript
export function AuthProvider({ children, initialUserId }: AuthProviderProps) {
  // Test/DEV path: synchronous hydration from DEMO_USERS by id
  if (initialUserId !== undefined) {
    return <AuthContextProvider userId={initialUserId}>{children}</AuthContextProvider>;
  }

  // Production path: async hydration from /api/auth/me
  return <AsyncAuthProvider>{children}</AsyncAuthProvider>;
}

function AsyncAuthProvider({ children }: { children: ReactNode }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['auth-me'],
    queryFn: fetchAuthMe,
  });

  if (isLoading) return <FullScreenLoader />;
  if (error || !data) {
    // Redirect to /login; render nothing (no consumer code runs)
    return <Navigate to="/login?error=session_expired" replace />;
  }

  return (
    <AuthContextProvider userId={data.user.id} hydrated={data}>
      {children}
    </AuthContextProvider>
  );
}
```

The `AuthContextProvider` (inner) preserves the existing spec 042 contract; downstream `useAuth()` consumers see non-null user with no behavior change. Existing 525-test baseline is unaffected: test files mount `AuthProvider initialUserId={...}` and take the synchronous path.

### 3.4 Backend Caller population (replaces header parsing)

Spec 031 + spec 042 currently:
- `get_caller()` reads `X-User-Id` + `X-User-Role` headers
- Returns `Caller(user_id=..., role=...)`

Spec 043 changes:
- `get_caller()` reads `pulse_session` cookie
- Verifies JWT signature + expiry
- Returns `Caller(user_id=claim.sub, role=claim.role)` populated from verified claims
- On verification failure: returns 401 with structured error (NOT 403; identity unverified is 401, scope insufficient is 403 per HTTP standards)

The `Caller` model itself stays unchanged. Spec 042's `require_queue_caller` defense-in-depth dependency continues to work — it gates AFTER identity verification.

---

## 4. Multi-domain Google Workspace configuration

### 4.1 Domain setup

Single Google Cloud project hosts the OAuth client. Authorized domains in OAuth consent screen:
- `onedge.co` (primary — 10 users: Eddy, Sarah, Muhammad, Sidra, Sajjal, Yozeline, Ameer, Mubeen, Akash, Pulse Admin)
- `edgeonline.co` (secondary — 1 user: Iffi Wahla)

Authorized redirect URIs (configured in Google Cloud console):
- `http://localhost:5173/api/auth/google/callback` (development)
- `https://pulse.onedge.co/api/auth/google/callback` (production, when deployed)

OAuth scopes requested (minimal):
- `openid` — required
- `email` — required for domain check + user lookup
- `profile` — required for displayName fallback

**No additional scopes** — spec 043 is identity only. Adapter ingestion specs handled this separately (specs 012-014).

### 4.2 Email canonicalization

Per Session 19 late-late stream operator ratification: `{first}.{last}@onedge.co` for all users except Iffi Wahla on `edgeonline.co`. Email comparison must be case-insensitive (Google returns lowercase but defensive comparison anyway).

```python
def normalize_email(email: str) -> str:
    return email.strip().lower()
```

### 4.3 Domain allowlist enforcement (backend)

```python
ALLOWED_DOMAINS = {"onedge.co", "edgeonline.co"}

def is_domain_allowed(email: str) -> bool:
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1].lower()
    return domain in ALLOWED_DOMAINS
```

Domain check runs BEFORE DEMO_USERS lookup. Wrong-domain attempts get `domain_not_allowed` error without disclosing whether the user exists in our allowlist (security — don't leak provisioning state to unauthorized domains).

### 4.4 User provisioning (allowlist-only — Hybrid disposition Q2)

After domain check passes: lookup user by normalized email in `DEMO_USERS` table.

```python
def find_user_by_email(email: str) -> Optional[DemoUser]:
    normalized = normalize_email(email)
    return next((u for u in DEMO_USERS if u.email == normalized), None)
```

If found → success path (write audit, mint tokens, redirect to `/`).
If not found → `user_not_provisioned` error (audit logs the attempted email so admin can debug).

**Why allowlist-only (Phase 1A):** the demo audience is fixed (11 known users). Auto-provisioning at this scale is over-engineering. Phase 2 spec will add proper user-creation flow on Settings panel.

**Phase 2 carryforward:** when EDGE onboards new RMs post-demo, admin will be able to add users via Settings panel (extends existing `/settings/users` from spec 042 Step 7) without code change.

---

## 5. Structured error code taxonomy

Every auth failure path returns a structured error with shape:

```typescript
interface AuthError {
  code: AuthErrorCode;
  message: string;        // human-readable
  remediation: string;    // actionable guidance for end-user
  attempted_email?: string;  // diagnostic only; admin audit log includes; NOT in user-facing URL
}

type AuthErrorCode =
  | 'oauth_state_mismatch'        // CSRF defense — state nonce didn't match
  | 'oauth_provider_error'         // Google returned error during code exchange
  | 'token_verification_failed'    // ID token signature or claims invalid
  | 'domain_not_allowed'           // email domain not in onedge.co / edgeonline.co
  | 'user_not_provisioned'         // domain ok but email not in DEMO_USERS
  | 'session_expired'              // pulse_session cookie expired, refresh failed
  | 'session_invalid'              // pulse_session cookie malformed or signature failed
  | 'no_session'                   // no cookie present (initial visit)
  | 'rate_limited'                 // (Phase 2 enables; Phase 1A wires the code but rate limit logic is Phase 2)
  | 'internal_error';              // catchall — backend exception during auth
```

### 5.1 Error code mapping table

| Code | When it fires | User sees | Audit logs |
|---|---|---|---|
| `oauth_state_mismatch` | Callback state nonce ≠ cookie nonce | "Login attempt was interrupted. Please try again." | All, with `state_in_cookie`, `state_in_callback` for forensic |
| `oauth_provider_error` | Google `/token` exchange returned error | "Sign-in with Google failed. Please try again or contact support." | All, with raw Google error response |
| `token_verification_failed` | ID token signature/claim verify failed | "Sign-in verification failed. Please try again." | All, with which check failed |
| `domain_not_allowed` | Email domain ∉ allowed set | "Your email domain is not authorized for Pulse. Contact your admin." | All, with attempted domain |
| `user_not_provisioned` | Email not in DEMO_USERS | "Your account is not provisioned for Pulse. Contact your admin." | All, with attempted email |
| `session_expired` | Access token expired, refresh failed | "Your session expired. Please sign in again." | Log + redirect to /login |
| `session_invalid` | Cookie tampered/malformed | "Your session is invalid. Please sign in again." | Log + clear cookie + redirect |
| `no_session` | No cookie on protected route | (silently redirects to /login) | No log (every initial visit hits this) |
| `rate_limited` | (Phase 2) Too many attempts | "Too many login attempts. Try again in N minutes." | All, with attempt count |
| `internal_error` | Backend exception during auth flow | "Something went wrong. Please try again." | All, with stack trace + exception type |

### 5.2 What end-user sees vs what admin sees

**End-user view (login page):**
- Top-of-page banner with error message + remediation
- No technical details, no exposed `attempted_email` in URL (prevents email enumeration via shared screenshots)
- Persistent across refresh until user clicks dismiss or retries login

**Admin view (`/admin/audit`):**
- Full audit row with timestamp, ip, user_agent, attempted_email, error code, raw diagnostics
- Color-coded: success = good-on-brand, failure = risk-on-brand
- Click row → expand to see full diagnostic payload (state nonces, token claim subset, exception traces if internal_error)

---

## 6. Front-end error UI

### 6.1 Login page (`/login`)

New route `/login` (no RoleGuard — unauthenticated route):

```
┌─────────────────────────────────────────────┐
│   Pulse                                     │
│                                             │
│   Relationship intelligence for RMs         │
│                                             │
│   ┌─────────────────────────────────────┐  │
│   │  Sign in with Google                │  │
│   └─────────────────────────────────────┘  │
│                                             │
│   [error banner appears here if error param]│
│                                             │
└─────────────────────────────────────────────┘
```

Error param handling: `/login?error=<code>` triggers banner rendering. Banner content from error code mapping table §5.1.

### 6.2 In-app session-expiry handling

When ANY API call returns 401:
1. Front-end automatically calls `POST /api/auth/refresh`
2. If refresh succeeds → retry original API call (transparent to user)
3. If refresh fails → AuthContext clears local state → redirect to `/login?error=session_expired`

This pattern wraps the fetch layer (likely via `lib/api.ts` — the API client already exists from spec 042 Step 2; extend it).

### 6.3 Logout flow

Header dropdown gains "Sign out" item below the avatar:

```
┌──────────────┐
│ Pulse Admin  │
│ admin@...co  │
├──────────────┤
│ Sign out     │ ← new
└──────────────┘
```

Click → `POST /api/auth/logout` → backend clears cookies → front-end redirects to `/login` → audit log writes `logout` event (Phase 2 may add; Phase 1A logs only login attempts).

### 6.4 Front-end ApiError type extension (A3 disposition)

Per audit A3: the existing `ApiError.detail` in the front-end client (`src/lib/api.ts`) is typed as `string`, but spec 042 Step 6 already returns a structured 403 detail object (the executive block), and spec 043 introduces structured 401/403 detail objects throughout. The field already silently holds objects in the executive-403 path today.

Type update (lands in Step 5):

```typescript
// src/lib/api.ts
interface AuthErrorDetail {
  code: AuthErrorCode;
  message: string;
  remediation?: string;
  required_roles?: UserRole[];
  user_role?: UserRole;
}

interface ApiError {
  status: number;
  detail: string | AuthErrorDetail;  // discriminated at consumer site
}
```

Consumers discriminate via a runtime `typeof` check; structured-detail consumers (login page error banner, audit viewer, refresh handler) cast to `AuthErrorDetail` after `typeof detail === 'object'`. String-detail consumers (existing queue error display) keep working unchanged.

---

## 7. Backend structured 401/403 responses

### 7.1 Endpoint additions

New endpoints (extend existing `api/` module):

```
GET    /api/auth/google              → initiate OAuth (redirect to Google)
GET    /api/auth/google/callback     → handle Google callback (success/failure)
GET    /api/auth/me                  → return current user from session cookie
POST   /api/auth/refresh             → refresh access token using refresh cookie
POST   /api/auth/logout              → clear cookies, audit log
GET    /api/auth/audit               → admin-only; last 100 audit log events
```

### 7.2 Response shape

**Success (`/api/auth/me`):**
```json
{
  "user": {
    "id": "iffi-wahla",
    "displayName": "Iffi Wahla",
    "email": "iffi.wahla@edgeonline.co",
    "role": "executive",
    "avatarInitials": "IW"
  },
  "accountScope": ["dhr-health-clinics", "dhr-health-hospital", "..."]
}
```

**Failure (401 with structured detail):**
```json
{
  "detail": {
    "code": "user_not_provisioned",
    "message": "Your account is not provisioned for Pulse.",
    "remediation": "Contact your admin to be added."
  }
}
```

Note: 401 detail format **matches** spec 042 Step 6 executive 403 structured format (per watched concern #37 normalization direction — spec 043 is the natural checkpoint to converge backend error formats).

### 7.3 Existing string-detail 403 normalization (closes #37 — expanded scope per audit)

Per watched concern #37 + audit advisory A1: existing string-detail 403s in the backend are NOT limited to `api/actions.py` scope-403 path. Audit identified additional string-detail 403s in:

- `api/dispatch.py` — dispatch endpoint 403s (`"internal token required"`, `str(e)`)
- `api/admin/kill_switch.py` — kill switch endpoint 403 (`"admin token required"`)
- `api/actions.py:73` — the `require_caller` invalid-role 403 (`"valid X-User-Id and X-User-Role required"`) + `api/actions.py:139` scope-403 (`"action outside your scope"`)

(Note: the spec 042 Step 6 executive-block 403 at `api/actions.py:82` is **already structured** and is the format target.)

Spec 043 Step 7 normalization pass converts ALL existing string-detail 403s in these files to structured detail matching the spec 043 pattern:

```python
detail = {
    "error": "<specific_error_code>",
    "required_roles": [...],  # or "required_scope" depending on context
    "user_role": "<caller_role>",
    "message": "<human-readable message>",
    "remediation": "<actionable guidance>",
}
```

Adds ~10 min to Step 7 budget (estimate revised from ~30 to ~40 min). Watched concern #37 closes more thoroughly than originally planned.

---

## 8. Auth audit log

### 8.1 Schema

New Postgres table `pulse.auth_audit_log` (H1 disposition — psycopg3 + `pulse.` schema + app-generated UUID, matching the existing migration conventions in `migrations/0001`–`0008`):

```sql
-- Migration file: 0009_auth_audit_log.sql (verified next available; 0008 is the last existing).

CREATE TABLE pulse.auth_audit_log (
  id              TEXT PRIMARY KEY,                    -- app-generated UUID (str(uuid.uuid4())); matches existing migration pattern (no DB-side default)
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  attempted_email TEXT,                  -- nullable; null for no_session
  attempted_domain TEXT,                  -- denormalized for query convenience
  user_id         TEXT,                  -- nullable; null when lookup failed
  role            TEXT,                  -- nullable; null when lookup failed
  success         BOOLEAN NOT NULL,
  error_code      TEXT,                  -- nullable; null when success=true
  ip_address      INET,                  -- captured from request (X-Forwarded-For aware; see §8.2)
  user_agent      TEXT,                  -- captured from request
  diagnostics     JSONB,                 -- nullable; full diagnostic payload
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_auth_audit_log_ts ON pulse.auth_audit_log(ts DESC);
CREATE INDEX idx_auth_audit_log_email ON pulse.auth_audit_log(attempted_email) WHERE attempted_email IS NOT NULL;
CREATE INDEX idx_auth_audit_log_error ON pulse.auth_audit_log(error_code) WHERE error_code IS NOT NULL;
```

### 8.2 Write path

`write_auth_audit(...)` function called at every terminal point in the OAuth callback handler. Written in **psycopg3 idiom** (`%s` placeholders + `async with pool.connection()/cursor()`, matching `core/ingest/pipeline.py`), app-generated UUID, and **X-Forwarded-For-aware IP capture** (A6):

```python
import uuid

async def write_auth_audit(
    *,
    attempted_email: Optional[str],
    user_id: Optional[str],
    role: Optional[str],
    success: bool,
    error_code: Optional[str],
    request: Request,
    diagnostics: Optional[dict] = None,
) -> None:
    domain = (
        attempted_email.split("@", 1)[1] if attempted_email and "@" in attempted_email
        else None
    )

    # Prefer X-Forwarded-For (production behind reverse proxy); fall back to direct client (per A6)
    ip_address = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pulse.auth_audit_log
                (id, attempted_email, attempted_domain, user_id, role, success, error_code,
                 ip_address, user_agent, diagnostics)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    attempted_email,
                    domain,
                    user_id,
                    role,
                    success,
                    error_code,
                    ip_address,
                    request.headers.get("user-agent"),
                    json.dumps(diagnostics) if diagnostics else None,
                ),
            )
```

(`pool` is obtained via the existing `await get_pool()` chokepoint in `core/db.py`.)

### 8.3 Write triggers (which events get logged)

| Event | Logged? | error_code | Notes |
|---|---|---|---|
| Successful login | ✓ | null | success=true |
| Failed login — domain not allowed | ✓ | `domain_not_allowed` | attempted_email captured |
| Failed login — user not provisioned | ✓ | `user_not_provisioned` | attempted_email captured |
| Failed login — state mismatch | ✓ | `oauth_state_mismatch` | diagnostics include state values |
| Failed login — provider error | ✓ | `oauth_provider_error` | diagnostics include Google error |
| Failed login — token verify | ✓ | `token_verification_failed` | diagnostics include which check failed |
| Token refresh success | ✓ | null | success=true; user_id from refresh token |
| Token refresh failure | ✓ | `session_expired` | logged BEFORE redirecting to /login |
| Logout | ✗ (Phase 2) | — | not load-bearing; Phase 2 may add |
| No session on protected route | ✗ | — | not a "failure" per se; just an unauthenticated visit |
| Session expired during /api call | ✗ | — | the refresh attempt's failure is what gets logged |

### 8.4 Retention (Phase 1A)

No active retention policy. Table grows unbounded.

**Realistic Phase 1A volume estimate (corrected per audit A7):**
- 11 users active during demo prep + demo
- Refresh-token events fire ~hourly per active user (dominant source — the audit caught that the earlier estimate omitted this)
- Login events (initial + occasional re-login): ~2-5 per user per day
- Estimate: 11 users × ~8 active hours × 30 days = ~2,640 refresh events + ~660 login events = ~3,300 rows
- With failure cases + edge cases, realistic upper bound: ~5,000 rows over the Phase 1A window

5,000 rows is well within "unbounded acceptable" for Postgres; the `ts DESC` index keeps queries sub-millisecond.

**Phase 2 carryforward:** retention policy (e.g. 90 days hot + S3 archive cold). Real production volume after EDGE-wide rollout could be 100x-1000x the demo-window estimate.

---

## 9. Admin audit viewer (`/admin/audit`)

### 9.1 Route + access

New sub-route on AdminLayout: `/admin/audit`. AdminLayout is already wrapped in `RoleGuard(['admin'])` per spec 042 Step 3. No new RoleGuard needed.

Adding to AdminLayout sub-nav:
- `/admin` (existing — admin home)
- `/admin/audit` ← new

### 9.2 View composition

Reverse-chronological table; last 100 events; expandable rows:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Auth audit log                                          Last 100 events  │
├──────────────────────────────────────────────────────────────────────────┤
│ Timestamp           Email                       Result      Code         │
├──────────────────────────────────────────────────────────────────────────┤
│ 2026-05-22 14:32:18 iffi.wahla@edgeonline.co    ✓ success                │ ◀ click
│ 2026-05-22 14:28:04 sajjal@onedge.co            ✗ failure  user_not_pr… │
│ 2026-05-22 14:27:51 sajjal.shaheedi@onedge.co   ✓ success                │
│ 2026-05-22 14:21:00 eddy@gmail.com              ✗ failure  domain_not…  │
│ ...                                                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Row coloring:**
- Success rows: subtle good-on-brand left border
- Failure rows: subtle risk-on-brand left border + error code chip

**Click row to expand:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ 2026-05-22 14:28:04 sajjal@onedge.co            ✗ failure  user_not_pr…  │
│   ┌──────────────────────────────────────────────────────────────┐      │
│   │ Attempted email:  sajjal@onedge.co                           │      │
│   │ Attempted domain: onedge.co                                  │      │
│   │ Error code:       user_not_provisioned                       │      │
│   │ Remediation:      Contact your admin to be added.            │      │
│   │ IP address:       192.168.1.50                               │      │
│   │ User agent:       Mozilla/5.0 ... Chrome/...                 │      │
│   │ Diagnostics:      { ... }                                    │      │
│   └──────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

The "user agent" + "IP" should make demo-day debugging trivial: admin sees a failed login, opens audit, sees exactly what email was attempted and from where.

### 9.3 Backend endpoint

```
GET /api/auth/audit?limit=100  → admin-only; returns last N events

Caller role check: must be 'admin' (NOT executive — audit is admin observability, not executive insight)
```

Response shape:
```json
{
  "events": [
    {
      "id": "...",
      "ts": "2026-05-22T14:32:18Z",
      "attempted_email": "iffi.wahla@edgeonline.co",
      "attempted_domain": "edgeonline.co",
      "user_id": "iffi-wahla",
      "role": "executive",
      "success": true,
      "error_code": null,
      "ip_address": "192.168.1.10",
      "user_agent": "Mozilla/...",
      "diagnostics": null
    }
  ]
}
```

### 9.4 Phase 2 carryforwards (NOT in this spec)

- Real-time updates (WebSocket / Server-Sent Events) — Phase 1A is on-load fetch
- Filter/search by email, error code, date range
- Pagination beyond first 100
- Alerting (e.g., email admin on 3+ failures for same email in 1 hour)
- Replay capability
- Export to CSV

---

## 10. Token lifecycle

### 10.1 Token shape

**Access token (`pulse_session` cookie):**
```json
{
  "sub": "iffi-wahla",
  "email": "iffi.wahla@edgeonline.co",
  "role": "executive",
  "iat": 1716394338,
  "exp": 1716397938,
  "iss": "pulse-api",
  "aud": "pulse-frontend"
}
```

**Refresh token (`pulse_refresh` cookie):**
```json
{
  "sub": "iffi-wahla",
  "type": "refresh",
  "iat": 1716394338,
  "exp": 1718986338,
  "iss": "pulse-api",
  "aud": "pulse-frontend"
}
```

Both signed with same HS256 secret (env var `PULSE_JWT_SECRET`, 32+ bytes random).

### 10.2 Cookie attributes

```
Set-Cookie: pulse_session=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=3600
Set-Cookie: pulse_refresh=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/api/auth/refresh; Max-Age=2592000
```

`Path=/api/auth/refresh` on refresh cookie restricts its exposure — only the refresh endpoint sees it.

`Secure` flag required in production (HTTPS); dev override via env `PULSE_COOKIE_INSECURE_DEV=true` for `localhost`.

### 10.3 Refresh flow

```
[Front-end API call] → 401 from any /api/* endpoint
  │
  ▼
[Front-end fetch wrapper detects 401]
  │
  ▼
POST /api/auth/refresh                  # refresh cookie sent (Path matches)
  │
  ├─ refresh token valid
  │   ├─ verify signature + expiry
  │   ├─ look up user in DEMO_USERS by sub claim
  │   ├─ mint new access token (1h)
  │   ├─ Set-Cookie: pulse_session=<new JWT>
  │   ├─ write audit log (success, refresh event)
  │   └─ return 200
  │
  └─ refresh token invalid/expired
      ├─ write audit log (failure, session_expired)
      ├─ clear both cookies
      └─ return 401 with structured detail
  │
  ▼
[Front-end: 200 → retry original API call] OR [401 → redirect to /login?error=session_expired]
```

### 10.4 Forced logout

`POST /api/auth/logout`:
- Clears `pulse_session` cookie (Set-Cookie with Max-Age=0)
- Clears `pulse_refresh` cookie
- No audit log Phase 1A (Phase 2 may add)
- Returns 200 with empty body

Front-end redirects to `/login` after success.

---

## 11. Cross-spec coordination

### 11.1 Spec 042 (RBAC) — interface preserved, population source changes

AuthContext interface unchanged:
- `user: DemoUser`
- `accountScope: AccountScope`
- `switchUser: (id: string) => void` (DEV-only consumer; production builds may exclude)

Backend `Caller` model unchanged. `require_queue_caller` defense-in-depth wrapper continues to work.

Migration (H2 disposition — non-null `user` contract preserved):
- `AuthProvider` **retains** the optional `initialUserId` prop (DEV + test path, synchronous hydration)
- In production (no `initialUserId`), AuthProvider takes the async path: calls `GET /api/auth/me` on mount, renders an internal loading boundary while in flight, hydrates `user` + `accountScope` on success, redirects to `/login` on failure
- The loading/null state is **encapsulated inside AuthProvider** — `useAuth().user` remains non-null for every consumer, so no downstream component changes
- **Existing 525-test baseline does not break:** all test files mount `AuthProvider initialUserId={...}` and take the synchronous path (see §3.3 implementation pattern)

Dev user-switcher (added in spec 042 Step 9) remains gated `import.meta.env.DEV`. Production build excludes it. Local development still allows persona switching via the UI affordance.

### 11.2 Spec 031 (Action Queue API) — backend Caller source changes

`get_caller()` reads from cookie+JWT instead of `X-User-*` headers. Caller shape unchanged.

`X-User-*` header convention removed Phase 1B (pulse-api Week 4 deploy is the natural cutover). Watched concern #29 (dev JWT injector) was retired earlier; this spec retires the dev header convention itself.

### 11.3 Pulse-api Week 4 deploy — natural pairing

Spec 043 and pulse-api deploy land in the same Week 4 window. Pulse-api deploy enables:
- Real signal extraction → real Action Queue cards (replaces DEMO_ACTIONS fixture)
- Real Caller-from-JWT on protected endpoints
- Real audit log Postgres table writes

Operator coordination: ratify pulse-api environment config (Postgres URL, JWT secret) at spec 043 audit time so deploy steps don't block.

### 11.4 Settings panel (spec 042 §9 / Step 7) — no changes

`/settings/users` continues to show user list. Audit log surfaces separately at `/admin/audit`. The two surfaces are conceptually distinct (user management vs admin observability) and live on separate routes.

---

## 12. Implementation sequence

Estimated 7 steps. Total ~5-6h Claude Code.

| Step | Description | Effort | Order constraint |
|---|---|---|---|
| 1 | Backend OAuth foundation: env config, JWT secret, Google client config, token mint/verify helpers, audit log table migration | ~45 min | First (foundation) |
| 2 | Backend OAuth endpoints: `/api/auth/google`, callback, `/api/auth/me`, refresh, logout, error code taxonomy | ~75 min | After Step 1 |
| 3 | Audit log write path on all auth terminal points + admin audit GET endpoint | ~30 min | After Step 2 |
| 4 | Front-end login page (`/login`) + error banner + "Sign in with Google" CTA | ~30 min | Can parallel with Step 5 |
| 5 | Front-end AuthContext refactor: `/api/auth/me` on mount + auto-refresh wrapper + logout dropdown | ~60 min | After Step 2 backend ready |
| 6 | Admin audit viewer (`/admin/audit`): route + table + expandable rows + row coloring | ~45 min | After Step 3 backend ready |
| 7 | Backend scope 403 normalization (watched concern #37) + DoD verification + spec 043 close | ~30 min | Last |

**Total: ~5-5.5h Claude Code. PM drafting per step prompt: ~10 min × 7 = ~70 min.**

**Step 1 dependencies (A2 disposition — added to `pyproject.toml`; codebase currently has neither):**
- `pyjwt[crypto]` — JWT mint + verify; HS256 signing per §10.1
- `google-auth` — Google ID token verification (signature, issuer, audience)

(`httpx>=0.27` already present — used for the Google `/token` code exchange; no new dep needed there.) Both added libraries are lightweight, well-maintained, and broadly used. No alternative library is justified by current codebase patterns. Step 1's ~45 min estimate is revised to **~60 min** to absorb dependency selection + Google JWKS verification wiring + the `0009` migration.

Operator coordination: deployment env vars must be ratified at audit time (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, PULSE_JWT_SECRET, PULSE_COOKIE_INSECURE_DEV). Real Google Workspace OAuth client must be configured at Google Cloud console before Step 2 — operator action item.

---

## 13. DoD criteria

When spec 043 closes, the following must be true:

1. ✓ Google Workspace OAuth client configured for `onedge.co` + `edgeonline.co`
2. ✓ Backend OAuth flow end-to-end: initiate, callback, token mint, cookie set
3. ✓ Front-end `/login` page with error banner + Sign in with Google CTA
4. ✓ AuthContext hydrates from `/api/auth/me`; falls back to `/login` on no session
5. ✓ Token refresh works transparently on access-token expiry
6. ✓ Logout clears both cookies; redirects to `/login`
7. ✓ Domain allowlist enforced (`onedge.co`, `edgeonline.co`)
8. ✓ Allowlist-only provisioning (must be in DEMO_USERS by email)
9. ✓ Structured error codes returned at all auth failure points (10 codes per §5.1)
10. ✓ Auth audit log table created + migrations applied
11. ✓ Every login attempt writes to audit (success + 6+ failure types per §8.3)
12. ✓ `/admin/audit` route accessible to admin only
13. ✓ Audit viewer shows reverse-chronological last 100 events, expandable rows
14. ✓ Dev user-switcher continues working in local dev (`import.meta.env.DEV`)
15. ✓ Production build excludes dev user-switcher
16. ✓ Existing scope 403s normalized to structured detail format (closes #37)
17. ✓ Watched concerns #29 (retired), #30, #40 all closed
18. ✓ Spec 042 AuthContext interface preserved (no breaking change)
19. ✓ Spec 031 `Caller` model preserved (no breaking change)
20. ✓ All cross-spec tests continue to pass (no regressions in spec 042 525 test count baseline)
21. ✓ New tests landed (~25-32 estimated; see §14)
22. ✓ Build green (front + back)
23. ✓ All commits tagged `[SPEC-043]`
24. ✓ Branch discipline: all on operator-designated branch
25. ✓ Spec doc closure section appended

---

## 14. Estimated test count (clarified per audit A4)

The default `pytest` run excludes `db` + `integration` markers (`addopts = "-m 'not integration and not db'"`); the 525 baseline = 241 front-end + 284 default-run backend. Tests that touch Postgres (audit-log write/read, callback-success persistence) must carry the `db` marker — they run only when Postgres is reachable (CI / local), NOT in the default suite. Google `/token` + JWKS verification is stubbed (httpx mock / monkeypatched verifier) so the DB-free path stays default-runnable, mirroring `test_rbac_executive.py`.

**Default-run tests (no DB; mock Google token verification):**
- Front-end Vitest: ~12-15 (Login page + error banner per code, AuthContext mount, auto-refresh on 401, logout, audit viewer render + expand, dev switcher gating, integration)
- Backend default pytest: ~6-8 (OAuth initiate/state nonce, callback success + failures [domain/provision/state/token], `/api/auth/me` success + 401, refresh logic, logout, structured 401/403 shapes)

Subtotal default-run new tests: **~18-22**

**`db`-marked tests (CI with Postgres):**
- Audit log write paths: ~3-4
- Admin `/api/auth/audit` endpoint (read + admin-only): ~2-3
- Cross-cutting integration: ~2-3

Subtotal `db`-marked new tests: **~7-10**

**Total new tests: ~25-32.** Spec 042 baseline 525 (default-run); spec 043 expected close at **~543-547 default-run** + the `db`-marked subtotal exercised under Postgres CI. The "~550-557" combined figure spans default + db runs.

---

## 15. Watched concerns

### 15.1 Closing with this spec

- **#29 (retired)** — Dev JWT injector — retired at spec 042 audit; this spec retires the dev `X-User-*` header convention as well
- **#30** — Multi-domain SSO (`onedge.co` + `edgeonline.co`) — single Google Workspace OAuth client covers both
- **#37** — Backend 403 detail format normalization — Step 7 normalizes existing scope 403s
- **#40 (NEW Session 19 late-late stream extended further)** — Auth observability — full structured error + audit log + admin viewer per Hybrid disposition

### 15.2 Carrying forward to Phase 2 (NOT in this spec)

- **(NEW)** Auth observability extensions: real-time updates, filter/search, alerting, replay, export, retention policy. Filed for Phase 2.
- **(NEW)** Auto-provisioning flow on Settings panel. When EDGE onboards new RMs post-demo, admin should add users via UI without code change. Filed for Phase 2.
- **(NEW)** Logout audit log entry. Phase 1A doesn't log logouts (not load-bearing for debugging); Phase 2 may add for completeness.
- **(NEW)** Multi-provider OAuth (Microsoft Entra) if needed. Filed for Phase 2 based on operator-stated Phase 1A scope (Google Workspace only).

### 15.3 Other concerns (unrelated, preserved)

- #15, #16, #17, #23, #24, #25, #28, #36, #38, #39 — all preserved per spec 042 close-out

---

## 16. Closure criteria

Spec 043 closes when:
1. All 25 DoD criteria met
2. All 25-32 new tests green
3. No regressions in spec 042 baseline (525)
4. Operator has performed at least one successful login end-to-end via real Google Workspace OAuth
5. Operator has triggered at least one failure case (e.g., wrong-domain email) and confirmed audit log captures it correctly
6. Admin user has navigated to `/admin/audit` and confirmed visibility
7. Spec doc closure section appended with date + DoD verification + carry-forward + cross-spec coordination notes

---

## 17. Risks + mitigations

### 17.1 Google Workspace config delays

**Risk:** Google Cloud console OAuth setup requires operator action; if delayed, blocks Step 2+ implementation.

**Mitigation:** Operator action item at audit time — provision OAuth client BEFORE Step 1 starts. If unavailable in time, Step 1 can use mock token verification (env override) until real client lands.

**Dependency note (A2, informational — no risk surfaced):** Step 1 adds `pyjwt[crypto]` + `google-auth` to `pyproject.toml`. Both are stable, widely-adopted libraries; the addition is routine and carries no integration risk for the current stack.

### 17.2 Cookie + CORS in production — OPERATOR DECISION REQUIRED PRE-STEP-5

**Risk:** SameSite=Lax cookies behave differently across deployment topologies:
1. **Single-domain deployment** (frontend + backend behind same domain via reverse proxy, e.g. `pulse.onedge.co/` serves both `/app/*` and `/api/*`) — Lax cookies work cleanly; minimal CORS config needed
2. **Split-domain deployment** (e.g. `app.onedge.co` + `api.onedge.co`) — requires explicit CORS allowlist + careful SameSite handling; some browsers reject SameSite=Lax cross-origin in this configuration

**Operator action item BEFORE Step 5 implementation begins:** ratify deployment topology. PM recommendation: single-domain via reverse proxy (simpler operationally; lower risk for cookie/CORS).

**Vite dev environment:** Step 1 implementation must configure the Vite proxy (`vite.config.ts`) to forward `/api/*` to the backend, allowing `Set-Cookie` to propagate to `localhost:5173` without dev-specific cookie attributes. (The dev proxy must preserve `Set-Cookie` on the OAuth callback 302 — verify during Step 1.)

If the operator hasn't ratified topology by Step 5 readiness, Claude Code HALTs for PM disposition.

### 17.3 JWT secret rotation

**Risk:** Phase 1A uses a single JWT secret. If secret leaks, all existing tokens are forgeable.

**Mitigation:** Phase 1A acceptable risk (small attack surface, fixed user set). Phase 2 implements key-rotation pattern (multiple keys with kid claim).

### 17.4 Audit log unbounded growth

**Risk:** Table grows without bound; Phase 1A doesn't retention-policy.

**Mitigation:** Phase 1A expected volume <1000 rows. Phase 2 adds retention. Index on `ts DESC` keeps queries fast.

### 17.5 Demo-day failure mode

**Risk:** OAuth flow fails during demo; investor sees blank screen.

**Mitigation:** This is exactly what spec 043 is designed to prevent. Structured errors + audit log + visible error banner ensures any failure is debuggable in seconds. Operator can pull up `/admin/audit` on a second device during demo if anything looks off.

### 17.6 Multi-domain OAuth consent screen warnings

**Risk:** Google Workspace may surface domain-verification warnings for `edgeonline.co` if not properly verified.

**Mitigation:** Operator pre-flight task: verify both domains in Google Cloud console before Step 1 starts.

---

## 18. Open questions (resolved before audit)

All resolved at draft time per Session 19 late-late stream extended further operator dispositions:

1. ✓ OAuth provider: Google Workspace only (Q1 ratified)
2. ✓ Provisioning model: Allowlist-only Phase 1A (Q2 ratified)
3. ✓ Audit viewer location: AdminLayout sub-route (Q3 ratified)
4. ✓ Production-grade scope: Hybrid (structured errors + audit log + minimal viewer; alerting/replay/etc Phase 2)
5. ✓ Multi-domain config: single OAuth client covers both domains
6. ✓ Email canonicalization: lowercase normalization, `{first}.{last}@` convention for non-Iffi users
7. ✓ Audit log retention: unbounded Phase 1A; Phase 2 carryforward

---

## 19. Notes for pre-spec audit

Suggested audit focus areas:
- **§3 architecture** — verify the OAuth flow + cookie pattern is right for this deployment context
- **§4 multi-domain config** — verify Google Workspace setup handles `edgeonline.co` cleanly under single client
- **§5 error code taxonomy** — verify codes are comprehensive (every realistic failure path has a code)
- **§7 backend** — verify Caller model compatibility (no breaking changes to spec 031 / 042)
- **§8 audit schema** — verify Postgres schema choices (indexes, JSONB for diagnostics)
- **§9 admin viewer** — verify route + component approach matches AdminLayout patterns
- **§11 cross-spec** — verify spec 042 AuthContext refactor doesn't break existing tests
- **§12 implementation sequence** — verify step ordering + effort estimates

Audit should produce: 0-2 HALTs maximum, with most findings as advisories or informational. If audit produces 3+ HALTs, spec needs revision before implementation.

---

*End of spec 043 draft. Awaiting PM/operator ratification → pre-spec audit → revision → implementation.*

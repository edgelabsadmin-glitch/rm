# ADR-006 — Authentication via Supabase Auth

**Status:** Accepted (amended to v1.1)
**Version:** 1.1 (Session 19 late-late stream extended further v3 — amends v1.0 to clarify asymmetric JWT signing per audit v3 Hv3-1)
**Date:** 2026-05-22 (v1.0 authored; v1.1 amended same day after pre-spec audit v3 surfaced JWT algorithm contradiction)
**Authored by:** PM (with operator ratification of underlying decision + operator verification of asymmetric signing keys in Supabase Project Settings)
**Supersedes:** None
**Superseded by:** None
**Related:** ADR-001 (Activepieces for cron orchestration), ADR-003 (Langfuse for observability), Spec 042 (RBAC 4-role model — CLOSED), Spec 043 v3.2 (OAuth implementation honoring this ADR)

**v1.1 amendments vs v1.0:**
- JWT signing algorithm clarified: **asymmetric RS256 or ES256**, per Supabase docs OAuth best-practice recommendation and operator verification of live Supabase Project Settings → JWT Signing Keys
- §Decision text updated to consistently describe asymmetric verification via JWKS public keys
- §Verification points updated to reflect asymmetric path
- §Negative consequences updated: JWKS public-key fetch retained; symmetric shared-secret concerns removed
- Removed obsolete cross-reference to a non-existent migration ADR

---

## Context

EDGE Pulse needs production-grade Google Workspace OAuth authentication for the demo on 2026-06-30 and beyond. The audience is EDGE's internal RM team plus the CEO (Iffi Wahla on `edgeonline.co`) plus other internal users on `onedge.co` — multi-domain SSO requirement. Spec 042 RBAC (CLOSED) established the 4-role model (Admin, Manager, RM, Executive) backed by DEMO_USERS allowlist + Caller object. Spec 043 implements the OAuth flow that hydrates that Caller object.

### What we need

- Google Workspace OAuth 2.0 flow (authorization code + PKCE)
- JWT-based session tokens with refresh
- Session cookie management (httponly, secure, samesite=lax)
- Multi-domain email allowlist (`onedge.co`, `edgeonline.co`)
- Audit log of authentication events — addresses watched concern #40
- Backend dependency that validates incoming requests and populates Caller object per spec 042 RBAC
- Preserves spec 042 service-to-service auth (`PULSE_INTERNAL_API_TOKEN` for Activepieces crons + dispatch + kill-switch)

### What we have

Reconnaissance commit `acc6ed1` verified:
- No authentication code exists in codebase. Spec 043 builds from scratch.
- Supabase Postgres already provisioned at `uckyovidaajhqkcuxaiz.supabase.co` (AWS Singapore)
- Supabase Auth is included in the same Supabase project
- Google Cloud OAuth client `pulse-web-client` provisioned in PULSE project under `onedge.co` org
- Internal user type OAuth consent screen — no Google verification required for `onedge.co` domain users; `edgeonline.co` works via Google org trust relationship

**Verified by operator Session 19 late-late stream extended further v3:** Supabase Project Settings → JWT Signing Keys shows asymmetric signing keys live (ES256 active; legacy symmetric keys retired). This is the foundation for the JWKS-based verification path documented in §Decision.

### Constraints

- **Demo timeline:** 5 weeks 1 day from ADR authoring date
- **Operator security posture:** high (operator rotated 6 secrets immediately upon PM flagging chat-paste incident)
- **AWS migration intent (post-demo):** Operator stated direction without specifics; deferred to post-demo (Watched Concern #43; Path C disposition)
- **No IT admin access for domain-wide delegation:** per-user OAuth model only

---

## Decision

**Authentication is delegated to Supabase Auth** with **asymmetric JWT signing (RS256 or ES256)** verified locally via Supabase JWKS endpoint. Google OAuth is the only configured identity provider for Phase 1.

### Supabase Auth handles

- Google OAuth 2.0 flow (authorization code + PKCE) end-to-end
- JWT minting + signing with **asymmetric algorithm (RS256 or ES256)** — private key managed internally by Supabase; never exposed
- Public keys published at JWKS endpoint `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` for backend verification
- Refresh token issuance + rotation (90-day default)
- Session cookie management (httponly, secure, samesite=lax)
- `auth.users` table (Supabase managed schema)
- `auth.audit_log_entries` table (auto-populated on login, logout, refresh, password change — addresses watched concern #40 at near-zero implementation cost)
- Email domain allowlist (configurable in Supabase Auth dashboard for tiers exposing this; backend DEMO_USERS check is authoritative regardless)

### Pulse application code handles

- **Frontend:** Supabase Auth client (`@supabase/supabase-js`) integration in React; `/login` page; `/auth/callback` redirect handler; AuthContext refactored to async loading state; logout flow
- **Backend:** FastAPI dependency `require_caller` (in `api/actions.py`) validates incoming Supabase JWTs:
  - Fetches JWKS public keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` at backend startup; caches in-process
  - Uses pyjwt (`pyjwt[crypto]>=2.8.0`) with `PyJWKClient` to look up correct signing key by `kid` claim
  - Validates JWT: signature (asymmetric verification with public key), expiry, audience (`"authenticated"`)
  - **Algorithm allowlist `["RS256", "ES256"]`** — explicitly rejects symmetric algorithms to prevent algorithm-substitution attacks
  - Refreshes JWKS cache on unknown `kid` (handles Supabase key rotation)
  - Extracts email from JWT claims; looks up DEMO_USERS allowlist (from spec 042); populates Caller object per spec 042 shape
- **Backend:** Admin-only `/admin/audit` viewer queries `auth.audit_log_entries` via Supabase service-role client
- **403 response format normalization** across all guards (addresses watched concern #37)

### Service-to-service auth preservation

`PULSE_INTERNAL_API_TOKEN` (used by Activepieces crons calling `/dispatch/*` and `/admin/kill-switch`) is **preserved unchanged**. User OAuth and service-to-service auth coexist.

---

## Alternatives considered

### Alternative A — Hand-rolled OAuth + custom symmetric JWT (PM's initial spec 043 v1/v2 draft)

PM initially drafted spec 043 v1 and v2 as a hand-rolled FastAPI OAuth flow: custom `/auth/google` endpoint, `pyjwt` library for self-minted symmetric JWTs, custom cookie handling, custom session table migration, custom refresh logic, custom audit log table.

**Rejected because:**
- ~5-6 hours implementation vs ~3 hours for Supabase Auth integration — meaningful in demo timeline
- Custom JWT signing introduces a new secret requiring rotation management — operator security posture argues for fewer secrets
- Custom audit log requires migration + write logic on every auth event — Supabase Auth provides this free
- Custom multi-domain allowlist requires backend filtering logic — Supabase Auth dashboard provides this free
- Refresh token rotation logic is non-trivial — Supabase Auth ships this with battle-tested implementation
- Pre-spec audit v1 on the hand-rolled v2 draft surfaced 2 HALTs + 7 advisories — audit cost itself signaled architectural overcomplexity

### Alternative B — Auth0 / Clerk / WorkOS

**Rejected because:**
- Adds new vendor + billing + secret management surface
- Supabase Auth already provisioned (zero net-new vendor work)
- No feature need that Auth0/Clerk offers but Supabase Auth lacks
- Future AWS migration (Watched Concern #43) simpler with one vendor (Supabase or AWS) than two (Auth0 + Supabase)

### Alternative C — Google OAuth direct, no JWT/session layer

**Rejected because:**
- ID tokens expire in 1 hour; refresh requires Google SDK re-prompt — bad UX
- No server-side session model; every request needs Google ID token validation
- No clean path for non-Google auth providers Phase 2+
- No audit log surface

### Alternative D — AWS Cognito (for AWS migration parity)

**Rejected because:**
- Watched Concern #43 (AWS migration scope) explicitly deferred to post-demo
- AWS Cognito requires AWS account + IAM setup + Cognito user pool provisioning — operator has not provisioned AWS infrastructure yet
- Most likely AWS migration outcome is Option A: backend moves to AWS, Supabase services stay managed — under Option A, Supabase Auth survives migration unchanged
- If AWS migration goes Option B (full Supabase replacement), auth layer rebuild is ~3-5 days post-demo — bounded; demo timeline wins

### Alternative E (v1.1 added) — Supabase Auth with symmetric (shared-secret) signing

PM's spec 043 v3 + v3.1 inadvertently described this path by combining "symmetric signing" with "JWKS verification." This combination is technically impossible (symmetric uses a shared secret; JWKS publishes public keys for asymmetric algorithms only). Audit v3 surfaced the contradiction as Hv3-1.

**Rejected because:**
- Supabase docs explicitly recommend asymmetric (RS256/ES256) for OAuth use cases
- Symmetric verification requires sharing the secret with Pulse backend; defeats purpose of separating signing authority
- Algorithm-substitution attacks are easier to mitigate against asymmetric-only allowlists
- Operator's Supabase project is already on asymmetric keys (verified Session 19 late-late stream extended further v3); symmetric path would require dashboard downgrade

---

## Consequences

### Positive

- ~3 hour implementation cost (vs 5-6 hour hand-rolled) — protects demo timeline margin
- Audit log surface free (closes Watched Concern #40)
- Multi-domain SSO via authoritative backend DEMO_USERS check (closes Watched Concern #30)
- Refresh + cookie management battle-tested by Supabase
- **Asymmetric signing**: Pulse backend never holds the JWT signing key — only the public key from JWKS — meaning even total Pulse compromise cannot forge new tokens
- No JWT signing secret env var needed; one fewer secret to manage and rotate
- AWS migration Option A (most likely) requires zero auth-layer rework

### Negative

- Couples Pulse auth to Supabase availability. Supabase Auth has 99.9%+ SLA; degraded path falls back to dev-bypass env var (`PULSE_AUTH_DEV_BYPASS=true` enables spec 042 X-User-* header behavior for emergency operations)
- Couples Pulse auth to Supabase pricing tier. ~14 users in DEMO_USERS scope; far below free tier
- AWS migration Option B (full Supabase replacement) requires ~3-5 days auth-layer rebuild post-demo. Acceptable; bounded
- JWKS public-key fetch on backend cold start adds ~100ms one-time latency. Mitigation: cache JWKS in-process; refresh on signature mismatch with unknown `kid`
- Asymmetric signature verification is computationally heavier than symmetric HMAC. Negligible at Pulse scale (~14 users; low req/s)

### Neutral

- Existing service-to-service auth (`PULSE_INTERNAL_API_TOKEN`) preserved
- Existing spec 042 Caller object shape preserved
- Frontend dev user-switcher preserved for dev workflows; gated to non-Supabase-session contexts

---

## Implementation

See spec 043 v3.2 (`02_planning/specs/043-oauth.md`) for the implementation plan. Spec 043 v3.2 honors this ADR.

If a future implementation needs to deviate from this ADR (e.g., to add a second OAuth provider, or to switch to a different auth service), the deviation MUST be documented as either an ADR amendment or a new superseding ADR. Silent drift from this ADR is not acceptable (PM_CONTEXT §4.26 + §6 rule 48 + §7 rule 39 codified Session 19 late-late stream extended further v3; Watched Concern #42 tracks process formalization).

---

## Verification at implementation time

When spec 043 v3.2 is implemented, the following will verify this ADR is honored:

1. No `jwt.encode()` calls anywhere in `03_build/api/` (Supabase mints JWTs, not Pulse)
2. **No JWT signing secret env var read by backend code** (asymmetric verification uses JWKS public keys only)
3. **No symmetric-algorithm references in production code paths** — `jwt_verify.py` algorithm allowlist is `["RS256", "ES256"]` explicitly; rejects symmetric algorithms
4. `jwt_verify.py` uses `PyJWKClient` (or equivalent) to fetch public keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
5. No custom session table migration (Supabase manages `auth.users`)
6. No custom audit log migration (Supabase manages `auth.audit_log_entries`)
7. `@supabase/supabase-js` listed in `03_build/front/package.json`
8. `supabase` Python client listed in `03_build/pyproject.toml`
9. `pyjwt[crypto]` listed in `03_build/pyproject.toml` (asymmetric algorithm support required for RS256/ES256)
10. `PULSE_INTERNAL_API_TOKEN` paths in `api/dispatch.py` + `api/admin/kill_switch.py` unchanged (service-to-service preservation)

---

## Why this ADR was authored retroactively and amended

**v1.0 authoring:** Pre-spec audit v2 of spec 043 v3 surfaced that the OAuth-via-Supabase-Auth architectural decision had been cited extensively in PM_CONTEXT, reconnaissance memo `acc6ed1`, Design 09, and spec 043 v3 framing — but the actual ADR file did not exist in `02_planning/architecture_decisions/` (only ADR-001/002/003 present). The decision content was real (operator-ratified); the document was missing. v1.0 authoring closed audit v2 HALT H2.

**v1.1 amendment:** Pre-spec audit v3 of spec 043 v3.1 (which honored v1.0 ADR-006) surfaced that v1.0 + spec 043 v3.1 had inadvertently combined symmetric-algorithm naming with "JWKS public-key verification." These are mutually exclusive: symmetric verification uses a shared secret (no JWKS); JWKS publishes public keys for asymmetric algorithms (RS256/ES256) only. Operator verified live Supabase Project Settings → JWT Signing Keys shows asymmetric keys active; PM amended this ADR to v1.1 and spec 043 to v3.2 to consistently describe asymmetric verification. v1.1 amendment closes audit v3 HALT Hv3-1.

PM_CONTEXT memory patterns filed Session 19 late-late stream extended further v3:
- `pm_must_verify_adr_files_exist_as_actual_documents_before_citing_them_recon_memo_citation_is_not_evidence_of_adr_existence` (drift #9)
- `pm_must_verify_jwt_signing_algorithm_matches_verification_method_shared_secret_means_symmetric_jwks_means_asymmetric_keys_pyjwt_crypto_extras_imply_asymmetric_dont_mix_models_in_specs_check_supabase_docs_at_spec_draft_time_for_authoritative_algorithm_choice` (drift #10)

---

*End of ADR-006 v1.1.*
# Spec 043 — OAuth (Google Workspace) + Supabase Auth + auth chokepoint

**Maps to:** §14 Infrastructure; Design 09 ADR-006.
**Depends on:** specs 001, 042.
**Effort:** 0.75 day.

## Description

Per Design 09 ADR-006: Google Workspace OAuth via Supabase Auth as the primary identity provider. Single-tenant `@onedge.co` domain restriction. JWT verification middleware on FastAPI. Front-end auth hook + protected routes.

## Inputs

- Google OAuth client credentials.
- Supabase Auth configured for Google provider with `@onedge.co` domain restriction.

## Outputs

- `03_build/pulse/api/middleware/auth.py` — JWT verification middleware.
- `03_build/front/src/auth/` — login flow + auth state hook.
- Pre-configured Supabase Auth (admin task; documented in setup README).

## Definition of Done

- [ ] Login flow works: Google → consent → Supabase session → JWT.
- [ ] Non-`@onedge.co` users blocked at OAuth.
- [ ] JWT validated on every FastAPI request to non-public endpoints.
- [ ] Scope from spec 042 derived per-request from JWT claims.
- [ ] MFA delegated to Google (no app-level MFA in Phase 1).

## Tests

- **Unit:** JWT validation logic.
- **E2E:** Playwright Google login + redirect.
- **Negative:** non-domain email rejected.

## Signal definitions involved

None.

## Open questions

None.

## What this is NOT

- Not RBAC (spec 042).
- Not multi-factor auth at the Pulse layer.

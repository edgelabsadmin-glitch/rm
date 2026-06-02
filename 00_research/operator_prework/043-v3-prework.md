# Supabase Auth + Google Cloud — operator pre-work for spec 043 v3

**Purpose:** Step 0 pre-work for spec 043 v3 OAuth (Path A Supabase Auth). Six tasks; ~20 min total. **Can be worked in parallel with Claude Code on Steps 1-2 (no Supabase-dashboard dependency until Step 3); blocking by Step 4.**

**Project:** Supabase project `uckyovidaajhqkcuxaiz` (per DATABASE_URL).
**Google Cloud:** PULSE project, OAuth client `pulse-web-client`.

---

## ✅ COMPLETION STATUS — 2026-05-23

All operator pre-work complete. Spec 043 v3 Step 3 (frontend Login/AuthCallback) is unblocked.

| Task | Status | Notes |
|------|--------|-------|
| 1 — Enable Google OAuth provider | ✅ DONE | Enabled with correct `GOOGLE_OAUTH_CLIENT_ID` (`338112410567-neki8iq…apps.googleusercontent.com`) + `GOOGLE_OAUTH_CLIENT_SECRET` (`GOCSPX-…`). Initial attempt had the Supabase project name + a wrong secret pasted into the fields; corrected before saving. Skip-nonce OFF, allow-no-email OFF. |
| 2 — Site URL + Redirect URLs | ✅ DONE | Site URL = `http://localhost:5173`. Redirect allowlist = `http://localhost:5173/auth/callback` + `https://pulse-front.vercel.app/auth/callback`. |
| 3 — Email domain allowlist | ⏭️ SKIPPED | Not exposed on the free tier (no "Allowed email domains" field in dashboard). Domain restriction (`onedge.co`, `edgeonline.co`) enforced in backend `require_caller` per spec 043 Step 2 — PM-preferred path anyway. |
| 4 — Email template config | ⏭️ SKIPPED | OAuth-only flow; no email templates needed. |
| 5 — Google Cloud callback URI | ✅ DONE | Registered `https://uckyovidaajhqkcuxaiz.supabase.co/auth/v1/callback` on OAuth client `pulse-web-client` (PULSE project). Existing localhost / `pulse-api.fly.dev` URIs kept (old + new during transition). |
| 6 — Local `.env` vars | ✅ DONE | Added `VITE_SUPABASE_URL` (= `SUPABASE_URL`) and `VITE_SUPABASE_PUBLISHABLE_KEY` (= `SUPABASE_PUBLISHABLE_KEY`). Added `PULSE_INTERNAL_API_TOKEN` (was MISSING despite recon `acc6ed1` claim — generated a fresh local-only 43-char token; see deferred note for production). |

### Bonus finding — JWT signing algorithm (relevant to Step 1 JWKS verification)

Checked **Project Settings → JWT Keys → JWT Signing Keys**:

- **Current key: ECC (P-256) = ES256** (asymmetric) — signs all new tokens.
- **Previous key: Legacy HS256 (Shared Secret)** — retired, last rotated 17 days ago; only verifies pre-switch tokens, all long expired.

**Conclusion: project is on ASYMMETRIC keys (ES256).** Backend Step 1 should verify against the Supabase JWKS endpoint (public ES256 key). No HS256 migration needed.

### Deferred (do NOT do now)

- Deploy pulse-front to Vercel → then update Supabase **Site URL** to the production domain.
- At spec 043 **Step 9** (deploy time): set production `PULSE_INTERNAL_API_TOKEN` on `pulse-api` Fly app, and set `VITE_SUPABASE_*` in the Vercel dashboard (frontend uses Vercel env, not Fly). The local `PULSE_INTERNAL_API_TOKEN` is local-only; production must use its own value, and the Activepieces dispatch flow must send that same value in the `X-Internal-Token` header.
- After spec 043 v3 is CLOSED + verified: remove the old `pulse-api.fly.dev/auth/callback` URI from the Google Cloud OAuth client to clean up.

### Validation evidence

- `grep "VITE_SUPABASE" .env` → both keys present with values.
- `PULSE_INTERNAL_API_TOKEN` → single line, non-empty value.
- Supabase Google provider → "Google sign-in is enabled".
- Both redirect URLs visible in Supabase URL Configuration.
- Supabase callback URI visible in Google Cloud Authorized redirect URIs alongside prior URIs.

---

## Task 1 — Supabase: Enable Google OAuth provider (~5 min)

1. Open Supabase dashboard → project `uckyovidaajhqkcuxaiz`.
2. Left sidebar: **Authentication** → **Providers**.
3. Find **Google** in the provider list → click to expand.
4. Toggle **Enable Sign in with Google** → ON.
5. Paste into fields:
   - **Client ID (for OAuth):** value of your `GOOGLE_OAUTH_CLIENT_ID` env var (the `338112410567-neki8iq...` one)
   - **Client Secret (for OAuth):** value of your `GOOGLE_OAUTH_CLIENT_SECRET` env var (the `GOCSPX-…` secret from Google Cloud)
6. **Skip** "Authorized Client IDs" (that's for iOS/Android native apps; not needed for web).
7. Note the **Callback URL** shown at the top of the Google provider config:
   `https://uckyovidaajhqkcuxaiz.supabase.co/auth/v1/callback`
   — **copy this URL**, you'll paste it into Google Cloud in Task 5.
8. Click **Save**.

**Validation:** Page shows "Google sign-in is enabled" with green checkmark.

**Gotcha encountered:** the **Client IDs** field expects the Google OAuth client ID string (`338112410567-…apps.googleusercontent.com`), NOT the Supabase project name. The **Client Secret** field expects the `GOCSPX-…` value. Don't confuse the Supabase project (named `edgelabsadmin-glitch's Project`) with the OAuth client ID.

---

## Task 2 — Supabase: Configure Site URL + Redirect URLs (~3 min)

1. Same dashboard → **Authentication** → **URL Configuration**.
2. **Site URL:** enter `http://localhost:5173` for now (update to Vercel production URL after pulse-front Vercel deploy is live; not blocking).
3. **Redirect URLs (allow list):** click "Add URL" and add **both** of these (one at a time):
   - `http://localhost:5173/auth/callback`
   - `https://pulse-front.vercel.app/auth/callback`
4. Click **Save** after each addition.

**Validation:** Both URLs appear in the "Redirect URLs" list.

**Why both:** Supabase Auth only redirects to allowlisted URLs after Google OAuth. Local dev uses :5173; production uses Vercel. Both must be allowlisted.

---

## Task 3 — Supabase: Email domain allowlist for multi-domain SSO (~5 min)

Closure mechanism for watched concern #30 (multi-domain SSO).

1. Same dashboard → **Authentication** → **Sign In / Up** (or "Policies" depending on dashboard version).
2. Look for **Allowed email domains** or **Email allowlist**.
3. Add: `onedge.co`
4. Add: `edgeonline.co`
5. Save.

**Note:** If your Supabase plan/version doesn't expose email-domain allowlist in the dashboard UI, enforce in the backend `require_caller` (Step 2 of spec 043) by checking JWT email domain against `["onedge.co", "edgeonline.co"]`. PM lean: backend enforcement is more flexible; dashboard allowlist is belt-and-suspenders. Skip if not exposed; backend enforcement is sufficient.

**Outcome (2026-05-23):** field not exposed on free tier → SKIPPED, backend handles.

---

## Task 4 — Supabase: Email template configuration (~1 min)

OAuth-only flow; no email templates needed. **Skip.**

---

## Task 5 — Google Cloud: Add Supabase callback URL to OAuth client (~3 min)

**Most important task** — Google won't redirect to Supabase without it.

1. Open Google Cloud Console → project **PULSE** → **APIs & Services** → **Credentials**.
2. Find OAuth 2.0 Client ID **pulse-web-client** → click to edit.
3. Scroll to **Authorized redirect URIs**.
4. Click **+ ADD URI**.
5. Paste: `https://uckyovidaajhqkcuxaiz.supabase.co/auth/v1/callback`
6. **Keep your existing redirect URIs** (the localhost:5173 ones and any `pulse-api.fly.dev` ones registered earlier).
7. Click **SAVE** at the bottom.
8. Wait ~30 seconds for Google to propagate.

**Validation:** The Supabase callback URL appears in "Authorized redirect URIs" along with prior URIs.

**Why "keep existing":** during transition, both old (hand-rolled) and new (Supabase) redirect URIs registered. After spec 043 v3 CLOSED + verified, remove the `pulse-api.fly.dev/auth/callback` URI to clean up.

---

## Task 6 — Verify env vars locally (~3 min)

Required (already present):
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `DATABASE_URL`
- `PULSE_INTERNAL_API_TOKEN` — **was MISSING** despite recon `acc6ed1` claim; added 2026-05-23 (local-only generated token).

New ones added (for Vite frontend build):
- `VITE_SUPABASE_URL` — same value as `SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY` — same value as `SUPABASE_PUBLISHABLE_KEY`

**Validation:** `grep "VITE_SUPABASE" .env` shows both values.

**Production (deploy time):** set `PULSE_INTERNAL_API_TOKEN` via `fly secrets set … --app pulse-api`; set `VITE_SUPABASE_*` in the Vercel dashboard (frontend uses Vercel env). Defer until spec 043 Step 9 close.

---

## What you should NOT do yet

- Don't deploy pulse-front to Vercel if not already deployed.
- Don't remove the existing Google Cloud redirect URIs (keep old + new during transition).
- Don't change `pulse-api` Fly secrets yet (Step 9 close).
- Don't paste any secret values in chat.

---

*Operator pre-work for spec 043 v3 — completed 2026-05-23.*

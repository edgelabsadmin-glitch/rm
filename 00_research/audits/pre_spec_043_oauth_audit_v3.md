# Pre-spec audit v3 — Spec 043 v3.1 OAuth (Path A Supabase Auth, audit v2 fixes verified)

**Audited:** 2026-05-22
**Auditor:** Claude Code (read-only)
**Subject:** `02_planning/specs/043-oauth.md` (status line confirmed: **DRAFT v3.1**)
**Method:** Read-only codebase verification + ADR cross-reference + audit v2 fix verification (Category K)
**Reference:** Audit v2 at `00_research/audits/pre_spec_043_oauth_audit_v2.md` (`5f82914`; 2 HALTs + 4 advisories + 5 informationals)

---

## Executive summary

**Both audit v2 HALTs are RESOLVED:** H1 (spec was v2 hand-rolled) → the on-disk file is now v3.1 Supabase Auth (77 "supabase" mentions; hand-rolled markers appear only in explicit "removed/must-not-appear" context); H2 (ADR-006 missing) → `ADR-006-authentication.md` exists with `Status: Accepted`, full Decision/Alternatives(A-D)/Consequences. **All four audit v2 advisories (ADV-1..4) are correctly reflected in v3.1** (Category K: 7/7 PASS). Codebase is unchanged from `acc6ed1` (HALT condition #4 did not fire).

**Audit v3 surfaces 1 new HALT, 3 advisories, 6 informationals.** The single HALT (**Hv3-1**): the spec **and** ADR-006 describe Supabase JWTs as **HS256** (symmetric) yet specify **JWKS-endpoint public-key verification with key rotation** (asymmetric) — these are mutually exclusive for a given token, and §6's env list omits the `SUPABASE_JWT_SECRET` that HS256 verification would require. This is a Step-1 foundation defect (`jwt_verify.py` cannot be built correctly against a contradictory token model) and must be disambiguated before implementation. Everything else is implementable as drafted.

---

## Findings

### HALTs (architectural blockers)

**Hv3-1 — JWT verification model is internally contradictory (HS256 vs JWKS).** (Category F.2 / I.1; spec §1 L30, §2.1 L64, Step 1 L117/L120/L128, §10 L456; ADR-006 L50/L59/L127)
- **Evidence:** Spec §1 L30 — *"JWT minting + signing (HS256, key managed internally)"*. Step 1 L120 — *"fetches Supabase JWKS once at startup, caches public keys… JWKS refresh on signature mismatch (handles Supabase key rotation)"*. L117 adds **`pyjwt[crypto]`** — the `[crypto]` extra exists specifically for **asymmetric** RSA/EC verification. ADR-006 mirrors all three (L50 "HS256 by default", L59 "via Supabase JWKS endpoint", L127 "JWKS public-key fetch… refresh on signature mismatch").
- **Why it's a contradiction:** HS256 is a **symmetric** algorithm — tokens are verified with the **same shared secret** used to sign them (`SUPABASE_JWT_SECRET`); there is **no public key and no JWKS document** to fetch. A JWKS endpoint (`/auth/v1/.well-known/jwks.json`) publishes **public** keys for **asymmetric** algorithms (RS256/ES256/EdDSA). A token cannot be both. (Reality: Supabase legacy projects sign HS256 with the project JWT secret; newer projects use asymmetric signing keys + JWKS. The spec blends the two models.)
- **Concrete downstream defect:** §6 env list (L382-394) provides `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_PUBLISHABLE_KEY` but **no `SUPABASE_JWT_SECRET`**. An implementer following Step 1 would build a JWKS verifier (asymmetric) while the project may issue HS256 tokens — verification fails at runtime; or, if HS256 is intended, the required secret is unlisted.
- **Recommended disposition (PM picks one, coherently, before Step 1):**
  - **(A) Asymmetric path:** correct "HS256" → "RS256/ES256 via Supabase asymmetric signing keys" in spec §1 + ADR-006 §Decision; keep JWKS + `pyjwt[crypto]` + rotation + `PULSE_JWKS_CACHE_TTL_SEC`. (Matches Supabase's current default for new projects; no extra secret.) **PM lean candidate** — it preserves the most spec text.
  - **(B) Symmetric path:** keep "HS256"; drop JWKS/rotation language + `[crypto]` extra; verify with `SUPABASE_JWT_SECRET` (add to §6 + `.env.example` + ADR-006 consequences); revise `test_jwt_verify.py` cases (the "JWKS fetch/rotation" cases become "shared-secret verify" cases).
  - Either is viable; the spec must commit to one and align env vars + the Step-1 test list. Operator should confirm which signing mode the Supabase project (`uckyovidaajhqkcuxaiz`) actually issues.

### Advisories (PM-disposition before close)

**ADVv3-1 — Operator pre-work file is not in the repo.** (Category G.1; spec §7 L405, Step 0 L109, reference doc #6)
- **Evidence:** `find . -iname "*prework*"` → none; `00_research/operator_prework/` does not exist. Spec §7 says the operator "places this file from PM-delivered draft at session start," so absence is **expected** (operator action pending) — but Step 3 hard-blocks on Tasks 1/2/5/6 from that file. The spec mitigates by inlining a 6-task summary (§7 L407-413), so the audit is not blocked. Flag so the operator actually places it before Step 3.

**ADVv3-2 — `SUPABASE_JWT_SECRET` absent from §6 (couples to Hv3-1).** (Category G.2 / I.1; spec §6)
- If disposition (B) HS256 is chosen, this secret is mandatory and currently unlisted in §6 + `.env.example`. If (A) asymmetric, no action. Listed separately so it isn't lost when Hv3-1 is dispositioned.

**ADVv3-3 — Multi-domain (#30) has no *automated* test asserting both domains.** (Category C.2 / J.1; spec Step 9 L278-281, §8 L423)
- Step 9 integration tests assert DEMO_USERS-present vs not-present, but neither explicitly exercises an `edgeonline.co` JWT vs an `onedge.co` JWT; both-domain coverage lives only in the manual smoke (steps 1-2). Audit pointer #8 (spec L457) asks for both-domain JWT scenarios — recommend adding one automated case (e.g., Iffi `edgeonline.co` JWT → executive Caller) so #30 closure has a regression guard.

### Informationals (observations)

**INFOv3-1 — Codebase grounding all PASS at `acc6ed1` (unchanged since reconnaissance).** `git log acc6ed1..HEAD -- 03_build` → empty (only doc commits since). See Category B.
**INFOv3-2 — Most "coverage gap" candidates are delegated to Supabase, correctly.** Rate-limiting, CSRF, PKCE, refresh rotation, concurrent refresh are Supabase-Auth responsibilities (ADR-006 L48-52); spec does not test them because Pulse doesn't implement them. JWKS rotation *is* tested (`test_jwt_verify.py` case 6) — acceptable (subject to Hv3-1's resolution).
**INFOv3-3 — `auth.audit_log_entries` (Supabase-managed) unverifiable.** §2.4/Step 6 query a Supabase managed table; cannot confirm schema/availability without dashboard access. Flag for operator confirmation (also: confirm the tier exposes `auth.audit_log_entries` read access via service-role).
**INFOv3-4 — `.env.example` drift.** Root `.env` has `SUPABASE_PUBLISHABLE_KEY` (reconnaissance §2) but `.env.example` does not; Step 1 (L125) already mandates adding the `VITE_*` mirrors, so this self-heals at implementation. Minor.
**INFOv3-5 — Supabase region label.** ADR-006 L30 states "AWS Singapore region"; reconnaissance recorded only the project host (`uckyovidaajhqkcuxaiz.supabase.co`), not region. Unverifiable here; harmless.
**INFOv3-6 — `api/auth/dependencies.py` is conditional, not assumed.** Spec §5 L335 marks it CONDITIONAL (only if guards exceed ~50 LOC), correctly avoiding audit v2's INFO-5 (the non-existent `api/dependencies.py`); `require_caller` stays in `api/actions.py`. Good.

---

## Category-by-category findings

### Category A — ADR cross-reference
- **A.1 — PASS.** Spec cites `ADR-006-authentication.md` **by filename** 5× (L4, L22, L26, L450, plus §1 framing). Not a bare "ADR-006" prose label.
- **A.2 — PASS.** `ls 02_planning/architecture_decisions/` → `ADR-001`, `ADR-002`, `ADR-003`, **`ADR-006-authentication.md`** (12,206 bytes).
- **A.3 — PASS.** ADR-006 `Status: Accepted`; documents Decision (Supabase Auth + Google IdP), Alternatives A-D (hand-rolled / Auth0-Clerk / Google-direct / AWS-Cognito) with rejections, and Consequences (positive/negative/neutral).
- **A.4 — Other ADRs:** ADR-001 (agent topology), ADR-002 (workflow engine), ADR-003 (observability/Langfuse) — none govern auth; no conflict. (ADR-006 L8 also references "ADR-008 Phase-1 simplicity over Alembic" — note **no `ADR-008` file exists** in the dir; that's a stale cross-reference in ADR-006, INFORMATIONAL, not in scope of this spec's surface.)
- **A.5 — Decisions warranting ADR amendment:** the JWT signing-mode choice (Hv3-1) should be reflected in ADR-006 §Decision once dispositioned; `PULSE_AUTH_DEV_BYPASS` and the JWKS caching strategy are spec-level and adequately covered.

### Category B — Codebase grounding (re-run at current HEAD; unchanged since `acc6ed1`)
| Check | Result | Evidence |
|---|---|---|
| `api/main.py` mounts 4 routers | **PASS** | `grep -c include_router` → 4 |
| `vite.config.ts` port 5173 + `/api` proxy strip | **PASS** | port 5173 + rewrite (reconnaissance-confirmed; unchanged) |
| `/profiles` unguarded pre-impl | **PASS** | `grep -c Depends api/profiles.py` → 0 |
| psycopg3 | **PASS** | `psycopg[binary,pool]>=3.2` |
| `.env.example` has `GOOGLE_OAUTH_CLIENT_ID/SECRET` | **PASS** | lines 37-38 |
| 4 files use `X-User-Id`/`Role` | **PASS** | actions.py, front/lib/api.ts, test_rbac_executive.py, test_actions_api_db.py |
- **B.2 — PASS.** 042 CLOSED present; backend default-run = 284 collected (525 = 241 FE + 284 BE) — no execution, collection only.
- **B.3 — INFOv3-3** (Supabase managed table unverifiable).

### Category C — Test count + posture
- **C.1 — PASS.** §4 uses ranges + explicit "**±5 tests for implementation discovery**" (L325) and "~50 updated (range; verified at implementation)" (L323). ~61 new / target ~586. No hard numbers presented as gospel.
- **C.2 — INFOv3-2** (Supabase-delegated concerns) + **ADVv3-3** (no automated both-domain test).

### Category D — Service-to-service preservation
- **D.1 — PASS.** `grep require_internal_token api/` → dispatch.py:25/34; `PULSE_INTERNAL_API_TOKEN` → dispatch.py + kill_switch.py. Spec §1 L45, §3 Step 8 (L265-273), ADR-006 L63/L131 all assert preservation; no global middleware introduced (Step 6 adds a *prefixed* `/admin/audit` router only).
- **D.2 — PASS.** No dependency shadows the internal-token guards; Activepieces cron paths intact. Step 8 is verification-only.

### Category E — Frontend architecture
- **E.1 — PASS.** Spec references **12** useAuth consumers (L12/191/198/297/370); matches audit v2's verified count. Step 4 DoD (L198) re-verifies count at implementation.
- **E.2 — PASS (audit v2 ADV-1 fixed).** Spec L205 mandates `npm install @radix-ui/react-popover@^1.0.7` and explicitly states it is NOT transitive; §5 L364 lists it as an explicit install. `grep "@radix-ui/react-popover" front/package.json` → still absent pre-install (correct).
- **E.3 — PASS.** Tier-0 brand tokens exist (`front/src/styles/tokens.css`, brand `#4a0f70`); login-page reuse feasible.

### Category F — Backend architecture
- **F.1 — PASS (audit v2 INFO-5 fixed).** Spec Step 2 L135 references `api/actions.py` for `require_caller` and explicitly notes `api/dependencies.py` "does not exist." `ls api/dependencies.py` → absent (confirmed). `api/auth/dependencies.py` is CONDITIONAL (§5 L335).
- **F.2 — Hv3-1** (HS256/JWKS contradiction). JWKS caching (TTL via `PULSE_JWKS_CACHE_TTL_SEC`), refresh-on-mismatch, and cold-start fail-fast (`test_jwt_verify.py` case 2) ARE specified — but only coherent under the asymmetric disposition (A).
- **F.3 — PASS.** Step 6 L220 specifies the admin role check happens **BEFORE** the service-role query ("admin role check happens BEFORE service-role query to prevent privilege escalation"). Correct ordering.

### Category G — Operator pre-work completeness
- **G.1 — PARTIAL (ADVv3-1).** Spec §7 + Step 0 reference the pre-work file with an inline 6-task summary; the file itself is not yet in the repo (operator-placed). Redirect URIs (L409: `localhost:5173/auth/callback` + `pulse-front.vercel.app/auth/callback`; L412 Supabase callback into Google client), env vars (§6), and parallelization (Steps 1-2 ∥ pre-work; Step 3 gated) are all specified.
- **G.2 — Gaps:** no explicit Vercel production env-var list, no Fly `pulse-api` secrets enumeration (esp. `PULSE_AUTH_DEV_BYPASS=false` + `SUPABASE_SERVICE_ROLE_KEY`), and Supabase RLS on `auth.*` is not addressed (service-role bypasses RLS, so likely moot — note for operator). Fold into the pre-work file before Step 3.

### Category H — Rollback strategy
- **H.1 — PASS (with INFO).** §9 L439 specifies `fly secrets set --app pulse-api PULSE_AUTH_DEV_BYPASS=true` and asserts Fly auto-restarts on secret set (**true** for Fly Machines — secret changes trigger a restart; INFORMATIONAL — not independently verified here). AuthContext rollback is frontend-only (revert to spec 042 synchronous resolver); no backend coordination required beyond the env toggle.
- **H.2 — Gap noted.** §9 covers the dev-bypass and frontend revert. Step 6 missing-service-role behavior: `test_admin_audit_api.py` case 5 (L233) asserts "missing service role config returns 500" — so it's a **graceful 500, not a crash** (good). Recommend §9 cross-reference that case so the rollback story is explicit.

### Category I — Security posture
- **I.1 — PASS with Hv3-1 caveat.** JWT validation specifies signature + expiry + audience (Step 1 L120). `PULSE_AUTH_DEV_BYPASS`: spec **mandates** "MUST be `false` in Fly production secrets" (§6 L393, Step 2 L139) — a mandate, not just a default. Logout calls `supabase.auth.signOut()` (clears Supabase session) + redirects to `/login` (§3 Step 5, ADR-006). CSRF/PKCE delegated to Supabase (ADR-006 L49). The one open item is the signing-model contradiction (Hv3-1), which is a correctness, not posture, defect.
- **I.2 — PASS.** Multi-domain allowlist is **backend-authoritative** (§2.3 L77: `require_caller` DEMO_USERS lookup → 403 if absent); dashboard allowlist is explicitly "belt-and-suspenders / skippable" (Task 3). DEMO_USERS lookup is an allowlist by construction → no gap if the dashboard step is skipped.

### Category J — Watched-concern closure verification
- **#30 — PASS** (backend DEMO_USERS authoritative; ADVv3-3 = add an automated both-domain test).
- **#37 — PASS.** Step 7 normalizes all four sites (require_caller/actions.py, require_admin/kill_switch.py, require_internal_token/dispatch.py, executive-403/actions.py) to the discriminated-union format; frontend union has legacy-string fallback (§7 L255).
- **#40 — PASS** (Step 6 `/admin/audit` over `auth.audit_log_entries`; INFOv3-3 = managed table unverifiable).
- **#41 — PASS.** Step 2 L142 adds `dependencies=[Depends(require_caller)]` to the profiles router (covers **both** GET and PUT); `test_profiles_auth.py` (4 cases incl. PUT) in §5.

### Category K — Audit v2 fix verification (highest-priority)
| Fix | Result | Evidence |
|---|---|---|
| **K.1** spec is v3.1 Supabase (not v2 hand-rolled) | **PASS** | status line "DRAFT v3.1"; `grep -ic supabase` → 77 (>20); hand-rolled markers only at L397 ("no longer needed") + L459 ("verify no remnants") |
| **K.2** ADR-006 file exists | **PASS** | `02_planning/architecture_decisions/ADR-006-authentication.md` present, Accepted |
| **K.3** explicit radix popover install | **PASS** | L13/L205/L213/L364 mandate `npm install @radix-ui/react-popover@^1.0.7`; "NOT transitive" stated |
| **K.4** 12 useAuth consumers (not 8) | **PASS** | "12 useAuth consumers" at L12/191/198/297/370; no "8" in consumer-count context |
| **K.5** `/profiles` guard step + test | **PASS** | Step 2 L142 adds guard (GET+PUT); `tests/test_profiles_auth.py` in §5 L339 |
| **K.6** test counts use ranges + ±5 | **PASS** | §4 L323/L325 ranges + "±5 tests for implementation discovery" |
| **K.7** `require_caller` in `api/actions.py`, not `dependencies.py` | **PASS** | `grep -c "api/actions.py"` → 11; `"api/dependencies.py"` → 3 (all 3 are explicit "does not exist" callouts) |

---

## Verification summary table

| Category | Findings | Highest severity |
|---|---|---|
| A — ADR cross-reference | A.1-A.5 PASS (+ stale ADR-008 ref, INFO) | INFO |
| B — Codebase grounding | 6/6 PASS + B.2 PASS + INFOv3-3 | INFO |
| C — Test count + posture | C.1 PASS; ADVv3-3 | ADVISORY |
| D — Service-to-service | PASS | INFO |
| E — Frontend | E.1/E.2/E.3 PASS | INFO |
| F — Backend | F.1/F.3 PASS; **F.2 Hv3-1** | **HALT** |
| G — Operator pre-work | partial; ADVv3-1, ADVv3-2 | ADVISORY |
| H — Rollback | PASS + minor gap note | INFO |
| I — Security | PASS (Hv3-1 caveat) | INFO |
| J — Watched concerns | #30/#37/#40/#41 PASS | INFO |
| K — Audit v2 fix verification | **7/7 PASS** | NONE |

**Totals: 1 HALT (Hv3-1), 3 advisories (ADVv3-1..3), 6 informationals (INFOv3-1..6).**

---

## Audit v2 → v3 progress

| Audit v2 finding | v3.1 disposition | Status |
|---|---|---|
| H1 (spec on disk is v2 hand-rolled) | v3.1 Supabase Auth placed in repo | **PASS** |
| H2 (ADR-006 missing) | `ADR-006-authentication.md` authored (Accepted) | **PASS** |
| ADV-1 (radix popover not transitive) | Step 5 mandates explicit `@^1.0.7` install | **PASS** |
| ADV-2 (12 useAuth consumers not 8) | Step 4 references 12 | **PASS** |
| ADV-3 (/profiles step missing) | Step 2 adds guard (GET+PUT) + test | **PASS** |
| ADV-4 (test count mismatch) | §4 uses ranges + ±5 allowance | **PASS** |

---

## Audit limitations

Could **not** be verified (read-only method; no dashboard/Fly/Google/Supabase access; no execution):
- Whether the Supabase project (`uckyovidaajhqkcuxaiz`) issues **HS256 (legacy)** or **asymmetric (JWKS)** tokens — central to disposing Hv3-1. **Operator must confirm** in the Supabase dashboard (Project Settings → API → JWT keys).
- `auth.audit_log_entries` schema/availability + service-role read access on the tier (INFOv3-3).
- Fly secret-set auto-restart behavior (H.1) and current Fly `pulse-api` secret set.
- Google Cloud current Authorized-redirect-URI list + `edgeonline.co` domain verification.
- Supabase region (INFOv3-5) and free-tier MAU headroom.

---

## Recommended PM disposition sequence

1. **Dispose Hv3-1** — choose the JWT signing model: (A) asymmetric RS256/ES256 + JWKS (recommended; preserves most spec text; matches Supabase's current default) or (B) HS256 + `SUPABASE_JWT_SECRET`. Update spec §1/§6/Step-1 + ADR-006 §Decision + `test_jwt_verify.py` case list accordingly. **Confirm the project's actual signing mode in the Supabase dashboard first.**
2. **Dispose ADVv3-2** alongside Hv3-1 (add `SUPABASE_JWT_SECRET` to §6/`.env.example` only if path B).
3. **Dispose ADVv3-1** — operator places `00_research/operator_prework/spec-043-supabase-prework.md` before Step 3; fold in the G.2 gaps (Vercel/Fly env, RLS note).
4. **Dispose ADVv3-3** — add one automated both-domain (`edgeonline.co` + `onedge.co`) JWT test to Step 9.
5. Apply edits → spec 043 v3.2. **HALT count must reach 0** before Step 1 implementation begins.
6. Operator pre-work (Tasks 1/2/5/6) proceeds in parallel; Step 3 gates on operator confirmation.

Audit v2's HALTs are closed; v3 leaves a single, well-bounded HALT (the signing-model contradiction) plus minor advisories. Recommend a small v3.2 disposition pass rather than a full re-draft.

---

*End of audit memo v3.*

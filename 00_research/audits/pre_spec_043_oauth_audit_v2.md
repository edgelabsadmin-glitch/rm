# Pre-spec audit v2 — Spec 043 v3 OAuth (Path A Supabase Auth)

**Audited:** 2026-05-22
**Auditor:** Claude Code (read-only)
**Subject:** `02_planning/specs/043-oauth.md`
**Method:** Read-only codebase verification + ADR cross-reference + reconnaissance grounding (`acc6ed1`)
**Reference:** Audit v1 at `00_research/audits/pre_spec_043_oauth_audit.md` (caught H1 + H2 + 7 advisories; missed ADR-006)

---

## Executive summary

**2 HALTs, 4 advisories, 5 informationals.** The single most important finding (**H1**): the document at `02_planning/specs/043-oauth.md` is **NOT** the "v3 Path A Supabase Auth" spec this audit was commissioned to verify — it is the **v2 hand-rolled OAuth spec** (custom FastAPI `/api/auth/google` redirect flow, self-minted HS256 JWTs via `PULSE_JWT_SECRET`, custom cookie management, `pyjwt` + `google-auth` JWKS verification). It contains **zero** Supabase Auth content. **H2**: the **ADR-006 document this audit must cross-reference does not exist** — `02_planning/architecture_decisions/` holds only ADR-001/002/003. Both load-bearing premises of the audit-v2 prompt are therefore unmet by the codebase, which **materially changes audit scope** (an explicit HALT condition). Per protocol I completed the version-agnostic codebase grounding (all PASS — high value to PM regardless) and audited the categories assessable against the v2 spec that is actually on disk; Supabase-specific sub-checks are marked **N/A — spec content absent**. **No Step-1 implementation should proceed** until PM reconciles the v2/v3 spec state and the ADR situation.

---

## Findings

### HALTs (architectural blockers)

**H1 — Spec on disk is v2 hand-rolled OAuth, not the "v3 Path A Supabase Auth" this audit targets.** (Category A/B; spec §3, §10, §12; whole document)
- **Evidence:** `043-oauth.md:3` status reads *"Ratified … v2 …"*; §3.1 builds a custom `GET /api/auth/google` → Google → `/api/auth/google/callback` flow; §10.1 mints own HS256 tokens signed with `PULSE_JWT_SECRET`; §12 Step 1 adds `pyjwt[crypto]` + `google-auth`. `grep -niE "supabase|@supabase|signInWithOAuth|getSession|service-role|PULSE_AUTH_DEV_BYPASS|audit_log_entries"` over the spec → **no matches**. `git log` shows the last spec edit (`067e10d`) was the v2 disposition pass; no v3 commit exists.
- **Impact:** Every Supabase-specific item the prompt enumerates (`@supabase/supabase-js`, `auth.audit_log_entries` managed table, `AsyncAuthProvider` over Supabase session, `PULSE_AUTH_DEV_BYPASS`, JWKS-from-Supabase, service-role `/admin/audit`, Tasks 1-3 Supabase/Google config) **cannot be verified — the content does not exist in the spec.** Auditing the v3 design as drafted is impossible.
- **Disposition options:** (A) If a v3 Supabase rewrite was authored elsewhere, commit it to `043-oauth.md` and re-run this audit. (B) If the team intends to stay hand-rolled, retract the "v3 Path A" framing and treat the existing v1 audit (`b7b90b3`) as current. (C) If Path A is the new direction, PM rewrites the spec to v3 first; this audit then re-runs against real content. **Recommend A or C before any implementation.**

**H2 — ADR-006 does not exist as a document.** (Category A; prompt reference #2)
- **Evidence:** `ls 02_planning/architecture_decisions/` → only `ADR-001-agent-reasoning-topology.md`, `ADR-002-workflow-engine.md`, `ADR-003-observability-backend.md`. No `ADR-006*`. The "ADR-006" label appears only as prose inside `.env.example:36` (*"Auth (Design 09 ADR-006: Google Workspace OAuth via Supabase Auth)"*) and was carried into the reconnaissance memo §8 D4 as a citation of that comment — **not** a written ADR.
- **Impact:** The audit-v2 prompt's core remediation for the v1 miss-mode ("cross-reference ADR-006") **cannot be executed** — there is no ADR to honor, supersede, or contradict. §7 rule 39 ("audit must cross-reference the relevant ADR") is satisfiable only against ADR-001/002/003, none of which govern auth.
- **Disposition options:** (A) PM authors `ADR-006-authentication.md` capturing the Supabase-Auth-vs-hand-rolled decision (the natural home for the Path A choice), then this audit cross-references it. (B) Acknowledge the "ADR-006" reference is a stale Design-09 label and renumber/retire it. **Recommend A** — the auth approach is exactly the kind of decision an ADR should record, and its absence is what let the v1 audit miss the Supabase question.

### Advisories (PM-disposition before close)

**ADV-1 — `@radix-ui/react-popover` is NOT present (Step 5 logout-dropdown claim false).** (Category E.2; spec §6.3)
- **Evidence:** `grep "@radix-ui/react-popover" front/package.json` → 0; `ls front/node_modules/@radix-ui/` → no popover. The Header today has no dropdown/menu primitive at all (reconnaissance §6).
- **Impact:** The logout dropdown is net-new UI requiring an explicit dependency add (or a hand-rolled menu). Whichever spec version proceeds, the "already transitively present, verify or add" assumption is wrong — it must be added.

**ADV-2 — `useAuth()` consumer count is 12, not the 8 audit v1 recorded.** (Category E.1; spec §3.3/§11.1)
- **Evidence:** `grep -rln useAuth front/src` (excl. AuthContext + tests) → 12 files: `App.tsx`, `Constellation.tsx`, `QueueList.tsx`, `queue/hooks.ts`, `AccountListColumn.tsx`, `AccountWorkspace.tsx`, `ExecutiveView.tsx`, `PulseBarController.tsx`, `Header.tsx`, `lib/api.ts`, `RoleGuard.tsx`, `AdminLayout.tsx`. Spec 042 close-out (Steps 4-9) added the four newest.
- **Impact:** Any AuthProvider refactor (async hydration/loading boundary) must be validated against **12** consumers. The non-null-`user` contract (spec §3.3) keeps this safe in principle, but the spec's consumer-count baseline is stale; whoever implements should re-enumerate.

**ADV-3 — `/profiles` GET+PUT remain unguarded (#41 still open).** (Category B/J; reconnaissance D6)
- **Evidence:** `grep -c Depends api/profiles.py` → 0. No `require_caller` on `read_profile` or the PUT.
- **Impact:** The v2 spec does not address `/profiles` (it scopes #37 to actions/dispatch/kill_switch only — §7.3). The prompt's J.1 expects a "#41 closure: /profiles guard — Step 2," but **no such step exists in the on-disk spec**. Whatever version proceeds must add a `/profiles` guard explicitly or PM defers #41 on the record.

**ADV-4 — Test-count posture in the prompt (583 = 525 + 58) does not match the on-disk spec (~25-32 new → ~543-557).** (Category C.2; spec §14)
- **Evidence:** Spec §14 estimates **~25-32** new tests (≈543-557 combined). The prompt's "583 = 525 + 58" assumes a Supabase-flavored spec with ~58 new tests that the on-disk doc does not describe.
- **Impact:** Arithmetic can't be reconciled because the two specs describe different test surfaces. Re-baseline after the v2/v3 question (H1) is resolved.

### Informationals (observations)

**INFO-1 — Codebase grounding: ALL PASS (version-agnostic).** (Category B.1) See Category B table — 7/7 spec/reconnaissance claims verified true at `acc6ed1`.
**INFO-2 — Spec 042 is CLOSED; backend default-run baseline = 284 collected (525 = 241 FE + 284 BE).** (Category B.2) `grep -c CLOSED 042-rbac.md` → 4; `pytest --collect-only` → "284/332 tests collected (48 deselected)". No execution performed.
**INFO-3 — Service-to-service auth intact and version-agnostic-safe.** (Category D) `require_internal_token` (dispatch.py:25/34) + `kill_switch.py` both gate on `PULSE_INTERNAL_API_TOKEN`; the v2 spec touches neither dependency. Activepieces crons are unaffected by either spec version.
**INFO-4 — `auth.audit_log_entries` (Supabase-managed) cannot be verified.** (Category B.3) The on-disk spec instead defines `pulse.auth_audit_log` (§8.1, app-managed, migration `0009`). The prompt's `auth.*` Supabase-managed table is a v3 concept absent from the doc; even if present, Supabase schema state is unverifiable without dashboard access — flag for operator.
**INFO-5 — `require_caller` lives in `api/actions.py` (not a separate `api/dependencies.py`).** (Category F.1) The prompt's `grep "require_caller" api/dependencies.py` target does not exist; the dependency is module-local to `actions.py`. Any get_caller refactor lands there.

---

## Category-by-category findings

### Category A — ADR cross-reference
- **A.1 — FAIL/HALT (H2).** Spec §1 cites no ADR at all (it references watched concerns #29/#30/#37/#40, not an ADR). It does **not** cite ADR-006 — and ADR-006 doesn't exist.
- **A.2 — Existing ADRs that touch this surface:** ADR-001 (agent reasoning topology — N/A to auth), ADR-002 (workflow engine — N/A), ADR-003 (observability backend, Langfuse — tangential; auth audit log is a separate Postgres concern, no conflict). **No ADR governs authentication / JWT / session / OAuth / frontend routing.** The spec is silent on ADRs because none apply → records as **H2** (the missing ADR-006), not a per-ADR advisory.
- **A.3 — Decisions warranting an ADR:** the auth architecture choice itself (Supabase Auth vs hand-rolled), the JWT-secret/refresh model (§10), the dev-bypass posture, and multi-domain allowlist enforcement location all warrant an `ADR-006-authentication.md`. **Recommend PM author it (ties to H2).**

### Category B — Codebase grounding (all at `acc6ed1`)
| Check | Result | Evidence |
|---|---|---|
| `api/main.py` mounts exactly 4 routers | **PASS** | kill_switch, profiles, actions, dispatch (lines 47-50) |
| `vite.config.ts` pins port 5173 | **PASS** | `port: 5173` (line 16) |
| `vite.config.ts` proxies `/api` with strip | **PASS** | `proxy: { "/api": … rewrite → '' }` (reconnaissance-confirmed) |
| `/profiles` unguarded | **PASS (gap confirmed)** | `grep -c Depends api/profiles.py` → 0 |
| psycopg3 in pyproject | **PASS** | `psycopg[binary,pool]>=3.2` |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` in `.env.example` | **PASS** | lines 37-38 (note: `_OAUTH_` infix — not `GOOGLE_CLIENT_ID`) |
| Exactly 4 files use `X-User-Id`/`Role` | **PASS** | actions.py, front/lib/api.ts, test_rbac_executive.py, test_actions_api_db.py |
- **B.2 — PASS.** 042 CLOSED present; 284 backend default-run collected (525 baseline holds).
- **B.3 — INFO-4** (Supabase managed table unverifiable; on-disk spec uses `pulse.auth_audit_log`).

### Category C — Test count + posture
- **C.1 — DEVIATION.** On-disk §14 names front-end (Login/AuthContext/refresh/logout/audit-viewer/switcher) + backend (initiate/callback/me/refresh/logout/shapes) test groups — all **new** files (none exist; no `/login`, `/api/auth/*`, or audit viewer in codebase per reconnaissance §4). The "~30 existing tests updated" the prompt cites is **not** in the on-disk spec; the relevant figure is the **4 X-User-Id files** that would change when the header convention is removed.
- **C.2 — ADV-4** (583/58 ≠ on-disk 25-32).
- **C.3 — Coverage gaps (apply to either version):** no tests specified for rate-limiting (spec wires `rate_limited` code but defers logic to Phase 2 — acceptable), CSRF beyond OAuth state nonce on refresh/logout endpoints, JWKS rotation/refresh-on-mismatch, or concurrent-refresh races. Record as coverage gaps for whichever version proceeds.

### Category D — Service-to-service preservation
- **D.1 — PASS (INFO-3).** `require_internal_token` (dispatch.py) + kill_switch both read `PULSE_INTERNAL_API_TOKEN`. The on-disk spec changes only `get_caller()` (cookie/JWT) and adds `/api/auth/*`; it introduces no global middleware that would shadow these header/token guards.
- **D.2 — PASS.** No middleware in either the v2 spec or current `api/main.py` would reject Activepieces internal-token calls. (Note: `timeout.py` middleware exists and is auth-agnostic.)

### Category E — Frontend architecture
- **E.1 — ADV-2.** 12 `useAuth` consumers (not 8). Non-null-user contract (§3.3) protects them, but baseline is stale.
- **E.2 — ADV-1.** `@radix-ui/react-popover` absent (package.json + node_modules). Logout dropdown needs an explicit add.
- **E.3 — PASS.** Tier-0 tokens exist (`front/src/styles/tokens.css`, used across surfaces); login-page visual-language reuse is feasible. (Note: the on-disk spec §6.1 references the Pulse wordmark, not "Constellation visual language" as the prompt states — minor framing drift, not a finding.)

### Category F — Backend architecture
- **F.1 — INFO-5 + caution.** `require_caller`/`get_caller` live in `api/actions.py` (no `api/dependencies.py`). The v2 spec's cookie/JWT rewrite (§3.4) preserves the `Caller` shape and `require_queue_caller` ordering — compatible with spec 042 RBAC **as written**. Implementer must keep the rewrite in `actions.py` (or extract a shared module deliberately).
- **F.2 — ADVISORY-level gap (folds into C.3).** The on-disk spec mentions "Google JWKS verification wiring" (§12) but specifies **no** JWKS caching TTL, refresh-on-signature-mismatch, concurrent-refresh handling, or fail-fast-on-unreachable-JWKS behavior. Add to spec before Step 1 (whichever version).
- **F.3 — N/A (spec content absent).** No `/admin/audit` Supabase service-role client in the on-disk spec; §9.3 specifies an app-managed `GET /api/auth/audit` with a `caller.role == 'admin'` check described **before** the query (correct ordering as written). No service-role bypass risk in the v2 design.

### Category G — Operator pre-work completeness
- **G.1 — PARTIAL.** On-disk spec covers Google Cloud redirect URIs (§4.1: localhost:5173 + pulse.onedge.co, both `/api/auth/google/callback`) + env vars (§12: GOOGLE_CLIENT_ID/SECRET, PULSE_JWT_SECRET, PULSE_COOKIE_INSECURE_DEV). **Note conflict:** §12 names `GOOGLE_CLIENT_ID` but `.env.example` + reconnaissance say `GOOGLE_OAUTH_CLIENT_ID` — unresolved naming discrepancy (reconnaissance D3, still open).
- **G.2 — Missing pre-work:** no Vercel production env vars, no Fly `pulse-api` secrets list, no Supabase RLS policy notes (the latter only relevant if Path A/v3 is adopted). All Supabase dashboard pre-work (the prompt's Tasks 1-3) is **absent** because the spec is hand-rolled.

### Category H — Rollback strategy
- **H.1 / H.2 — N/A (spec content absent).** The on-disk v2 spec has **no §9 rollback section** and **no `PULSE_AUTH_DEV_BYPASS`** (grep → 0). Its rollback affordance is implicit: AuthProvider retains `initialUserId` (DEV/test synchronous path, §3.3) and the dev switcher stays DEV-gated. A real rollback section (Fly secret toggle behavior, missing-key graceful degradation) is **unwritten** — add it for whichever version proceeds.

### Category I — Security posture
- **I.1 — Partial PASS (v2 design).** JWT validation (signature + expiry + `aud`/`iss`) specified §3.4/§10.1; logout clears both cookies §10.4; OAuth `state` nonce CSRF defense §3.1/§5.1. **Gaps:** PKCE not mentioned (hand-rolled flow relies on state nonce only — Supabase Auth would handle PKCE, another argument for the v3 question); no `PULSE_AUTH_DEV_BYPASS` accidental-prod risk because the var doesn't exist.
- **I.2 — Allowlist by construction (PASS).** Backend enforces via `is_domain_allowed` (§4.3) then `DEMO_USERS` email lookup (§4.4) — the lookup is itself the allowlist; no dashboard dependency in the v2 design. Closes #30 backend-side regardless of any Supabase dashboard step.

### Category J — Watched-concern closure verification
- **#30 — PASS** (backend domain allowlist + DEMO_USERS lookup, §4.3/§4.4).
- **#37 — PARTIAL.** Step 7 normalizes actions/dispatch/kill_switch 403s (§7.3); discriminated-union front-end type added (§6.4). Covers the 403 sites enumerated in reconnaissance. **PASS for the named sites.**
- **#40 — PASS (as written).** `/api/auth/audit` + viewer surface ts/email/result/code/IP/user-agent/diagnostics (§9.2/§9.3).
- **#41 — NOT ADDRESSED (ADV-3).** No `/profiles` guard step in the on-disk spec; the prompt's "Step 2 closes #41" does not match the doc.

---

## Verification summary table

| Category | Findings | Highest severity |
|---|---|---|
| A — ADR cross-reference | 1 (H2) | **HALT** |
| B — Codebase grounding | 7 PASS + INFO-1/2/4 | INFO |
| C — Test count + posture | ADV-4 + C.3 gaps | ADVISORY |
| D — Service-to-service | INFO-3 (PASS) | INFO |
| E — Frontend | ADV-1, ADV-2 | ADVISORY |
| F — Backend | INFO-5 + F.2 gap | ADVISORY |
| G — Operator pre-work | partial + naming conflict | ADVISORY (folds to known D3) |
| H — Rollback | N/A (absent) | INFO |
| I — Security | partial PASS | INFO |
| J — Watched concerns | #30/#37/#40 ok; #41 open | ADVISORY (ADV-3) |
| (cross-cutting) | spec version mismatch | **HALT (H1)** |

**Totals: 2 HALTs (H1 spec-version, H2 missing ADR), 4 advisories (ADV-1..4), 5 informationals (INFO-1..5).**

---

## Audit limitations

Could **not** be verified (read-only method + absent content):
- Any Supabase Auth design — **not present in the spec** (H1). All Category-prompt items keyed to `@supabase/supabase-js`, `auth.audit_log_entries`, `signInWithOAuth`, `PULSE_AUTH_DEV_BYPASS`, service-role audit reads, and Tasks 1-3 are unverifiable for that reason.
- Supabase managed schema state / live tables (no dashboard access).
- Fly `pulse-api` secret values + auto-restart-on-`fly secrets set` behavior (no Fly access; not run).
- Google Cloud current redirect-URI list / domain verification (no console access).
- Live test execution (collection only; no `pytest`/`vitest` run, no code/deps installed).

---

## Recommended PM disposition sequence

1. **Resolve H1 first.** Decide the actual direction: (a) commit the real v3 Supabase spec to `043-oauth.md` and re-run this audit, or (b) confirm hand-rolled v2 is current and retract the "v3 Path A" framing. No implementation until this is settled.
2. **Resolve H2.** Author `ADR-006-authentication.md` recording the chosen auth architecture (this is the artifact whose absence caused the v1 miss-mode); make the spec cite it.
3. Disposition **ADV-1** (add `@radix-ui/react-popover` or hand-roll the menu) and **ADV-2** (re-baseline to 12 `useAuth` consumers).
4. Disposition **ADV-3** (#41 `/profiles` guard — add a step or defer on record) and **ADV-4** (re-baseline test count once H1 settles).
5. Close the F.2/C.3 coverage gaps (JWKS caching/rotation, concurrent refresh, CSRF on refresh/logout) and the G.1 `GOOGLE_OAUTH_CLIENT_*` naming conflict (reconnaissance D3) in the spec.
6. Only after HALT count = 0: re-audit (v3) if applicable, then Step 1.

**Codebase is unchanged from `acc6ed1` reconnaissance** (4 routers, profiles still unguarded, no new auth surface) — no re-recon needed; HALT condition #3 (codebase drift) did not fire. The drift is between the **prompt's premise and the spec document**, not the code.

---

*End of audit memo v2.*

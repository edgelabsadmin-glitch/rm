# Pre-spec audit v4 — Spec 043 v3.2 OAuth + ADR-006 v1.1 (audit v3 Hv3-1 + advisories verified)

**Audited:** 2026-05-22
**Auditor:** Claude Code (read-only)
**Subject:** intended `02_planning/specs/043-oauth.md` (v3.2) + `02_planning/architecture_decisions/ADR-006-authentication.md` (v1.1)
**Actual files found:** `02_planning/specs/043-oauth-v3-2.md` (untracked) + `02_planning/architecture_decisions/ADR-006-authentication-v1-1.md` (untracked); both canonical paths **deleted/absent**
**Method:** Read-only verification of audit v3 fix landings (Category L) + carry-forward (K + A-J)
**Reference:** Audit v3 at `00_research/audits/pre_spec_043_oauth_audit_v3.md` (`c57a15f`; 1 HALT + 3 advisories + 6 informationals)

---

## Executive summary

**Mixed result with 4 HALTs.** The **ADR-006 v1.1 amendment landed correctly** — it consistently describes asymmetric RS256/ES256 verification, adds Alternative E rejecting the HS256 path, specifies the `["RS256","ES256"]` algorithm allowlist, and documents the operator's live key verification. **But the spec 043 "v3.2" did NOT land**: the placed file `043-oauth-v3-2.md` is byte-for-byte the **v3.1 content** (status line still "DRAFT v3.1", active "HS256, key managed internally" at line 30, no RS256/ES256, no algorithm allowlist, no Task 7, no DoD row 13, Step 9 still 3 integration cases, footer "End of Spec 043 v3.1"). Consequently **audit v3's HALT Hv3-1 is NOT resolved in the spec**, and the spec now **directly contradicts the amended ADR**. Two further structural HALTs: the new docs were placed at **versioned filenames while the canonical paths were deleted** (every cross-reference now dangles, and both new files are untracked in git), and the **operator pre-work file is still missing** (ADVv3-1 claimed-resolved but `00_research/operator_prework/` does not exist). Codebase is unchanged from `acc6ed1` (HALT condition #5 clear). **No Step-1 implementation; this needs a re-placement + genuine spec amendment pass.**

---

## Findings

### HALTs

**Hv4-1 — Spec "v3.2" fixes did NOT land; Hv3-1 unresolved in the spec.** (Category L.1; HALT conditions #1 + #4; `043-oauth-v3-2.md` L3, L30, L120, §10, footer)
- **Evidence:** status line L3 = *"DRAFT **v3.1**"* (not v3.2); L30 (active "What Supabase Auth provides") = *"JWT minting + signing (**HS256**, key managed internally)"*; `grep RS256|ES256|algorithms=[` → **NONE**; no Task 7, no DoD row-13, no §6 "NO `SUPABASE_JWT_SECRET`" callout; §10 still titled "audit pointers for pre-spec audit **v3**"; footer L467 *"End of Spec 043 **v3.1**"*; Step 9 still has **3** integration cases (the "5 cases" grep hit is `test_403_format.py`, not the integration test). The file is the v3.1 document under a `-v3-2` filename — none of the audit-v3 spec edits were applied.
- **Impact:** audit v3's HALT Hv3-1 (HS256/JWKS contradiction) remains live in the spec; `jwt_verify.py` still can't be built coherently from the spec. **HALT condition #1 fires (active HS256 in §1) and #4 fires (status ≠ v3.2).**
- **Disposition:** PM applies the actual v3.2 edits to the spec (asymmetric RS256/ES256 in §1/Step1/§6/§10, `algorithms=["RS256","ES256"]` in `jwt_verify.py`, HS256-rejection test case, Task 7, DoD row 13, Step 9 cases 4+5, status→v3.2, footer→v3.2) — mirroring what ADR-006 v1.1 already did correctly.

**Hv4-2 — Spec contradicts ADR-006 v1.1 (HS256 vs asymmetric).** (Category A / L.1; HALT condition #7; spec L30 vs ADR L56/L61/L76)
- **Evidence:** ADR-006 v1.1 §Decision L56 = *"asymmetric JWT signing (RS256 or ES256) verified locally via Supabase JWKS endpoint"*, L76 = *"Algorithm allowlist `["RS256","ES256"]` — explicitly rejects HS256"*. Spec L30 = *"HS256, key managed internally."* The spec's active token-model statement is the **opposite** of the ADR it claims to honor (spec §1 L22 still cites the ADR).
- **Impact:** an implementer reading the spec builds HS256 expectations; reading the ADR builds asymmetric expectations. Direct doc-vs-ADR contradiction → rule-39 honor claim is false in current state.
- **Disposition:** folds into Hv4-1 — once the spec is genuinely amended to v3.2, the contradiction resolves.

**Hv4-3 — New docs placed at versioned filenames; canonical paths deleted; both untracked.** (Category B / structural; `git status`)
- **Evidence:** `git status` → `D 02_planning/specs/043-oauth.md` (canonical spec **deleted**); `?? 02_planning/specs/043-oauth-v3-2.md` (untracked). `ADR-006-authentication.md` is **absent** from `architecture_decisions/`; only `?? ADR-006-authentication-v1-1.md` exists (untracked). The v3.1→ convention (and ADR convention) is **overwrite-in-place, bump internal version**, not new suffixed files.
- **Impact:** every cross-reference now dangles: spec L22/L26 cite `ADR-006-authentication.md` (gone); audits v2/v3, ADR-006, reconnaissance, and PM_CONTEXT cite `02_planning/specs/043-oauth.md` (deleted). Neither new file is committed, so they're invisible to anything reading the canonical paths. This is a repo-integrity HALT independent of content.
- **Disposition:** PM renames the amended content onto the canonical paths (`043-oauth.md`, `ADR-006-authentication.md`), removes the `-v3-2`/`-v1-1` variants, and commits. Internal version bumps go in the status line, not the filename.

**Hv4-4 — Operator pre-work file still missing (ADVv3-1 not actually resolved).** (Category G / L.2; HALT condition #6; reference doc #7)
- **Evidence:** `00_research/operator_prework/` directory does not exist; `find . -iname "*prework*"` → none. Spec §7 L405 + Step 0 L109 reference `00_research/operator_prework/spec-043-supabase-prework.md` as "placed by operator." The audit-v4 context claimed this was placed; it is not.
- **Impact:** Step 3 hard-blocks on Tasks 1/2/5/6 from this file. (Spec inlines a 6-task summary §7 L407-413, so the *information* exists, but the referenced artifact does not.)
- **Disposition:** operator places the file before Step 3; or PM downgrades the §7 reference to "inline summary is authoritative."

### Advisories

**ADVv4-1 — ADR-006 v1.1 claims to remove the stale ADR-008 reference but it persists.** (Category L.5; ADR L? )
- **Evidence:** ADR v1.1 L4 + L11-15 claim *"fixes stale ADR-008 cross-reference per audit v3 INFO"*, yet `grep -c "ADR-008" ADR-006-authentication-v1-1.md` → **2** (the amendment claim itself + a residual reference, e.g. the `Related:` line). The fix is asserted but not fully applied.
- **Impact:** minor — a dangling ADR cross-reference (ADR-008 has never existed as a file). Clean up the residual mention.

### Informationals

**INFOv4-1 — ADR-006 v1.1 content is correct and complete.** Status "Accepted (amended to v1.1)", Version 1.1; §Decision asymmetric throughout; Alternative E (HS256 rejection) added; algorithm allowlist `["RS256","ES256"]`; operator key-verification recorded (L43); "Why amended" section closes Hv3-1. All HS256 mentions (15) are in correct rejected/legacy/Alternative-E/amendment contexts. **The ADR side of this iteration is a clean PASS.**
**INFOv4-2 — Carry-forward (audit v2) K-fixes intact in the spec content** — because the placed spec *is* v3.1: 12 useAuth consumers, explicit `@radix-ui/react-popover@^1.0.7` install, `require_caller` in `api/actions.py`, test counts as ranges. These survive (K.1-K.7 PASS), but they sit in a file that still carries the unresolved Hv3-1.
**INFOv4-3 — Codebase unchanged since `acc6ed1`.** `git log acc6ed1..HEAD -- 03_build` → empty. 4 routers, `/profiles` unguarded, no new auth surface. HALT condition #5 did not fire.
**INFOv4-4 — Unverifiable (read-only).** Live Supabase JWT-signing-key state (operator-confirmed in ADR L43, not codebase-checkable), JWKS endpoint contents, Fly secrets, Google redirect-URI list.

---

## Category-by-category findings

### Categories A-J — quick sweep
- **A (ADR cross-ref):** **FAIL/HALT** — spec cites `ADR-006-authentication.md` which no longer exists (Hv4-3); spec content contradicts the ADR (Hv4-2). ADR-006 v1.1 itself is well-formed (INFOv4-1).
- **B (codebase grounding):** repo facts unchanged + PASS (4 routers, port 5173, `/profiles` 0 `Depends`, psycopg3, `GOOGLE_OAUTH_CLIENT_ID/SECRET`, 4 X-User files) — but **B-level HALT Hv4-3** on doc placement/tracking.
- **C (test posture):** spec still ranges + ±5 (PASS as v3.1 content); but the v3.2-specific additions (HS256-rejection case, Step 9 cases 4+5) are **absent** (rolls into Hv4-1).
- **D (service-to-service):** PASS — spec preserves `PULSE_INTERNAL_API_TOKEN` (§1 L45); no middleware introduced; unchanged from audit v3.
- **E (frontend):** PASS — 12 useAuth consumers; explicit radix install (carry-forward intact).
- **F (backend):** `require_caller` in `api/actions.py` PASS; **F.2 Hv3-1 still unresolved in spec** (Hv4-1).
- **G (operator pre-work):** **FAIL/HALT Hv4-4** (file missing).
- **H (rollback):** PASS as written (dev-bypass toggle; frontend revert) — unchanged from audit v3.
- **I (security):** `PULSE_AUTH_DEV_BYPASS` mandate present; multi-domain backend-authoritative — PASS; but the signing-model defect (Hv3-1) persists in the spec.
- **J (watched concerns):** #30/#37/#40/#41 mechanisms present in spec content (PASS as v3.1); #30 automated both-domain test still **absent** (ADVv3-3 unresolved — rolls into Hv4-1).

### Category K — audit v2 fix verification (carry-forward)
K.1 spec-is-Supabase **PASS** · K.2 ADR exists (as `-v1-1`, see Hv4-3) **PASS-with-caveat** · K.3 radix explicit install **PASS** · K.4 12 useAuth **PASS** · K.5 `/profiles` guard **PASS** · K.6 ranges **PASS** · K.7 `api/actions.py` **PASS**. (All intact because the placed spec is the v3.1 doc.)

### Category L — audit v3 fix verification (PRIMARY)
| Check | Result | Evidence |
|---|---|---|
| **L.1** Hv3-1 fixed (asymmetric in spec §1/Step1/§6/§10) | **FAIL (Hv4-1)** | spec L30 active "HS256"; no RS256/ES256; status "v3.1"; footer "v3.1" |
| L.1 (ADR side) asymmetric in Decision | **PASS** | ADR L56/L61/L76 asymmetric; allowlist `["RS256","ES256"]`; HS256 only in rejected/Alt-E/amendment |
| L.1 algorithm allowlist in `jwt_verify.py` (spec) | **FAIL** | spec Step 1 L120 unchanged; no `algorithms=[...]` |
| L.1 HS256-rejection test case (spec) | **FAIL** | spec Step 1 L128 still the 6 v3.1 cases; no algorithm-substitution case |
| **L.2** pre-work file placed | **FAIL (Hv4-4)** | `00_research/operator_prework/` absent |
| **L.3** §6 "NO `SUPABASE_JWT_SECRET`" (spec) | **FAIL** | spec §6 unchanged; no such callout |
| L.3 (ADR side) "no `SUPABASE_JWT_SECRET`" | **PASS** | ADR verification points (asymmetric → no shared secret) |
| **L.4** Step 9 has 5 integration cases (4+5 multi-domain) | **FAIL** | spec Step 9 L278-281 still 3 cases; no onedge/edgeonline JWT cases |
| **L.5** stale ADR-008 ref removed | **PARTIAL/ADV (ADVv4-1)** | `grep -c ADR-008` ADR → 2 (claimed removed, still present) |
| **L.6** Task 7 (verify asymmetric keys) in Step 0 | **FAIL (spec)** / **PASS (ADR L43)** | spec Step 0 unchanged; ADR records operator verification |
| **L.7** DoD row 13 (asymmetric/HS256-grep) | **FAIL** | spec DoD table still 12 rows |

---

## Verification summary table

| Category | Findings | Highest severity |
|---|---|---|
| A — ADR cross-reference | Hv4-2, Hv4-3 | **HALT** |
| B — Codebase grounding | repo PASS; Hv4-3 (placement) | **HALT** |
| C — Test posture | v3.2 additions absent | (rolls into Hv4-1) |
| D — Service-to-service | PASS | INFO |
| E — Frontend | PASS (carry-forward) | INFO |
| F — Backend | Hv4-1 (Hv3-1 unresolved) | **HALT** |
| G — Operator pre-work | Hv4-4 | **HALT** |
| H — Rollback | PASS | INFO |
| I — Security | PASS (signing defect persists) | (rolls into Hv4-1) |
| J — Watched concerns | mechanisms present; #30 test absent | (rolls into Hv4-1) |
| K — audit v2 fixes | 7/7 PASS | NONE |
| L — audit v3 fixes | ADR PASS; **spec FAIL across the board** | **HALT** |

**Totals: 4 HALTs (Hv4-1 spec-not-amended, Hv4-2 spec-vs-ADR contradiction, Hv4-3 file placement/deletion, Hv4-4 pre-work missing), 1 advisory (ADVv4-1), 4 informationals.**

---

## Audit v3 → v4 progress

| Audit v3 finding | v3.2 + v1.1 disposition claimed | Actual status |
|---|---|---|
| Hv3-1 (HS256/JWKS contradiction) | both amended to asymmetric | **PARTIAL** — ADR ✅ fixed; **spec ❌ not amended** (placed file is v3.1) |
| ADVv3-1 (pre-work file missing) | file placed | **FAIL** — still missing |
| ADVv3-2 (`SUPABASE_JWT_SECRET` in §6) | §6 explicit "NOT needed" | **FAIL (spec)** / ✅ (ADR) |
| ADVv3-3 (multi-domain JWT test) | Step 9 cases 4+5 added | **FAIL** — spec still 3 cases |
| INFO (stale ADR-008 ref) | v1.1 removes it | **PARTIAL** — still 2 mentions (ADVv4-1) |

---

## Audit limitations

Could not be verified (read-only; no dashboard/Fly/Google access; no execution): live Supabase JWT-signing-key mode (operator states asymmetric in ADR L43 — accepted on operator attestation, not codebase-verifiable); JWKS endpoint contents; Fly secret values + auto-restart; Google redirect-URI list; whether a *correct* v3.2 spec exists outside the repo (only the v3.1-content `-v3-2` file is present here).

---

## Recommended PM disposition sequence

1. **Hv4-3 first (repo integrity):** rename the amended ADR content onto the canonical `02_planning/architecture_decisions/ADR-006-authentication.md`; delete the `-v1-1` variant; restore/replace `02_planning/specs/043-oauth.md` as the canonical spec path; commit both. Version bumps live in status lines, not filenames.
2. **Hv4-1 + Hv4-2 (the real work):** actually apply the v3.2 edits to the spec — asymmetric RS256/ES256 in §1/Step1/§6/§10, `algorithms=["RS256","ES256"]`, HS256-rejection test, Task 7, DoD row 13, Step 9 cases 4+5, status→v3.2, footer→v3.2. Mirror what ADR-006 v1.1 already did. (The ADR is the correct template.)
3. **Hv4-4:** operator places `spec-043-supabase-prework.md` (or PM marks the inline §7 summary authoritative).
4. **ADVv4-1:** remove the residual ADR-008 reference from ADR-006.
5. Re-audit (v5) against the corrected canonical files. **HALT count must reach 0 before Step 1.**

Net: this iteration **amended the ADR but not the spec**, and **broke the canonical file paths**. A focused re-placement + spec-amendment pass (not a redraft — the ADR shows the exact target) closes all four HALTs.

---

*End of audit memo v4.*

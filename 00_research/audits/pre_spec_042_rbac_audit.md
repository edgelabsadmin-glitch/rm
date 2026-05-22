# Pre-spec 042 RBAC audit memo

**Audited spec:** `02_planning/specs/042-rbac.md` (commit `6e3c619` on `dz-001`)
**Audit date:** 2026-05-22 (Session 19 late-late stream extended)
**Auditor:** Claude Code (read-only; no spec or code edits — this memo is the only artifact)
**Cross-referenced:** `03_build/front/src/{App.tsx, lib/api.ts, session/useSession.ts}`, `src/fixtures/demo_characters.ts`, the three Constellation composers + `demo_patterns.ts`, `03_build/api/{actions.py, middleware/, profiles.py}`, `03_build/tests/`, `PM_CONTEXT.md` (§4.16/§4.22/§6/§7 rules + watched concerns).
**Output:** Structured findings + recommended dispositions for PM ratification. No implementation.

## Summary

- **Total findings: 17** (4 positive confirmations folded into INFORMATIONAL)
- **🚦 HALT: 2**
- **⚠️ ADVISORY: 6**
- **ℹ️ INFORMATIONAL: 9**
- **Overall recommendation: PROCEED WITH MODIFICATIONS.** The core model is sound and **fixture-aligned** — role definitions, `deriveAccountScope()` logic, the 11 demo users, scope-count math, and the Settings topology all verify correct against canonical `demo_characters.ts`. But two HALTs must be resolved first: (H1) the spec wires guards into front-end components that **don't exist yet** (`PerAccountView`, `ActionQueueView`), and (H2) the §7 pulse-api middleware targets an **endpoint surface that doesn't match reality** AND duplicates **scope enforcement that already ships** in `api/actions.py` (spec 031). Both are spec-text reconciliations, not redesigns.

---

## Findings by dimension

### Dimension 1 — Spec internal consistency
- **⚠️ ADVISORY (A2): §9 Settings table emails contradict §8 `DEMO_USERS`.** §8 sets the convention `{first}.{last}@onedge.co` with **Iffi on `edgeonline.co`** (`iffi.wahla@edgeonline.co`). §9's table shows short forms (`iffi@onedge.co`, `sidra@onedge.co`) **and puts Iffi back on `onedge.co`** — directly contradicting the §8 multi-domain rule that §13/§15 + watched concern #30 depend on. *Disposition: MODIFIED — regenerate §9 table emails from the §8 `DEMO_USERS` source (or note "illustrative; authoritative in §8").*
- Permission matrix (§3) ↔ `deriveAccountScope` (§4) ↔ demo assignments (§8) are otherwise mutually consistent. Implementation sequence (§14) is reachable from the types/derivation in §4–§7 (modulo the HALTs below).

### Dimension 2 — Cross-spec dependency completeness
- **✅ Confirmed:** front-end route tree exists in `App.tsx` (`<Routes>` under `<AppShell/>`, `Navigate` already imported/used) and is structurally ready for `RoleGuard` wrapping. Constellation `accountScope` prop **exists** (spec 041 Step 8). `demo_characters.ts` exports needed for `DEMO_USERS` all exist (`DEMO_RMS`, `DEMO_MANAGERS`, `DEMO_CEO=iffi-wahla`, `DEMO_VP_CS=eddy-chen`, `DEMO_ACCOUNTS`, `DemoAccountId`). Action Queue already accepts scope filtering (`useActions(filters)` with `rm_id`/`manager` params, Step 4).
- **🚦 HALT (H1) — see Dimension 7.** Two referenced components don't exist.
- **ℹ️ INFORMATIONAL (I1):** spec writes the middleware path as `pulse-api/middleware/rbac_scope.py`; the actual backend lives at `03_build/api/` and an `api/middleware/` dir **already exists**. Path/name drift to correct during implementation.

### Dimension 3 — Canonical fixture alignment
- **✅ Confirmed correct.** All 6 RM ids (`sidra-zia`, `sajjal-shaheedi`, `yozeline-candia`, `ameer-ali`, `mubeen-sohail`, `akash-tahir`) match `DEMO_RMS`. Both manager ids (`sarah-hooper`, `muhammad-ibrahim`) match `DEMO_MANAGERS`. `iffi-wahla` + `eddy-chen` match `DEMO_CEO`/`DEMO_VP_CS`. `pulse-admin` is a **new functional alias** — no collision with any existing canonical id (verified: not present in fixtures). Email convention + Iffi `edgeonline.co` exception matches operator confirmation (PM_CONTEXT watched concern #30, Block MM).
- Note: `DEMO_CEO`/`DEMO_VP_CS` are single `as const` objects, not array members; spec creates a fresh `DEMO_USERS` array — no conflict, but implementation should keep them as the single source for the two exec ids/names (don't re-type).

### Dimension 4 — AccountScope derivation correctness
- **✅ Confirmed correct against canonical fixture.** Per-RM books: Sidra `[dhr-health-clinics, dhr-health-hospital, palm-primary-care]` = **3**; Sajjal `[mendota-insurance, dmv-allergy-asthma, cirventis]` = **3**; Yozeline `[manhattan-restorative]` = **1**; Ameer = **5**; Mubeen = **1**; Akash = **1** (total 14). Manager scope: Sarah (sidra+sajjal+yozeline) = 3+3+1 = **7** ✓; Muhammad = 5+1+1 = **7** ✓. Executive/Admin = **14** ✓. Every §9 scope count is correct. The `deriveAccountScope` switch logic (rm by `rmId`, manager by team `rmIds`, exec/admin all) is sound.
- **ℹ️ INFORMATIONAL (I4):** the TS `switch` in §4 has a `case 'manager':` block that declares `const teamRmIds` without braces — will trip `no-case-declarations` lint. Trivial (wrap in `{}`); flagging so the implementer doesn't lose a halt to it.

### Dimension 5 — Defense-in-depth enforcement coverage
- **🚦 HALT (H2): the §7 middleware both mismatches the real endpoint surface AND duplicates existing enforcement.**
  - **Existing enforcement already ships** (spec 031, `api/actions.py`): a `Caller` with `role ∈ {rm, manager, admin}`, `visible_rm_ids()` (manager scope), admin bypass, `_load_in_scope()` → `403 "action outside your scope"`, and `403` on missing/bogus role. `test_actions_api_db.py` exercises all of it. So Action-Queue defense-in-depth is **largely done** — spec 042 should **extend** it (add the `executive` role; executives get **no** queue access), not build a parallel `rbac_scope.py` from scratch.
  - **Endpoint names don't exist as written:** spec lists `/api/queue`, `/api/accounts`, `/api/constellation`, `/api/executive`, `/api/settings/users`. Actual API is `/actions`, `/actions/{id}`, `/actions/{id}/{approve,modify,reject}` (+ `profiles.py`, `admin/`). **`/constellation` and `/executive` have NO server endpoints** — those surfaces are 100% client-side fixture-derived in Phase 1, so there is nothing for middleware to wrap there yet.
  - **Header model differs:** existing API uses `X-User-Id` / `X-User-Role` / `X-Report-Ids` (manager passes reports in-header). Spec proposes `X-Dev-User-Id` + server-side `get_team_rm_ids()`. Two different scoping mechanisms.
  - *Disposition: REQUIRES PM DECISION + MODIFIED — reconcile §7 to (a) extend the existing `Caller`/`visible_rm_ids` model with `executive`, (b) keep `/actions*` naming, (c) drop `/api/constellation` + `/api/executive` middleware from Phase-1A scope (no endpoints), (d) decide whether to migrate the header model or keep `X-User-*`. The dev-mode injector concept (watched concern #29) is fine and gated.*
- **ℹ️ INFORMATIONAL (I8):** `api/admin/kill_switch.py` comment already says its admin guard is a placeholder "in specs 042/043" — the backend anticipates this spec. Good.

### Dimension 6 — Constellation overlay composer scope filtering (#26 closure)
- **⚠️ ADVISORY (A1): the §6/§11 composer references don't match shipped code.**
  - There is **no `cluster_pattern_composer.ts`**. The cluster-pattern overlay is `DEMO_PATTERNS` (fixture) + `clusterCentroid()` + filtering done **inline in `Constellation.tsx`**. §6 says "cluster_pattern_composer.ts equivalent" (hedged) but §11 lists a `cluster_pattern_composer.test.ts` that has no module to test.
  - Actual composer signatures are **parameterless module-readers**: `composeCapacityImbalance()` and `composeEscalationTierJumps(now?, events?)` — NOT the `computeRmCapacityImbalance(accounts, rms, accountScope)` signature shown in §6.
  - *Disposition: MODIFIED — implement scope filtering by adding an optional `accountScope` arg to `composeCapacityImbalance` / `composeEscalationTierJumps`, and add a scoped filter for `DEMO_PATTERNS` in `demo_patterns.ts` (filter-out when any `support_account_id ∉ scope`, per §6 edge case) consumed in `Constellation.tsx`. Rename the §11 test target from `cluster_pattern_composer.test.ts` → `demo_patterns.test.ts` (or extend the inline Constellation test). The §6 "all existing tests pass with `accountScope=undefined`" requirement is correct and achievable.*
- **✅ Confirmed:** the §6 behavior table + the Yozeline/Sajjal/Sarah expectations are consistent with the actual composer outputs (Sajjal top-loaded; pattern = DHR+Manhattan filtered-out for Yozeline).

### Dimension 7 — Front-end route guard feasibility
- **🚦 HALT (H1): §5 wires guards around components that don't exist.**
  - `/accounts/:id` currently renders a **`<Placeholder spec="036-037">`**, not a `<PerAccountView/>`. The §5 "sub-route guard **inside PerAccountView component**" + the Executive read-only exception have **no host component** to live in. `PerAccountView` is unbuilt (spec 037 is still a placeholder route).
  - `/actions` renders **`<QueueList/>`**, not the `<ActionQueueView/>` named in §5's route tree.
  - *Disposition: REQUIRES PM DECISION — either (a) scope spec 042 to **route-level** guards only (wrap `QueueList`, the `/accounts/:id` Placeholder, `Constellation`, `ExecutiveView`, `SettingsUsersPanel`) and defer the in-`:id`-scope sub-guard until PerAccountView is built (spec 037), or (b) build a minimal real PerAccountView as part of 042. Recommend (a): route-guard now, sub-route in-scope check added when spec 037 lands. Rename `ActionQueueView`→`QueueList` in the spec.*
- **✅ Confirmed:** `Navigate` is imported and already used in `App.tsx` (`/admin` index redirect, `*` catch-all) — react-router v6 supports the `RoleGuard` `<Navigate replace/>` pattern. Route-tree wrapping won't break existing tests (no `App.test.tsx` exists yet; the spec proposes adding one).

### Dimension 8 — Settings panel `/settings/users` composition
- **ℹ️ INFORMATIONAL (I6):** three-column layout matches the Per-Account/Executive precedent; longest cells ("Muhammad Ibrahim" + `muhammad.ibrahim@onedge.co` + "Manager" + scope count) fit a typical desktop table. Executive scope detail = 14 account names — verify the right-column (~320px) list scrolls rather than overflows (minor; CSS at build). No blocker.
- **✅ Confirmed:** "Change role" is **text-only placeholder** per §9 (no half-built modal) — good demo hygiene; satisfies §15-style scope discipline.

### Dimension 9 — Test coverage estimate (~25-30 tests)
- **✅ Confirmed feasible.** `03_build/tests/` has a working **pytest** suite (`test_actions_api_db.py` already covers role-scoped queue access, 403s, admin bypass) — the proposed back-end tests extend an existing, passing pattern. Front-end Vitest at 65 today; +15-18 → ~80-83 is reasonable.
- **⚠️ ADVISORY (A6-test): the proposed back-end tests partly already exist.** `test_actions_api_db.py` already asserts rm/manager/admin scope + 403. New back-end work is mostly **adding the `executive` role** + the (deferred) account/executive/settings endpoints. The "10-12 new pytest" estimate likely overshoots if Phase-1A drops the non-existent endpoints. *Disposition: MODIFIED — re-scope back-end test count after H2 reconciliation.*

### Dimension 10 — Implementation sequence (§14) halt appropriateness
- 8 halts across ~4.5-5.5h are logically bounded and each yields a spot-checkable artifact. **⚠️ ADVISORY (A6): Step 6 (pulse-api middleware, ~60min) is mis-scoped** given H2 — much of the queue enforcement exists; `/constellation`+`/executive` have no endpoints. Step 6 will be shorter (extend `Caller` with `executive`) OR partly N/A. *Disposition: MODIFIED — rebalance Step 6 after H2; consider folding it into Step 5.* Steps 1–5 + 7–8 boundaries are sound. No concurrent pulse-api **deploy** is required (the API already runs locally for tests); production deploy + spec 043 OAuth is the separate cutover.

### Dimension 11 — DoD criteria (§12) measurability
- 17 DoD items are mostly testable as written. **ℹ️ INFORMATIONAL (I3): security items absent from DoD** — no RBAC-bypass-attempt logging, no rate-limiting on auth, no CSRF for mutations. Phase-1 header-auth has no CSRF surface and these are reasonably Phase-2, but worth an explicit "deferred" line so the gap is intentional, not forgotten. DoD item "User switcher gated behind `import.meta.env.DEV` per posture rule #44" — see I2.

### Dimension 12 — Watched concerns alignment
- **✅** §13's five concerns are deferrable, not blocking. **Multi-domain SSO (#30)** blocks **production OAuth deployment (spec 043)**, NOT Phase-1A implementation — the dev-mode `X-Dev-User-Id` injector needs no real domains. So #30 is a spec-043 kickoff action item, correctly filed. None of the five immediately block 042 implementation.

### Dimension 13 — PM_CONTEXT cross-reference
- **✅ Confirmed:** §4.16 (pre-spec audits) ✓, §4.22 (branch discipline) ✓, §6 #1 white-label ✓ (PM_CONTEXT line 20 "product is white-labeled"), §7 rule 27 (real-data principle) ✓, watched concerns #26/#29/#30/#31/#32 all present and consistent with the spec's framing.
- **ℹ️ INFORMATIONAL (I2): could not confirm "posture rule #44."** §12 + §13 cite "posture rule #44" for `import.meta.env.DEV` gating; PM_CONTEXT §7 rules currently enumerate through **31**. The DEV-gating *precedent* exists (Polish #27 / watched #23 demo-fixture pattern), but the specific "#44" citation may be drift from a different rule list or a stale number. *Disposition: PM verify the citation; low priority.*

### Dimension 14 — Demo flow validity (§10)
- **Story A (Yozeline RM):** default `/actions`, Constellation scoped to Manhattan + her RM/Sarah nodes, capacity overlay empty (her score 1.1 ≠ top — ✓ matches composer), tier-jump surfaces (Manhattan in scope — ✓), cluster pattern correctly **omitted** (DHR+Manhattan partially out-of-scope → filter-out per §6 — ✓), `/executive` + `/accounts/dhr-health-clinics` redirect. **Consistent** — *contingent on H1 (sub-route guard host) being resolved.*
- **Story B (Sarah Manager):** team scope 7, all 3 overlays (Sajjal top-loaded ✓, Manhattan tier-jump ✓, DHR+Manhattan pattern both in team scope ✓). **Consistent.**
- **Story C (Iffi Executive):** default `/executive`, full Constellation, read-only `/accounts/:id` nav, **no `/actions`**. **⚠️ ADVISORY (A5): the "Executive has zero Action Queue access" is a deliberate product choice worth ratifying.** An executive seeing a **read-only** queue (transparency into what RMs are being asked to approve) is a plausible alternate. *Disposition: REQUIRES PM DECISION — confirm "no queue for execs" vs "read-only queue for execs." Spec currently says blocked; either is implementable.*

### Dimension 15 — Spec scope boundaries
- **✅ Clean.** Nothing in the §2 out-of-scope list (OAuth, live role-change, role-change audit, per-field perms, multi-tenant, theming, user CRUD) leaks back into in-scope sections. "Change role" stays a text placeholder (§9). No tenant logic present. **ℹ️ INFORMATIONAL (I5):** confirmed no accidental half-implementation of deferred items.

---

## Halt triggers requiring PM ratification

1. **🚦 H1 — Guard target components don't exist.** §5 wraps `<PerAccountView/>` and `<ActionQueueView/>` and puts a sub-route in-scope guard "inside PerAccountView"; actual routes render a **Placeholder** (`/accounts/:id`) and **`QueueList`** (`/actions`). *Recommended: route-level guards now; defer the `:id` in-scope sub-guard to when spec 037 PerAccountView is built; rename `ActionQueueView`→`QueueList` in the spec. (REQUIRES PM DECISION: route-guard-only vs build PerAccountView in 042.)*
2. **🚦 H2 — pulse-api middleware mismatches reality + duplicates existing enforcement.** Endpoint names (`/api/queue`, `/api/constellation`, `/api/executive`, `/api/accounts`) don't exist (actual: `/actions*`; constellation/executive are client-side, no endpoints). The Action-Queue scope enforcement **already ships** (`api/actions.py` `Caller`/`visible_rm_ids`/403, spec 031). *Recommended: extend the existing `Caller` model with the `executive` role; keep `/actions*` naming + `X-User-*` headers; drop client-only-surface middleware from Phase-1A; reconcile the 403 body format. (REQUIRES PM DECISION on header-model migration.)*

## Advisory findings for PM ratification

- **A1 (Dim 6):** No `cluster_pattern_composer.ts`; composer signatures in §6 don't match shipped `composeCapacityImbalance()`/`composeEscalationTierJumps()`. → MODIFIED: scope-filter via optional `accountScope` arg + `demo_patterns.ts` filter; fix §11 test name.
- **A2 (Dim 1):** §9 Settings emails contradict §8 (short form + Iffi on wrong domain). → MODIFIED: regenerate from §8.
- **A3 (Dim 3):** Existing `useSession.Role` ("rm"|"manager"|"admin") lacks `executive`; spec adds a parallel `UserRole` + `AuthContext`. → REQUIRES PM DECISION: does `AuthContext.user.role` supersede `useSession.Role` (Header/AdminLayout consume it today), or coexist? Spec should state the reconciliation.
- **A4 (Dim 5):** 403 body `{error,required_role,user_role,message}` differs from existing FastAPI `{detail}`; `X-Dev-User-Id` differs from existing `X-User-Id/Role/Report-Ids`. → MODIFIED: align to existing conventions or document migration.
- **A5 (Dim 14):** Executive fully blocked from `/actions` — confirm vs read-only queue for transparency. → REQUIRES PM DECISION.
- **A6 (Dim 9/10):** Back-end test count + Step-6 effort overshoot given existing enforcement. → MODIFIED: re-scope after H2.

## Informational observations

- **I1:** middleware path drift (`pulse-api/middleware/` vs actual `03_build/api/middleware/`).
- **I2:** "posture rule #44" citation unverified (PM_CONTEXT §7 rules go to 31); DEV-gating precedent exists regardless.
- **I3:** DoD omits bypass-attempt logging / rate-limit / CSRF — reasonably Phase-2; add an explicit "deferred" line.
- **I4:** `deriveAccountScope` `case 'manager'` needs `{}` braces (no-case-declarations lint). Trivial.
- **I5:** scope boundaries clean; deferred items not half-built.
- **I6:** Settings right-column 14-name exec scope list should scroll, not overflow (CSS at build).
- **I7:** multi-domain SSO (#30) blocks prod OAuth, not Phase-1A — correctly deferred to spec 043 kickoff.
- **I8:** `api/admin/kill_switch.py` already references "specs 042/043" — backend anticipates this spec.
- **Positive:** roles, `deriveAccountScope`, 11 demo users, all scope counts, and Settings topology are **fixture-correct** — the substance of the spec is solid.

---

## Recommended next steps

1. PM ratifies dispositions for **H1** and **H2** (both REQUIRES PM DECISION components) — these gate implementation. Recommend route-level guards now (H1-a) and extend-existing-enforcement (H2).
2. PM applies the MODIFIED edits (A1, A2, A4, A6) and decides A3 (role-type reconciliation) + A5 (executive queue access) in the spec text.
3. After spec 042 is updated + re-committed on `dz-001`, PM sends the ratified Step-1 implementation prompt (types + `deriveAccountScope` + `DEMO_USERS`), which the audit confirms is the lowest-risk, fully-fixture-aligned starting point.
4. No implementation begins until the above lands. All work continues on `dz-001`; merge to `main` awaits the operator two-step authorization.

*End of pre-spec 042 audit. Read-only; no spec or code modified.*

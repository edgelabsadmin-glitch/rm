# Spec 042 — Role-Based Access Control (RBAC)

**Status:** Draft for PM/operator review. Lands on `dz-001` once ratified and pre-spec audit cleared.
**Author:** PM (Senior Product Advisor)
**Drafted:** 2026-05-22 (Session 19 late-late stream)
**Phase:** Week 4 — back-end infrastructure
**Depends on:** spec 034 (frontend shell), spec 041 (Constellation `accountScope` prop interface)
**Enables:** spec 043 (OAuth — real user→role mapping via SSO claims)
**Coordinates with:** watched concern #26 (overlay composer scope filtering propagation)
**Estimated Claude Code execution:** 3.5-5.5 hours

---

## 1. Purpose

Phase 1 Pulse currently treats every user as having full access to every surface and every account. Spec 042 introduces role-based access control with four distinct roles, propagates scope filtering through every read surface (front-end + pulse-api), and surfaces a read-only Settings panel so the Admin role can see (but not yet modify) role assignments across the org. Real assignment workflow lands Phase 2 post-demo; Phase 1A delivers the scoping enforcement + viewable role topology.

Spec 042 also unblocks watched concern #26 from spec 041 closure: the three Constellation overlay composers (cluster-pattern, capacity-imbalance, escalation-tier-jump) must honor `accountScope` so scoped users don't see overlay references to accounts outside their scope.

---

## 2. Scope

### In scope

- 4-role definition + permission matrix (RM / Manager / Executive / Admin)
- AccountScope derivation logic (given role + user identity → `DemoAccountId[]`)
- Front-end route guards (protected routes redirect on unauthorized)
- AccountScope propagation through:
  - Constellation graph filtering (already wired via spec 041 Step 8)
  - All three Constellation overlay composers (closes watched concern #26)
  - Action Queue filtering (RM sees their cards; Manager sees team cards; Executive sees all; Admin sees all)
  - Per-Account View access (RM can only navigate to accounts in scope)
  - Executive View access (only Executive + Admin can navigate to `/executive`)
- Pulse-api middleware: JWT-claim-derived scope filtering applied to all read endpoints
- Hardcoded Phase 1 demo role assignments in canonical `demo_characters.ts`
- Settings panel (`/settings/users`) with read-only role topology view (Admin-only access)
- Tests: route guards, scope filtering correctness per role, composer scope propagation, middleware enforcement, settings panel access control

### Out of scope (deferred to spec 043 or Phase 2)

- Real OAuth integration (spec 043)
- Live role assignment / role change workflow (Phase 2)
- Role-change audit log entries (Phase 2 — current §6 #2 audit covers RM actions, not role mutations)
- Fine-grained per-field permissions within scope (Phase 1 is coarse — role grants scope; within scope, full access)
- Multi-tenant role isolation (Phase 1 single-tenant)
- Role-based theming or UI variants beyond access control (out of scope; same UI, scoped data)
- User management UI for creating/deactivating users (Phase 2)

---

## 3. Role definitions + permission matrix

### Role definitions

**RM (Relationship Manager).** Scoped to their own book of accounts. Sees Action Queue filtered to their cards, Per-Account View only for in-scope accounts, Constellation showing only their accounts + their RM node + their manager's node. No Executive View access. No Settings access.

**Manager.** Scoped to their team's books (all accounts owned by RMs they manage). Sees Action Queue filtered to team cards, Per-Account View for any account in team scope, Constellation showing team accounts + team RMs + themselves + peer managers. No Executive View access. No Settings access.

**Executive.** Read-only access to Executive View + Constellation (full org scope) + read-only Per-Account View navigation (full org). Cannot access Action Queue (executives don't approve RM actions; that's the RM/Manager workflow). No Settings access.

**Admin.** Full access to everything. Sees all Action Queue cards, all Per-Account Views, Executive View, full Constellation, Settings panel. Phase 1 single Admin role per tenant; Phase 2 may introduce role hierarchies if needed.

### Permission matrix

| Surface | RM | Manager | Executive | Admin |
|---|---|---|---|---|
| `/actions` (Action Queue) | ✓ (own book) | ✓ (team book) | ✗ | ✓ (all) |
| `/accounts/:id` (Per-Account View) | ✓ (in scope only) | ✓ (in scope only) | ✓ (all, read-only navigation) | ✓ (all) |
| `/constellation` | ✓ (own book scope) | ✓ (team book scope) | ✓ (full org) | ✓ (full org) |
| `/executive` (Executive View) | ✗ | ✗ | ✓ (read-only) | ✓ |
| `/settings/users` (Settings panel) | ✗ | ✗ | ✗ | ✓ |
| Action mutation (approve/modify/reject) | ✓ (own cards) | ✓ (team cards) | ✗ | ✓ (all cards) |
| Constellation overlay Investigate clicks | ✓ (route to in-scope) | ✓ (route to in-scope) | ✓ (route to anywhere) | ✓ (route to anywhere) |

### Default routes per role on login

| Role | Default route after login |
|---|---|
| RM | `/actions` (their queue) |
| Manager | `/actions` (team queue) |
| Executive | `/executive` |
| Admin | `/actions` (all queue) |

---

## 4. AccountScope derivation

### Type

```typescript
// extends existing DemoAccountId from demo_characters.ts
export type AccountScope = DemoAccountId[]; // empty = no access; undefined = unscoped (legacy / pre-RBAC)
```

### Derivation per role

Pure function in `src/lib/rbac/accountScope.ts`:

```typescript
export function deriveAccountScope(
  role: UserRole,
  userId: string, // demo character id; Phase 1 hardcoded, Phase 2 from OAuth claim
): AccountScope {
  switch (role) {
    case 'rm':
      // RM sees their own book
      return DEMO_ACCOUNTS
        .filter(a => a.rmId === userId)
        .map(a => a.id);
    case 'manager':
      // Manager sees all accounts owned by RMs they manage
      const teamRmIds = DEMO_RMS
        .filter(rm => rm.managerId === userId)
        .map(rm => rm.id);
      return DEMO_ACCOUNTS
        .filter(a => teamRmIds.includes(a.rmId))
        .map(a => a.id);
    case 'executive':
    case 'admin':
      // Full org scope
      return DEMO_ACCOUNTS.map(a => a.id);
  }
}
```

All numbers derived from canonical `demo_characters.ts` per real-data principle (§7 rule 27). No hardcoded counts.

### AccountScope propagation

Every read surface receives `accountScope` from a top-level `AuthContext` provider in `App.tsx`:

```typescript
// src/lib/auth/AuthContext.tsx (new)
interface AuthContextValue {
  user: DemoUser; // { id, role, displayName, ... }
  accountScope: AccountScope;
}
```

Consumers use `useAuth()` hook to read scope; pass to surfaces that need it (Constellation, Action Queue, Per-Account View navigation guards, all three overlay composers).

---

## 5. Front-end route guards

### Implementation

New component `src/lib/auth/RoleGuard.tsx`:

```typescript
interface RoleGuardProps {
  allowedRoles: UserRole[];
  fallbackRoute?: string; // default '/actions'
  children: ReactNode;
}

export function RoleGuard({ allowedRoles, fallbackRoute = '/actions', children }: RoleGuardProps) {
  const { user } = useAuth();
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={fallbackRoute} replace />;
  }
  return <>{children}</>;
}
```

### Route tree wrapping (App.tsx update)

```typescript
<Routes>
  <Route path="/actions" element={
    <RoleGuard allowedRoles={['rm', 'manager', 'admin']}>
      <ActionQueueView />
    </RoleGuard>
  } />
  <Route path="/accounts/:id" element={
    <RoleGuard allowedRoles={['rm', 'manager', 'executive', 'admin']}>
      <PerAccountView />
    </RoleGuard>
  } />
  <Route path="/constellation" element={
    <RoleGuard allowedRoles={['rm', 'manager', 'executive', 'admin']}>
      <Constellation />
    </RoleGuard>
  } />
  <Route path="/executive" element={
    <RoleGuard allowedRoles={['executive', 'admin']}>
      <ExecutiveView />
    </RoleGuard>
  } />
  <Route path="/settings/users" element={
    <RoleGuard allowedRoles={['admin']}>
      <SettingsUsersPanel />
    </RoleGuard>
  } />
</Routes>
```

### Sub-route guards

Per-Account View also enforces in-scope check at component level (since `:id` route param can be anything):

```typescript
// inside PerAccountView component
const { accountScope } = useAuth();
const { id } = useParams();
if (accountScope && !accountScope.includes(id as DemoAccountId)) {
  return <Navigate to="/actions" replace />;
}
```

Executive role exception: Executive can navigate to any `/accounts/:id` (read-only); scope check skipped for Executive role.

---

## 6. Constellation overlay composer scope filtering (closes watched concern #26)

### The problem (recap)

Per spec 041 Step 8 ratification, Constellation graph itself filters by `accountScope`. But the three overlay composers (`rm_capacity_composer.ts`, `cluster_pattern_composer.ts` equivalent, `escalation_tier_jump_composer.ts`) read full `DEMO_ACCOUNTS` regardless of scope.

Scoped user (e.g., RM Yozeline with `accountScope=['manhattan-restorative']`) currently sees:
- Constellation graph filtered correctly to just Manhattan ✓
- Cluster pattern overlay referencing "DHR Health Clinics + Manhattan Restorative" — exposes DHR which is out-of-scope ✗
- Capacity imbalance overlay referencing Sajjal's book — exposes Mendota + DMV + Cirventis ✗
- Escalation tier-jump overlay referencing Manhattan — in-scope, OK ✓

### The fix

All three composers accept optional `accountScope` parameter; filter their working set before computing:

```typescript
// rm_capacity_composer.ts (updated)
export function computeRmCapacityImbalance(
  accounts: typeof DEMO_ACCOUNTS,
  rms: typeof DEMO_RMS,
  accountScope?: AccountScope,
): RmCapacityCard[] {
  const scopedAccounts = accountScope
    ? accounts.filter(a => accountScope.includes(a.id))
    : accounts;
  const scopedRmIds = new Set(scopedAccounts.map(a => a.rmId));
  const scopedRms = rms.filter(r => scopedRmIds.has(r.id));
  // ... existing logic operates on scopedAccounts + scopedRms
}
```

Same pattern for cluster_pattern (filter DEMO_PATTERNS to those where all `support_account_ids` ⊆ scope) and escalation_tier_jump (filter DEMO_TIER_JUMP_EVENTS to those where event's `accountId` ∈ scope).

### Behavior expectations per role

| Role | What overlays they see |
|---|---|
| RM (e.g., Sajjal) | Only overlays involving accounts in their book (capacity overlay surfaces if their score warrants, otherwise empty; tier-jump if their account flips; pattern only if pattern's accounts all in their book) |
| Manager (e.g., Sarah) | Overlays involving their team's accounts |
| Executive | All overlays (full org scope) |
| Admin | All overlays (full org scope) |

### Edge case: pattern partially in scope

If a Skill 10 pattern card references accounts both in-scope and out-of-scope for the current user, the pattern is **not surfaced** at all to that user. Phase 1 demo doesn't have this case (DHR + Manhattan pattern accounts are both Strategic; only Executive/Admin/owning-RM-Sidra see it). Phase 1B post-pulse-api may surface this case; behavior is filter-out (not partial-display).

---

## 7. Pulse-api middleware (defense in depth)

### New middleware: `pulse-api/middleware/rbac_scope.py`

Wraps all read endpoints. Extracts user role + identity from JWT claim (provided by spec 043 OAuth; Phase 1 dev mode uses fixture JWT with hardcoded claims).

```python
def apply_scope_filter(query, user_role: str, user_id: str):
    """Filter DB query by user's account scope."""
    if user_role in ('executive', 'admin'):
        return query  # full org access
    elif user_role == 'manager':
        team_rm_ids = get_team_rm_ids(user_id)
        return query.filter(Account.rm_id.in_(team_rm_ids))
    elif user_role == 'rm':
        return query.filter(Account.rm_id == user_id)
    else:
        raise PermissionDenied(f"Unknown role: {user_role}")
```

### Applied to endpoints

- `GET /api/queue` — filter cards by scope
- `GET /api/accounts/:id` — 403 if out of scope (except Executive read-only)
- `GET /api/accounts` (list) — filter by scope
- `GET /api/constellation` — filter accounts + composer outputs by scope
- `GET /api/executive` — 403 unless Executive or Admin
- `GET /api/settings/users` — 403 unless Admin
- `POST /api/queue/:id/approve` — 403 if card not in scope
- `POST /api/queue/:id/modify` — 403 if card not in scope
- `POST /api/queue/:id/reject` — 403 if card not in scope

### Phase 1 dev mode

Until spec 043 OAuth ships (Week 4 same window), pulse-api uses a dev-mode JWT injector that reads `X-Dev-User-Id` header (front-end sends current user id) and synthesizes claims from hardcoded role assignments. **DEV-only fallback** — production builds reject requests without real JWT. Pattern matches Action Queue `demo_actions.ts` fallback approach (watched concern #23 cutover tracking applies).

### 403 response format

```json
{
  "error": "insufficient_scope",
  "required_role": "admin",
  "user_role": "rm",
  "message": "This action requires admin role."
}
```

Front-end surfaces 403s via toast notification: "You don't have access to this resource."

---

## 8. Demo character role assignments (hardcoded Phase 1)

Added to `demo_characters.ts`:

```typescript
export type UserRole = 'rm' | 'manager' | 'executive' | 'admin';

export interface DemoUser {
  id: string;
  displayName: string;
  email: string; // for Phase 1B OAuth simulation
  role: UserRole;
  rmId?: string; // for RM role
  managerId?: string; // for Manager role
  avatarInitials: string;
}

export const DEMO_USERS: DemoUser[] = [
  // Executives (note: Iffi on edgeonline.co per operator-confirmed canonical;
  // all other users on onedge.co. Spec 043 OAuth must cover both domains via
  // single Google Workspace with multi-domain configuration.)
  { id: 'iffi-wahla', displayName: 'Iffi Wahla', email: 'iffi.wahla@edgeonline.co', role: 'executive', avatarInitials: 'IW' },
  { id: 'eddy-chen', displayName: 'Eddy Chen', email: 'eddy.chen@onedge.co', role: 'executive', avatarInitials: 'EC' },
  // Managers
  { id: 'sarah-hooper', displayName: 'Sarah Hooper', email: 'sarah.hooper@onedge.co', role: 'manager', managerId: 'sarah-hooper', avatarInitials: 'SH' },
  { id: 'muhammad-ibrahim', displayName: 'Muhammad Ibrahim', email: 'muhammad.ibrahim@onedge.co', role: 'manager', managerId: 'muhammad-ibrahim', avatarInitials: 'MI' },
  // RMs
  { id: 'sidra-zia', displayName: 'Sidra Zia', email: 'sidra.zia@onedge.co', role: 'rm', rmId: 'sidra-zia', avatarInitials: 'SZ' },
  { id: 'sajjal-shaheedi', displayName: 'Sajjal Shaheedi', email: 'sajjal.shaheedi@onedge.co', role: 'rm', rmId: 'sajjal-shaheedi', avatarInitials: 'SS' },
  { id: 'yozeline-candia', displayName: 'Yozeline Candia', email: 'yozeline.candia@onedge.co', role: 'rm', rmId: 'yozeline-candia', avatarInitials: 'YC' },
  { id: 'ameer-ali', displayName: 'Ameer Ali', email: 'ameer.ali@onedge.co', role: 'rm', rmId: 'ameer-ali', avatarInitials: 'AA' },
  { id: 'mubeen-sohail', displayName: 'Mubeen Sohail', email: 'mubeen.sohail@onedge.co', role: 'rm', rmId: 'mubeen-sohail', avatarInitials: 'MS' },
  { id: 'akash-tahir', displayName: 'Akash Tahir', email: 'akash.tahir@onedge.co', role: 'rm', rmId: 'akash-tahir', avatarInitials: 'AT' },
  // Admin (functional alias, not a person; Phase 1 demo)
  { id: 'pulse-admin', displayName: 'Pulse Admin', email: 'admin@onedge.co', role: 'admin', avatarInitials: 'PA' },
];
```

**Total: 11 demo users across 4 roles.** All names + role mappings derived from canonical Path A character set; one additional Admin functional alias added for demo completeness.

### Email convention

- `{first}.{last}@onedge.co` for all real-person users **except** Iffi Wahla.
- **Iffi Wahla on `edgeonline.co` domain** (operator-confirmed Session 19 late-late stream) — single executive on the secondary domain.
- `admin@onedge.co` for Pulse Admin (functional alias, not a person).
- Spec 043 OAuth Week 4 must configure Google Workspace to cover **both** `onedge.co` AND `edgeonline.co` domains under a single SSO identity provider (standard multi-domain Workspace configuration; no additional spec 043 scope change required). Alternative: separate IdP per domain (more setup; not recommended).

---

## 9. Settings panel — read-only role topology (Phase 1A; Hybrid disposition)

### Route + access

`/settings/users` — Admin-only. Route guard enforces.

### Composition

Three-column workspace (consistent with Per-Account View + Executive View patterns):

**Left column (~280px):** Role filter chips (All / Executive / Manager / RM / Admin). Click filters the main list.

**Main column:** User list table.

| Avatar | Name | Email | Role | Scope (accounts) |
|---|---|---|---|---|
| IW | Iffi Wahla | iffi@onedge.co | Executive | 14 (full org) |
| EC | Eddy Chen | eddy@onedge.co | Executive | 14 (full org) |
| SH | Sarah Hooper | sarah@onedge.co | Manager | 7 (team scope) |
| MI | Muhammad Ibrahim | muhammad@onedge.co | Manager | 7 (team scope) |
| SZ | Sidra Zia | sidra@onedge.co | RM | 3 |
| SS | Sajjal Shaheedi | sajjal@onedge.co | RM | 3 |
| YC | Yozeline Candia | yozeline@onedge.co | RM | 1 |
| AA | Ameer Ali | ameer@onedge.co | RM | 5 |
| MS | Mubeen Sohail | mubeen@onedge.co | RM | 1 |
| AT | Akash Tahir | akash@onedge.co | RM | 1 |
| PA | Pulse Admin | admin@onedge.co | Admin | 14 (full org) |

Counts derived from `deriveAccountScope()` per user. No hardcoded counts.

**Right column (~320px):** Selected-user detail panel (opens when user row clicked). Shows:
- User display name + email + role + avatar
- Account scope list (full list of in-scope account names)
- Permission summary ("Can access: Action Queue, Per-Account View, Constellation, Executive View, Settings panel" — derived from permission matrix)
- "Change role" CTA with placeholder modal: "Role assignment workflow coming in Phase 2. Contact Pulse support to change role assignments."

### Phase 1A → 1B transition

Phase 1B (post-Phase-2 user management UI work): "Change role" CTA opens functional role-change modal with confirmation + audit log entry + PATCH `/api/users/:id` to pulse-api. Same Settings panel UI; just the modal becomes functional.

---

## 10. Demo flow stories (for stakeholder review)

Three demo stories spec 042 enables:

### Story A — RM Yozeline opens her view

- Logs in as `yozeline-candia` (Phase 1: dev-mode user switcher; Phase 1B post-spec-043: real Google SSO)
- Default route: `/actions` (her queue — empty or 1-2 cards based on Manhattan Restorative state)
- Navigates to `/constellation` — sees her single account (Manhattan), her RM node, Sarah's manager node, no DHR or Sajjal cluster
- Capacity overlay: empty (her score doesn't warrant)
- Tier-jump overlay: surfaces (Manhattan watch→at-risk is in her scope)
- Tries to navigate to `/executive` — RoleGuard redirects to `/actions`
- Tries to navigate to `/accounts/dhr-health-clinics` — sub-route guard redirects to `/actions`

### Story B — Manager Sarah opens her view

- Logs in as `sarah-hooper`
- Default route: `/actions` (her team's queue — Sidra/Sajjal/Yozeline cards)
- `/constellation` shows team scope: 7 accounts (Sidra's 3 + Sajjal's 3 + Yozeline's 1) + 3 RMs + herself + peer manager Muhammad (showing as inactive/dim node since out-of-team)
- Capacity overlay: surfaces Sajjal (in-team) as top-loaded
- Tier-jump overlay: surfaces Manhattan
- Cluster pattern overlay: surfaces DHR + Manhattan pattern (both in-scope)
- No Executive View access
- No Settings access

### Story C — Executive Iffi opens his view

- Logs in as `iffi-wahla`
- Default route: `/executive` (the surface designed for him)
- Sees full Executive View with three-column agentic workspace, all asks, all stats
- Navigates to `/constellation` — full org scope, all 3 overlays, all 14 accounts
- Can navigate to any `/accounts/:id` read-only
- No `/actions` access (executives don't approve)
- No Settings access

Admin role is technical (Phase 1 demo doesn't surface Admin flow prominently; Admin used to demonstrate the Settings panel exists).

---

## 11. Tests

### Front-end (Vitest)

- `accountScope.test.ts` — `deriveAccountScope()` correctness per role: RM returns own book, Manager returns team scope, Executive/Admin return full org, unknown role throws
- `RoleGuard.test.tsx` — allowed role renders children; disallowed role navigates to fallback
- `AuthContext.test.tsx` — provider supplies user + scope; useAuth hook returns values
- `Constellation.test.tsx` (extension) — scoped user sees only in-scope nodes; existing tests still pass with scope undefined
- `rm_capacity_composer.test.ts` (extension) — `accountScope` parameter filters working set; existing tests still pass with scope undefined
- `escalation_tier_jump_composer.test.ts` (extension) — same
- `cluster_pattern_composer.test.ts` (extension) — same; patterns partially in scope filtered out entirely
- `PerAccountView.test.tsx` (extension) — out-of-scope account id redirects; in-scope renders
- `SettingsUsersPanel.test.tsx` — renders user list, scope counts correct, role filter chips work, selected-user detail panel opens
- `App.test.tsx` (extension) — route guards enforce; default route per role correct

### Back-end (pytest)

- `test_rbac_scope_middleware.py` — middleware applies correct filter per role; 403 on missing/invalid claim; Admin bypasses filter
- `test_queue_endpoint_scope.py` — `GET /api/queue` filtered per role; out-of-scope mutations 403
- `test_account_endpoint_scope.py` — `GET /api/accounts/:id` 403 if out of scope (RM/Manager); Executive bypasses
- `test_executive_endpoint_access.py` — Executive + Admin only
- `test_settings_endpoint_access.py` — Admin only

### Estimated test count

~25-30 new tests (15-18 front-end Vitest, 10-12 back-end pytest). Front-end test total grows from 65 to ~80-83.

---

## 12. Definition of Done

- ✅ All 4 roles defined with permission matrix in code (`src/lib/rbac/roles.ts`)
- ✅ `deriveAccountScope()` pure function landed + tested
- ✅ `AuthContext` provider wraps app; `useAuth()` hook available
- ✅ `RoleGuard` component implemented; all 5 protected routes wrapped
- ✅ Per-Account View sub-route guard enforces in-scope check (Executive exception)
- ✅ All three Constellation overlay composers accept + honor `accountScope` parameter (watched concern #26 closed)
- ✅ Action Queue filters by scope (existing surface, extended)
- ✅ Default route per role correct (RM → `/actions`, Executive → `/executive`, etc)
- ✅ Pulse-api middleware applies scope filter to all read endpoints; mutation endpoints 403 on out-of-scope
- ✅ Dev-mode JWT injector reads `X-Dev-User-Id` header (Phase 1 fallback before spec 043 OAuth)
- ✅ 11 demo users hardcoded in `demo_characters.ts` with correct role assignments
- ✅ Settings panel `/settings/users` renders user list with scope counts; selected-user detail panel works; role-change CTA shows placeholder
- ✅ User switcher in app shell (dev-only, gated behind `import.meta.env.DEV` per posture rule #44) lets demo operator switch between demo users
- ✅ All three demo stories (A/B/C) walkable end-to-end on `localhost:5173`
- ✅ 25-30 new tests green
- ✅ Existing 65 tests still pass (no regressions)
- ✅ Build green, lint clean
- ✅ Branch: all commits on `dz-001` per §4.22
- ✅ Spec doc updated with closure section + carry-forward concerns

---

## 13. Watched concerns carry-forward

Likely new watched concerns to emerge during implementation (will file as they appear):

- **Pulse-api `users` table schema** — Phase 1 hardcoded; pulse-api will need a real `users` table Phase 2 with role + scope_override columns. Spec 042 doesn't create this table; spec 043 OAuth may, or it lands Phase 2.
- **Audit log gap on role changes** — Phase 1 doesn't audit role changes (because there are no role changes). Phase 2 functional Settings panel must add audit entries; tracked separately.
- **Multi-tenant scope isolation** — spec 042 is single-tenant. White-label deployments will need tenant-scoped role assignment. Phase 2.
- **Dev user-switcher UI affordance** — `import.meta.env.DEV` gates a user switcher; production hides it. If Phase 2 surfaces a "switch user" affordance for legitimate admin impersonation use cases, design pattern needs revisit.
- **Multi-domain SSO (NEW Session 19 late-late stream)** — Spec 043 OAuth must support both `onedge.co` and `edgeonline.co` domains via single Google Workspace multi-domain configuration. Operator action item for spec 043 kickoff: confirm Google Workspace covers both domains, or coordinate IdP setup. Cross-reference §15.

---

## 14. Implementation sequence (recommended Claude Code halts)

**Step 1 — Types + scope derivation (~30 min):**
- `src/lib/rbac/types.ts` (UserRole, AccountScope)
- `src/lib/rbac/accountScope.ts` (deriveAccountScope + tests)
- `demo_characters.ts` extension (DEMO_USERS + DemoUser interface)
- HALT for PM review of derived scope counts (verify all 11 users return expected scope sizes)

**Step 2 — AuthContext + RoleGuard (~45 min):**
- `src/lib/auth/AuthContext.tsx` + provider in App.tsx
- `src/lib/auth/RoleGuard.tsx` + tests
- Dev-mode user switcher in app shell (gated `import.meta.env.DEV`)
- HALT for PM visual ratification of user switcher + role-based redirect on login

**Step 3 — Route guards + sub-route enforcement (~30 min):**
- App.tsx route tree wrapping
- Per-Account View sub-route guard (Executive exception)
- Tests
- HALT for PM verification of all 5 protected routes

**Step 4 — Constellation overlay composer scope propagation (~45 min):**
- Update rm_capacity_composer, escalation_tier_jump_composer, cluster_pattern_composer to accept accountScope
- Update tests
- Verify scoped user (Yozeline) sees only in-scope overlay references
- HALT for PM verification (closes watched concern #26)

**Step 5 — Action Queue + Per-Account View scope filtering (~45 min):**
- Action Queue filter logic updated
- Per-Account View access checks (Executive exception)
- Tests
- HALT for PM visual ratification per demo story A (Yozeline) and B (Sarah)

**Step 6 — Pulse-api middleware + dev-mode JWT injector (~60 min):**
- `pulse-api/middleware/rbac_scope.py`
- `pulse-api/middleware/dev_jwt_injector.py` (gated behind ENV flag)
- Apply middleware to all read + mutation endpoints
- Tests
- HALT for PM verification (curl against dev endpoints with different X-Dev-User-Id headers; verify 403s + filtered responses)

**Step 7 — Settings panel `/settings/users` (~45 min):**
- `src/features/settings/SettingsUsersPanel.tsx` (three-column workspace)
- Route + role guard
- Tests
- HALT for PM visual ratification

**Step 8 — Demo flow end-to-end + polish + DoD verification (~30 min):**
- Walk through demo stories A/B/C
- Run full test suite (target ~80-83 vitest + ~10-12 pytest)
- Update spec doc with closure section
- HALT for PM ratification + spec 042 close

**Total estimated:** 4.5-5.5 hours Claude Code execution across 8 halts.

---

## 15. Cross-spec coordination

- **Spec 041 closure (`accountScope` prop interface):** Already wired; spec 042 extends to overlay composers.
- **Spec 043 OAuth:** Real JWT claims replace dev-mode header injector. Same middleware contract. **Multi-domain SSO requirement (NEW per Session 19 late-late stream operator confirmation):** spec 043 must configure Google Workspace to cover both `onedge.co` AND `edgeonline.co` domains under a single SSO identity provider (Iffi Wahla is on `edgeonline.co`; all other users on `onedge.co`).
- **Spec 044-047 Layer 8 surfaces:** Will need role guards (likely Admin-only for Signal Performance + Outcome tracking surfaces). Spec 042 establishes the RoleGuard + AccountScope pattern those specs will reuse.
- **Pulse-api deploy:** Middleware deploys with rest of pulse-api; dev fallback removed at production cutover.

---

## 16. Branch discipline

All work lands on `dz-001` per §4.22. Branch directive prominent in every Claude Code prompt for spec 042 execution.

Merge to main awaits operator authorization: "audit `dz-001` → merge with [developer's branch] → merge with main."

---

*End of Spec 042 — Role-Based Access Control.*
*PM-drafted Session 19 late-late stream (2026-05-22). Lands on `dz-001` once ratified + audit cleared.*

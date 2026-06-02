# Spec 042 — Role-Based Access Control (RBAC)

**Status:** ✅ **CLOSED 2026-05-22** (Session 19 late-late stream extended). All 8 implementation steps + 4 follow-up commits landed on `dz-001`; DoD verified (§17 close-out); demo Stories A/B/C walkable end-to-end. Watched concern #26 (overlay composer scope filtering) closed by this spec. Carry-forward: #36 (Phase-1B pulse-api endpoint enforcement), #37 (403 detail-format normalization), #38 (capacity interpretation-B at scale), #39 (badge semantics Phase 2), multi-domain SSO (spec 043). Merge to `main` awaits separate operator authorization (§16). Phase-1A delivers scoping enforcement + viewable role topology; Phase-1B (post-pulse-api Week 4 cutover) swaps fixtures for real signal data + LLM-composed prose. — _Originally ratified per pre-spec audit (memo `00_research/audits/pre_spec_042_rbac_audit.md`, commit `510eae0`) + Executive workload visibility extension (operator-ratified Option D)._
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

### 3.3 Executive workload visibility (per operator catch Session 19 late-late stream extended)

Executive role is blocked from `/actions` per permission matrix (the RM queue is RM/Manager workspace, not executive surface). Executive visibility into RM workload delivers through:

1. **RM capacity imbalance overlay** (existing — spec 041 Step 6). Surfaces top-loaded RM at org level.
2. **Team workload panel on Executive View** (NEW — per spec 042 §6.6 below). Per-RM queue depth + approvals this week + throughput indicator. At-a-glance team-wide workload texture.
3. **Constellation RM node hover drill-down** (NEW — extension to spec 041 Step 4 hover tooltips). Hover an RM node shows workload metrics plus existing ARR + account count.

NOT delivered through Action Queue read-only access — `/actions` is RM workspace surface; executive context is delivered through curated executive surfaces.

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
    case 'manager': {
      // Manager sees all accounts owned by RMs they manage
      const teamRmIds = DEMO_RMS
        .filter(rm => rm.managerId === userId)
        .map(rm => rm.id);
      return DEMO_ACCOUNTS
        .filter(a => teamRmIds.includes(a.rmId))
        .map(a => a.id);
    }
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

### AuthContext supersedes useSession.Role (A3 disposition)

Per audit A3 disposition: `useSession.Role` (currently used by Header + AdminLayout) is SUPERSEDED by AuthContext. Spec 042 Step 2 includes the migration:

1. Header refactored to use `useAuth()` instead of `useSession()`
2. AdminLayout refactored to use `useAuth()` instead of `useSession()`
3. `useSession.Role` removed from codebase by end of spec 042
4. AuthContext.user.role is single source of truth for user role going forward
5. Spec 043 OAuth hydrates AuthContext directly from JWT claims (no useSession migration needed Phase 1B)

Migration is ~30 min Claude Code work; folded into Step 2.

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
      <QueueList />
    </RoleGuard>
  } />
  <Route path="/accounts/:id" element={
    <RoleGuard allowedRoles={['rm', 'manager', 'executive', 'admin']}>
      <AccountScopeGuard executiveBypass>
        <PerAccountView />
      </AccountScopeGuard>
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

### AccountScopeGuard sub-route guard (Phase 1A wrapper pattern)

Per audit H1 disposition: `/accounts/:id` currently renders a Placeholder (spec 037 PerAccountView is unbuilt). To preserve demo Story A's "Yozeline blocked from DHR" demonstration without waiting for spec 037 build, spec 042 lands a lightweight wrapper component at the route level:

```typescript
interface AccountScopeGuardProps {
  executiveBypass?: boolean; // Executive role bypasses scope check (read-only navigation)
  children: ReactNode;
}

export function AccountScopeGuard({ executiveBypass = false, children }: AccountScopeGuardProps) {
  const { user, accountScope } = useAuth();
  const { id } = useParams();

  if (executiveBypass && user.role === 'executive') return <>{children}</>;
  if (executiveBypass && user.role === 'admin') return <>{children}</>;
  if (accountScope && !accountScope.includes(id as DemoAccountId)) {
    return <Navigate to="/actions" replace />;
  }
  return <>{children}</>;
}
```

When spec 037 builds the real PerAccountView component, AccountScopeGuard can either be folded inside PerAccountView or kept as the route wrapper — implementation choice at that time. For Phase 1A, the wrapper pattern intercepts before the Placeholder renders.

> **Note (audit H1):** `ActionQueueView` was a drafting placeholder; the actual Action Queue component is `QueueList` (spec 035). All route references use `QueueList`.

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

### Composer signatures (corrected per audit A1)

**`composeCapacityImbalance()` extension** (actual shipped name, not "rm_capacity_composer.ts"):

```typescript
export function composeCapacityImbalance(
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

**`composeEscalationTierJumps()` extension:**

```typescript
export function composeEscalationTierJumps(
  events: typeof DEMO_TIER_JUMP_EVENTS,
  accountScope?: AccountScope,
): EscalationTierJumpCard[] {
  const scopedEvents = accountScope
    ? events.filter(e => accountScope.includes(e.accountId))
    : events;
  // ... existing logic operates on scopedEvents
}
```

**Cluster pattern (inline filter, not a composer extension):**

Cluster-pattern handling lives inline within `ClusterPatternOverlay` (filtering `DEMO_PATTERNS` directly), not in a separate composer module (no `cluster_pattern_composer.ts` exists). The inline filter applies the same partial-scope-pattern filter-out semantics: if any of a pattern's `support_account_ids` is out of scope, the pattern is not surfaced to that user.

```typescript
// inside ClusterPatternOverlay component
const { accountScope } = useAuth();
const scopedPatterns = DEMO_PATTERNS.filter(pattern => {
  if (!accountScope) return true; // unscoped = show all
  return pattern.support_account_ids.every(id => accountScope.includes(id));
});
```

§11 test naming updated correspondingly:
- `composeCapacityImbalance` covered by the existing `rm_capacity_composer.test.ts` (extended with `accountScope` cases)
- `composeEscalationTierJumps` covered by the existing `escalation_tier_jump_composer.test.ts` (extended)
- Cluster pattern tested at `ClusterPatternOverlay.test.tsx` (overlay level), not as a standalone composer

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

## 6.5. Team workload composer (Executive workload visibility — Edit 11)

New composer module: `src/features/executive/composers/team_workload_composer.ts`

```typescript
export interface TeamWorkloadRow {
  rmId: string;
  rmName: string;
  avatarInitials: string;
  pendingCount: number;        // open cards in Action Queue
  approvedThisWeek: number;    // cards approved in last 7d
  modifiedThisWeek: number;
  rejectedThisWeek: number;
  throughputIndicator: 'rising' | 'steady' | 'declining' | 'flat';
  combinedLoad: number;         // sort key (pending + throughput adjustment)
}

export function composeTeamWorkload(
  rms: typeof DEMO_RMS,
  actions: typeof DEMO_ACTIONS, // existing dev-only Action Queue fixture
  accountScope?: AccountScope,  // for Manager-scoped workload view (not used by Executive who sees all)
): TeamWorkloadRow[] {
  // For each RM in scope:
  //   - pending = actions where rmId matches AND status === 'pending'
  //   - approvedThisWeek = actions where rmId matches AND status === 'approved' AND within 7d
  //   - modifiedThisWeek, rejectedThisWeek = same pattern
  //   - throughputIndicator: derive from approval rate trend over last 14 days
  //     (Phase 1: heuristic based on approvedThisWeek vs averageThisMonth; Phase 1B: real signal-derived)
  //   - combinedLoad = pendingCount + (approvedThisWeek * 0.5)  // weighted heuristic; sort descending
  // Returns sorted by combinedLoad descending. All counts derived from DEMO_ACTIONS fixture (Phase 1A);
  // Phase 1B reads real pulse-api data.
}
```

Test file: `team_workload_composer.test.ts`. Verify scope filtering, derived counts match expected per-RM values from fixture.

**Phase 1A → 1B transition:** Composer reads `DEMO_ACTIONS` fixture currently; pulse-api Week 4 cutover swaps to real action data via the existing `Caller` + `visible_rm_ids` pattern. No composer-signature change at cutover.

---

## 6.6. Executive View Team workload panel (Edit 11)

New panel on Executive View, positioned BETWEEN the asks band ("What I'd ask of you · 3 this week") and the "Book in numbers" bottom strip. Honors §4.20 (every section surfaces an agentic decision) by giving the executive a workload-distribution-at-a-glance to support team interventions.

### Composition

```
┌─────────────────────────────────────────────────────────┐
│  Team workload                                          │
├─────┬─────────────────┬──────┬──────────┬──────────────┤
│ Av  │ Name            │ Pend │ Approved │ Throughput    │
├─────┼─────────────────┼──────┼──────────┼──────────────┤
│ SS  │ Sajjal Shaheedi │  8   │   12     │  ↑ rising     │
│ SZ  │ Sidra Zia       │  3   │    9     │  → steady     │
│ AA  │ Ameer Ali       │  4   │    7     │  → steady     │
│ YC  │ Yozeline Candia │  1   │    3     │  ↑ rising     │
│ MS  │ Mubeen Sohail   │  0   │    2     │  → flat       │
│ AT  │ Akash Tahir     │  1   │    1     │  → flat       │
└─────┴─────────────────┴──────┴──────────┴──────────────┘
```

(Numbers in mockup are illustrative; actual values derived from `composeTeamWorkload()`.)

Per-row composition:
- Avatar (24×24 rounded square; chip-warning bg if pendingCount >= 6, otherwise neutral)
- Name (13px medium)
- Pending count (numeric; chip-warning text-color if >= 6)
- Approved this week (numeric; secondary text)
- Throughput indicator: arrow + label (↑ rising, → steady, ↓ declining, → flat) with corresponding text color (good-on-brand / secondary / risk-on-brand / tertiary)

Sortable by clicking column header (default: combinedLoad descending). Click an RM row → routes to `/constellation?rm=<rm-id>` (focuses Constellation on that RM's cluster — uses the existing spec 041 Step 4 deep-link pattern).

### Agentic decision the panel surfaces

"Sajjal is at 8 pending + rising throughput → either intervention warranted (Sarah pairs with him) OR he's handling the load (let him operate). Sidra at 3 pending + steady → no intervention needed. Yozeline at 1 pending + rising → ramp signal worth recognizing." The panel makes a per-RM decision possible without leaving the Executive View.

---

## 6.7. Constellation RM node hover drill-down (Edit 11)

Extend the existing spec 041 Step 4 hover tooltip on RM nodes to surface workload metrics in addition to ARR + account count.

### Existing hover content (spec 041 Step 4)
- RM name
- Book ARR (e.g., "$760K")
- Account count (e.g., "3 accounts")

### NEW additional content (Edit 11 — for Executive + Admin roles only; RM/Manager roles see existing tooltip)
- Pending cards (e.g., "8 pending")
- Approved this week (e.g., "12 approved this week")
- Throughput indicator (e.g., "↑ rising")

### Behavior
- Hover tooltip extension shows for Executive + Admin roles.
- RM + Manager roles see the existing tooltip (their scope already gives them direct queue access; redundant in tooltip).
- Same `composeTeamWorkload()` data source as the Executive View Team workload panel; no duplicate composer.

### Implementation
- Extend the existing hover tooltip component to accept optional workload props.
- AuthContext role check determines whether to render the workload section.
- Workload row data passed from the parent Constellation component (which already reads `composeTeamWorkload()` for any executive-role rendering).

---

## 7. Pulse-api backend touchpoints (defense in depth — narrowed per audit)

Per audit H2 disposition: spec 042 originally proposed a new middleware (`pulse-api/middleware/rbac_scope.py`) targeting endpoints (`/api/queue|constellation|executive|accounts`). Audit revealed:

1. Scope enforcement **already ships** in `api/actions.py` via the `Caller` model + `visible_rm_ids` filtering + 403 responses (spec 031, exercised by `test_actions_api_db.py`).
2. Three of the four proposed endpoints (`/api/constellation`, `/api/executive`, `/api/accounts`) do not exist — those surfaces are client-side in Phase 1A; pulse-api endpoints land Phase 1B Week 4 cutover.
3. The dev-mode `X-Dev-User-Id` JWT injector pattern is redundant — the existing `X-User-*` header convention from spec 031 is the established Phase 1A pattern.

### Backend changes for spec 042 (narrowed)

Single backend touchpoint:

**`api/actions.py` — Extend `Caller` model to add `executive` role:**
- Current `Caller.role` enum includes `rm | manager | admin`; add `executive`.
- `visible_rm_ids` derivation for executive: returns all RM IDs (full org scope, matching `deriveAccountScope` for executive role).
- 403 logic unchanged; existing test pattern in `test_actions_api_db.py` extended with executive-role cases.
- Note: per the permission matrix, executives are blocked from `/actions` at the front-end route guard. The backend executive scope is "all" for the Phase-1B endpoints that will reuse `Caller` (Constellation/Executive/Per-Account); the queue endpoints remain RM/Manager/Admin in practice.

### Backend deferred to Phase 1B (Week 4 pulse-api cutover)

When Constellation, Executive View, and Per-Account View wire to real pulse-api endpoints (not yet built), RBAC enforcement extends to those endpoints using the same `Caller` model + `visible_rm_ids` pattern. Filed as watched concern #36 for Week 4 coordination.

### Defense-in-depth posture (Phase 1A)

- **Front-end:** route guards + AccountScopeGuard + accountScope filtering through composers + AuthContext (this spec).
- **Back-end:** existing `Caller`-based 403 enforcement on `/actions*` (spec 031; extended here with executive role).
- **Phase 1B addition:** new pulse-api endpoints for Constellation/Executive/Per-Account inherit `Caller` enforcement (Week 4).

### Header convention

Front-end sends `X-User-Id`, `X-User-Role` headers (matching the spec 031 established pattern) to pulse-api. Pulse-api populates `Caller` from headers in Phase 1A; real JWT claims replace headers Phase 1B once spec 043 OAuth deploys.

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
| IW | Iffi Wahla | iffi.wahla@edgeonline.co | Executive | 14 (full org) |
| EC | Eddy Chen | eddy.chen@onedge.co | Executive | 14 (full org) |
| SH | Sarah Hooper | sarah.hooper@onedge.co | Manager | 7 (team scope) |
| MI | Muhammad Ibrahim | muhammad.ibrahim@onedge.co | Manager | 7 (team scope) |
| SZ | Sidra Zia | sidra.zia@onedge.co | RM | 3 |
| SS | Sajjal Shaheedi | sajjal.shaheedi@onedge.co | RM | 3 |
| YC | Yozeline Candia | yozeline.candia@onedge.co | RM | 1 |
| AA | Ameer Ali | ameer.ali@onedge.co | RM | 5 |
| MS | Mubeen Sohail | mubeen.sohail@onedge.co | RM | 1 |
| AT | Akash Tahir | akash.tahir@onedge.co | RM | 1 |
| PA | Pulse Admin | admin@onedge.co | Admin | 14 (full org) |

Email convention: `{first}.{last}@onedge.co` for everyone except Iffi Wahla on `edgeonline.co` (single executive on secondary domain per Session 19 late-late stream extended operator confirmation). Pulse Admin = `admin@onedge.co` functional alias. Counts derived from `deriveAccountScope()`.

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
- Tries to navigate to `/accounts/dhr-health-clinics` — AccountScopeGuard redirects to `/actions`

### Story B — Manager Sarah opens her view

- Logs in as `sarah-hooper`
- Default route: `/actions` (her team's queue — Sidra/Sajjal/Yozeline cards)
- `/constellation` shows team scope: 7 accounts (Sidra's 3 + Sajjal's 3 + Yozeline's 1) + 3 RMs + herself + peer manager Muhammad (showing as inactive/dim node since out-of-team)
- Capacity overlay: surfaces Sajjal (in-team) as top-loaded
- Tier-jump overlay: surfaces Manhattan
- Cluster pattern overlay: surfaces DHR + Manhattan pattern (both in-scope)
- No Executive View access
- No Settings access

### Story C — Executive Iffi opens his view (REVISED Edit 11)

- Logs in as `iffi-wahla`
- Default route: `/executive` (the surface designed for him)
- Sees full Executive View:
  - Hero Card with three-column agentic workspace + 2×2 pulse-facts
  - "What I'd ask of you · 3 this week" asks band
  - **NEW: Team workload panel** showing 6 RMs sorted by combined load — Sajjal at top (8 pending + rising throughput), Akash at bottom (1 pending + flat)
  - "Book in numbers" bottom strip
- Identifies Sajjal as the RM needing attention → clicks Sajjal's row → routes to `/constellation?rm=sajjal-shaheedi`
- Constellation focuses on Sajjal's cluster + zoom level
- Hovers Sajjal's RM node → tooltip shows: book ARR ($760K) + account count (3) + **NEW: 8 pending + 12 approved this week + ↑ rising**
- Decides intervention warranted: navigates to Sajjal's accounts via Per-Account View read-only navigation to understand context before suggesting Sarah pair with him
- No Action Queue access (executives don't approve; that's RM/Manager workspace)
- Returns to Executive View; full visibility into team workload without touching the RM action surface

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

### Estimated test count (revised per audit + Executive workload extension)

- Vitest (front-end): 23-27 tests (was 15-18 — A3 Supersede adds Header + AdminLayout migration tests; Edit 11 adds Team workload composer + Executive View panel + Constellation RM hover tests)
- Pytest (back-end): 5-7 tests (was 10-12 — H2 scope-down to `Caller.executive` extension only)
- **Total: 28-34 new tests** (was 25-30)
- Front-end test total grows from 65 to ~88-92.

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
- ✅ User switcher in app shell (dev-only, gated behind `import.meta.env.DEV` per §6 posture rule #44) lets demo operator switch between demo users
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
- **Phase 1B pulse-api endpoint build (NEW Session 19 late-late stream extended audit)** — When Constellation, Executive View, and Per-Account View wire to real pulse-api endpoints (Week 4 cutover), RBAC enforcement extends to those endpoints using the same `Caller` model + `visible_rm_ids` pattern already established in `api/actions.py`. Filed for Week 4 coordination (watched concern #36).

---

## 14. Implementation sequence (recommended Claude Code halts)

**Step 1 — Types + scope derivation (~30 min):**
- `src/lib/rbac/types.ts` (UserRole, AccountScope)
- `src/lib/rbac/accountScope.ts` (deriveAccountScope + tests)
- `demo_characters.ts` extension (DEMO_USERS + DemoUser interface)
- HALT for PM review of derived scope counts (verify all 11 users return expected scope sizes)

**Step 2 — AuthContext + RoleGuard + `useSession.Role` supersession migration (~75 min; A3 Supersede):**
- `src/lib/auth/AuthContext.tsx` + provider in App.tsx
- `src/lib/auth/RoleGuard.tsx` + tests
- Migrate Header + AdminLayout from `useSession()` to `useAuth()`; remove `useSession.Role`
- Dev-mode user switcher in app shell (gated `import.meta.env.DEV`)
- HALT for PM visual ratification of user switcher + role-based redirect on login

**Step 3 — Route guards + AccountScopeGuard sub-route enforcement (~30 min):**
- App.tsx route tree wrapping
- `AccountScopeGuard` wrapper on `/accounts/:id` (Executive bypass)
- Tests
- HALT for PM verification of all 5 protected routes

**Step 4 — Constellation overlay composer scope propagation (~45 min):**
- Extend `composeCapacityImbalance` + `composeEscalationTierJumps` to accept `accountScope`; add inline `DEMO_PATTERNS` scope filter in `ClusterPatternOverlay`
- Update tests
- Verify scoped user (Yozeline) sees only in-scope overlay references
- HALT for PM verification (closes watched concern #26)

**Step 5 — Action Queue + Per-Account View scope filtering (~45 min):**
- Action Queue filter logic updated
- Per-Account View access checks (Executive exception) via AccountScopeGuard
- Tests
- HALT for PM visual ratification per demo story A (Yozeline) and B (Sarah)

**Step 6 — `Caller.executive` extension in `api/actions.py` + `test_actions_api_db.py` (~30 min; H2 scope-down):**
- Add `executive` to the `Caller` role enum + `visible_rm_ids` (full org scope)
- Extend `test_actions_api_db.py` with executive-role cases
- HALT for PM verification (curl against `/actions*` with different `X-User-Role` headers; verify 403s + filtered responses)

**Step 7 — Settings panel `/settings/users` (~45 min):**
- `src/features/settings/SettingsUsersPanel.tsx` (three-column workspace)
- Route + role guard
- Tests
- HALT for PM visual ratification

**Step 8 — Executive workload visibility (NEW; ~75-90 min; Edit 11):**
- `team_workload_composer.ts` + tests (`composeTeamWorkload`)
- Executive View Team workload panel (between asks band + Book-in-numbers strip)
- Constellation RM node hover extension (Executive/Admin only)
- HALT for PM visual ratification per demo story C (Iffi)

**Step 9 — Demo flow end-to-end + polish + DoD verification (~30 min):**
- Walk through demo stories A/B/C
- Run full test suite (target ~88-92 vitest + ~5-7 pytest)
- Update spec doc with closure section
- HALT for PM ratification + spec 042 close

**Total estimated:** ~6-7 hours Claude Code execution across 9 halts (was 4.5-5.5h; Edit 11 adds ~75-90 min net new work).

---

## 15. Cross-spec coordination

- **Spec 041 closure (`accountScope` prop interface):** Already wired; spec 042 extends to overlay composers.
- **Spec 043 OAuth:** Real JWT claims replace the `X-User-*` header convention from spec 031 + spec 042. Same `Caller` model contract on backend side. **Multi-domain SSO requirement (NEW per Session 19 late-late stream extended operator confirmation):** spec 043 must configure Google Workspace to cover both `onedge.co` AND `edgeonline.co` domains under a single SSO identity provider (Iffi Wahla is on `edgeonline.co`; all other users on `onedge.co`).
- **Spec 044-047 Layer 8 surfaces:** Will need role guards (likely Admin-only for Signal Performance + Outcome tracking surfaces). Spec 042 establishes the RoleGuard + AccountScope pattern those specs will reuse.
- **Pulse-api deploy:** Middleware deploys with rest of pulse-api; dev fallback removed at production cutover.

---

## 16. Branch discipline

All work lands on `dz-001` per §4.22. Branch directive prominent in every Claude Code prompt for spec 042 execution.

Merge to main awaits operator authorization: "audit `dz-001` → merge with [developer's branch] → merge with main."

---

## 17. Step-9 close-out + DoD verification (2026-05-22)

**Closed:** 2026-05-22 (Session 19 late-late stream extended), branch `dz-001`.

### Implementation history (all on `dz-001`)

8 implementation steps + 4 follow-up commits, all PM-ratified at each halt:

- **Step 1** — `types.ts` + `accountScope.ts` + `DEMO_USERS` (11 users).
- **Step 2** — `AuthContext` + `RoleGuard` + `useSession.Role` supersession (A3); `ApiCaller` shim; role-aware `filterDemoActions`.
- **Step 3** — route-tree guards + role-aware `defaultRouteForRole` fallback (HALT #1 resolution).
- **Step 4** + follow-up — overlay composer scope propagation; **interpretation B** (org-wide truth, scoped display) ratified (`d2c4cb5`).
- **Step 5** + 2 follow-ups — Action Queue + `/accounts` scope filtering; seeded 2 Sajjal cards + 2 approved cards; PulseBar badge counts scoped **pending** only; Status/Time filters replace the My-Queue/Overall toggle.
- **Step 6** — `Caller.executive` + `require_queue_caller` 403 (defense in depth); 6 backend tests, no DB.
- **Step 7** — `SettingsUsersPanel` (read-only role topology, Hybrid disposition); replaced the Step-3 placeholder.
- **Step 8** — `composeTeamWorkload` + Executive-View Team workload panel + Constellation RM-node tooltip extension (Edit 11).
- **Step 9** (this) — DoD verification, dev persona switcher (DoD gap closed), walkability tests, spec close-out.

### DoD verification (§12)

| # | DoD criterion | Status | Note |
|---|---|---|---|
| 1 | 4 roles + permission matrix in code | ✅ | In `src/lib/rbac/types.ts` (⚠️ §12 said `roles.ts`; actual is `types.ts` — cosmetic path delta). |
| 2 | `deriveAccountScope()` pure fn + tested | ✅ | `accountScope.ts` + `accountScope.test.ts`. |
| 3 | `AuthContext` provider + `useAuth()` | ✅ | Wraps app; exposes `user`/`accountScope`/`switchUser`. |
| 4 | `RoleGuard` on all 5 protected routes | ✅ | `/actions`, `/accounts/:id`, `/constellation`, `/executive`, `/settings/users`. |
| 5 | Per-Account sub-route guard (Exec exception) | ✅ | `AccountScopeGuard executiveBypass`. |
| 6 | 3 overlay composers honor `accountScope` | ✅ | Capacity + escalation composers + inline cluster filter. **Closes watched concern #26.** |
| 7 | Action Queue filters by scope | ✅ | `scopeAndRefineCards` (security) then `?rm=` (UX). |
| 8 | Default route per role | ✅ | `defaultRouteForRole` (RM/Manager/Admin → `/actions`, Executive → `/executive`). |
| 9 | Pulse-api `Caller.executive` + queue 403 | ✅ | `require_queue_caller` blocks Executive (structured detail). |
| 10 | Dev-mode auth header convention | ⚠️ | **Deviation (per audit H2):** uses the spec-031 `X-User-Id`/`X-User-Role` convention, **not** the §12 `X-Dev-User-Id` JWT injector (dropped as redundant). Intended. |
| 11 | 11 demo users hardcoded | ✅ | `DEMO_USERS` in `demo_characters.ts`. |
| 12 | Settings panel `/settings/users` | ✅ | List + scope counts + detail panel + Change-role Phase-2 placeholder. |
| 13 | Pulse-api scope on **all** read endpoints | 〜 | **Deferred to Phase-1B (#36):** only `/actions*` enforced in Phase-1A; Constellation/Executive/Per-Account endpoints don't exist yet (client-side fixtures), inherit `Caller` at Week-4 cutover. |
| 14 | Dev user-switcher (gated `import.meta.env.DEV`) | ✅ | **Gap found + closed in Step 9** — `switchUser` was exposed/tested but had no UI consumer; added a DEV-only persona `<select>` to the Header. |
| 15 | Stories A/B/C walkable end-to-end | ✅ | `demo_walkability.test.ts` (12 canvas-free cross-surface assertions). |
| 16 | New tests green | ✅ | ~168 new across Steps 1–9 (far exceeds the 28–34 §11 estimate). |
| 17 | Existing tests pass (no regressions) | ✅ | 241 front-end + 284 backend green. |
| 18 | Build green, lint clean | ✅ | `tsc -b && vite build` clean. |
| 19 | All commits on `dz-001` | ✅ | Per §4.22 / §16. |
| 20 | Spec doc closure section | ✅ | This §17 + CLOSED status line. |
| 21 | Edit 11: Team workload panel + Constellation hover | ✅ | Both shipped (Step 8). |

**Net:** all criteria met, with 2 documented deviations (#10 header convention per H2; #14 user-switcher gap closed this step) and 1 explicit deferral (#13 → Phase-1B / #36).

### Implementation deviations recorded across steps

- **Constellation tooltip** (Step 8, §6.7) implemented by extending the react-force-graph `nodeLabel` **string-builder** (`nodeTooltip`), not a JSX hover component with `hoveredRmId` state — the latter doesn't exist. Additive, unit-tested at the string level (canvas-free). No behavioral deviation from §6.7.
- **`DEMO_RMS`** carries `{id, name, managerId}` (no `displayName`/`avatarInitials`); `composeTeamWorkload` uses `rm.name` and derives initials from it (SS/SZ/YC/AA/MS/AT, matching `DEMO_USERS`).
- **`ApprovalStatus`** models `modified-approved` (not `modified`); `modifiedThisWeek`/`rejectedThisWeek` resolve to 0 in the Phase-1A fixture (only `pending`/`approved` present).

### Watched concerns carry-forward

- **#26 — overlay composer scope filtering** → **CLOSED by this spec** (DoD #6).
- **#36 — Phase-1B pulse-api endpoint enforcement** → open; Constellation/Executive/Per-Account endpoints inherit `Caller` + `visible_rm_ids` at Week-4 cutover.
- **#37 — 403 detail-format normalization** → open; pulse-api Week-4 cutover (structured vs string detail consistency).
- **#38 — capacity interpretation-B at production scale** → open; re-evaluate org-wide-truth/scoped-display threshold at real volume (Phase 2).
- **#39 — PulseBar badge semantics** → resolved Step-5 follow-up (scoped pending count); Phase-2 revisit if status taxonomy expands.
- **Multi-domain SSO** → spec 043 (Google Workspace must cover `onedge.co` + `edgeonline.co`).

### Phase-1A → Phase-1B transition

Phase-1A ships the enforcement skeleton + viewable role topology against canonical fixtures. Phase-1B (post-pulse-api **Week-4 cutover**) swaps `DEMO_ACTIONS`/`DEMO_*` fixtures for real signal data and LLM-composed prose via the established `Caller` + `visible_rm_ids` pattern — **no composer-signature changes** at cutover. Real OAuth (spec 043) hydrates `AuthContext` from JWT claims, replacing the dev persona switcher + `X-User-*` headers.

---

*End of Spec 042 — Role-Based Access Control. **CLOSED 2026-05-22.***
*PM-drafted Session 19 late-late stream (2026-05-22). All work on `dz-001`; merge to `main` awaits separate operator authorization.*

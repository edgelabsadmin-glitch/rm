# Edge Pulse — Feature Documentation

> **Product:** Relationship Intelligence for Relationship Managers  
> **Stack:** React (Vite) + FastAPI + Postgres (Supabase) + Salesforce + Claude AI  
> **Branch:** `feature/salesforce-support-integration`

---

## Table of Contents

1. [Authentication & Role-Based Access](#1-authentication--role-based-access)
2. [Account List Rail](#2-account-list-rail)
3. [Account Workspace](#3-account-workspace)
4. [Action Queue](#4-action-queue)
5. [Constellation View](#5-constellation-view)
6. [Executive Dashboard](#6-executive-dashboard)
7. [Outreach Submit Form](#7-outreach-submit-form)
8. [Support AI Chat](#8-support-ai-chat)
9. [Admin Panel](#9-admin-panel)
10. [User Management](#10-user-management)
11. [Salesforce Sync (Background)](#11-salesforce-sync-background)
12. [Backend API Reference](#12-backend-api-reference)

---

## 1. Authentication & Role-Based Access

### Roles

| Role | Description |
|---|---|
| `rm` | Relationship Manager — sees only their own book of accounts |
| `manager` | Team manager — sees their accounts + all direct reports' accounts |
| `executive` | VP/C-suite — sees all accounts org-wide (read-only on queue) |
| `admin` | Full access to all features including admin panel |

### How It Works

- **AuthContext** (`src/lib/auth/AuthContext.tsx`) is the single source of the current user identity and derived account scope.
- Phase 1A: Users are selected via a **dev persona switcher** in the header (visible only in development). Default user is `pulse-admin`.
- Phase 1B (planned): Google Workspace OAuth replaces the switcher — same contract, different hydration source.
- `switchUser(userId)` callback lets the dev switcher change the active persona without a page reload.

### Route Guards

- **RoleGuard**: Wraps every route; redirects unauthorized roles to their default route.
- **AccountScopeGuard**: Applied to `/accounts/:id`; enforces RM/Manager scope. Executives and Admins bypass with read-only access.

### Role → Default Route

| Role | Default landing |
|---|---|
| `rm` | `/accounts` |
| `manager` | `/accounts` |
| `executive` | `/executive` |
| `admin` | `/actions` |

### User Hierarchy (Real Salesforce Users)

```
Eddy Chen (executive / VP of Client Success)
├── Sarah Hooper (manager)
│   ├── Sidra Zia
│   ├── Sajjal Shaheedi
│   ├── Michael Vasquez
│   ├── Yozeline Candia
│   ├── Tanveer Shoukat
│   ├── Muhammad Dawar Khan
│   └── Attiya Arooj
└── Muhammad Ibrahim (manager)
    ├── Ameer Ali
    ├── Abbas Haider
    ├── Zeeshan Hassan
    ├── Ghaeen Us Salam
    ├── Akash Tahir
    ├── Ammar Ashique
    ├── Amir Zaidi
    ├── Mubeen Sohail
    └── Sheryl Stephen
```

All users have real Salesforce User IDs (`sfUserId`) stored in `demo_characters.ts`, used to filter accounts by `owner_id` in the database.

---

## 2. Account List Rail

**Route:** `/accounts` (left column)  
**Roles:** RM, Manager, Executive, Admin

### Scope Filtering (Server-Side)

| Role | API filter | What they see |
|---|---|---|
| RM | `?rm_id=<sfUserId>` | Only their own accounts |
| Manager | `?rm_ids=<mgr_id>,<rm1_id>,...` | Their accounts + all direct reports' accounts |
| Executive | _(no filter)_ | All accounts (assigned + unassigned) |
| Admin | _(no filter)_ | All accounts (assigned + unassigned) |

### Search

- Real-time name search input with a magnifier icon.
- Clears with an `×` button.
- Filters the already-loaded list instantly (no API call).

### Filter Chips

- **Risk:** All / Low / Medium / High
- **Tier:** All / Core / Growth / Strategic
- Active chip is highlighted in brand purple.

### Count Display

- Shows total count (e.g. `28`) when no filter is active.
- Shows `N of total` (e.g. `12 of 28`) when any filter or search is active.
- "Clear all" link appears when any filter/search is set.

### Account Cards

Each card shows:
- Account name
- Next meeting / EBR date (or "No meeting scheduled")
- Risk badge (High / Medium / Low)
- ARR (`$10K × active placements`)
- Composite health score and progress bar (`x/10`)

Clicking a card sets the selected account, updating the center column and right-rail queue.

---

## 3. Account Workspace

**Route:** `/accounts`  
**Layout:** Three-column grid

### Columns

| Column | Width | Content |
|---|---|---|
| Left | 3/12 | Account List Rail (see §2) |
| Center | 6/12 | Situational Hero + Signal Vector + Verified Themes + Meeting Brief |
| Right | 3/12 | Per-account Action Queue |

### Auto-Select

When the account list loads and no account is selected, the first account in the list is automatically selected.

### Center Column Panels

**Situational Hero**
- Account name, tier, composite health ring (270° conic-gradient arc)
- Churn probability (if available)
- AI-RM positioning statement

**Signal Vector Panel**
- 4 axes: Engagement, Satisfaction, Retention Safety, Growth Orientation
- Percentage bars per axis (sourced from `signal_vector` JSONB in DB)

**Verified Themes Panel**
- List of AI-identified themes for the account (e.g. "Churn risk signal", "Renewal window approaching")

**Meeting Brief Panel**
- Last EBR details + AI-generated briefing for upcoming meetings

---

## 4. Action Queue

**Routes:** `/actions` (full page), right rail in `/accounts`  
**Roles:** RM, Manager, Admin (Executives cannot act on queue)

### What It Shows

AI-proposed outreach actions. Each action is a recommendation the RM must approve, modify, or reject before anything is sent to the client.

### Filters

| Filter | Options |
|---|---|
| Status | Active / Approved / All |
| Time | All time / Today / This week |
| Tier | Core / Growth / Strategic |

### Action Card

Each card shows:
- Account name + tier badge
- Proposed action headline
- Risk indicator
- Expand button → **WhyDetailPanel**

### WhyDetailPanel (Expanded)

- Full context: why the AI recommended this action
- Editable fields (via ModifyEditor) for in-line customization
- Three controls:
  - **Approve** — accepts the action as-is
  - **Modify** — edits fields then approves
  - **Reject** — opens RejectModal with reason picker + free text

### Per-Account Mode (Right Rail)

When embedded in `/accounts`, the queue shows only actions for the selected account. Status/Time/Tier filters are hidden in this mode.

### Polling

Queue auto-refreshes every 10 seconds to pick up new AI-proposed actions.

### URL Deep-Link

`/actions?rm=<rmId>` — navigates from Constellation node click directly to that RM's filtered queue.

---

## 5. Constellation View

**Route:** `/constellation`  
**Roles:** RM, Manager, Executive, Admin  
**Code-split:** ~200 kB gz (react-force-graph + d3)

### What It Is

An interactive force-directed network graph of the org's accounts, talent, and RMs.

### Node Types & Click Behavior

| Node | Click action |
|---|---|
| Globe (org root) | Executive view (Admin/Exec only) |
| Manager node | Zoom into manager's sub-graph |
| RM node | Navigate to `/actions?rm=<id>` |
| Account node | Open talent orbit / account detail |

### RBAC Scoping

- RM sees only their own book
- Manager sees their team's sub-graph
- Executive / Admin sees full org

### Overlay Cards

Three overlay cards appear on top of the graph when patterns are detected:

1. **Cluster Pattern Overlay** — groups of at-risk accounts clustering together
2. **RM Capacity Imbalance Overlay** — RMs with overloaded vs. underloaded queues
3. **Escalation Tier-Jump Overlay** — accounts that jumped tiers unexpectedly

---

## 6. Executive Dashboard

**Route:** `/executive`  
**Roles:** Executive, Admin

### Layout

Three top stat cards + hero section + asks band + team table + book numbers strip.

### Stat Cards (Top Row)

- **Client Stickiness** — active talent as % of max capacity
- **Hero Card** — composite health ring for the full book
- **Upsell Opportunities** — expansion-ready accounts count + ARR

### "What I'd Ask of You" Band

AI-generated asks directed at named RMs, with approve/edit buttons for the executive to action.

### Team Workload Table

Per-RM row showing:
- Pending actions count
- Approved this week
- Throughput trend indicator

### Book in Numbers Strip

Live ARR breakdown: Total book ARR, at-risk ARR, churn-exposure ARR (all computed from `active_placements × $10K`).

---

## 7. Outreach Submit Form

**Route:** `/submit`  
**Roles:** RM, Manager, Executive, Admin

### Purpose

RMs create RM_Outreach__c records directly in Salesforce from this form. It captures everything needed to document a client outreach event.

### Sections

1. **Account & Opportunity** — searchable dropdowns, pulls from Salesforce
2. **Health & Risk** — composite health score, churn probability, expansion probability
3. **Meeting Details** — EBR date, description, recording URL, transcript
4. **Sentiment** — client sentiment assessment
5. **Competitive Intelligence** — competitor mentions, positioning notes
6. **Feedback & Referral** — category tagging, referral data

### On Submit

POSTs to `/submit/outreach` → creates record in Salesforce → shows success confirmation screen.

---

## 8. Support AI Chat

**Route:** `/support`  
**Roles:** RM, Manager, Executive, Admin  
**Model:** Claude Sonnet 4.6

### What It Does

A streaming AI assistant that can look up live Salesforce data to answer questions about accounts, placements, outreach history, escalations, and opportunities.

### Conversation Features

- Streaming response (Server-Sent Events) — text appears as it's generated
- Conversation history persists across messages in the session
- Suggested starter questions for new users
- Auto-resizing textarea

### Tool Use: `query_salesforce`

The AI can run read-only SOQL queries against Salesforce to answer factual questions.

- **Allowed objects:** Account, Associates__c, RM_Outreach__c, Opportunity, Case
- **Safety:** DML keywords (`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `UPSERT`) are blocked server-side
- **Transparency:** Tool calls are shown as collapsible chips in the chat UI (with the SOQL query visible)

---

## 9. Admin Panel

**Route:** `/admin/*`  
**Roles:** Admin only

### Sub-pages

#### Signal Performance (`/admin/signals`)

Table of 7 AI signals with:
- Precision score (bar)
- RM satisfaction rating
- Trend indicator (up/down/flat)
- Fire rate (signals triggered per week)

KPI cards at top: Avg precision, High-confidence signals count, Fires/week.

#### Outcome Tracking (`/admin/outcomes`)

Closed-loop table showing signal → proposed action → RM decision → outcome → revenue impact.

KPI cards: Approval rate, Revenue protected, Revenue lost.

#### Admin Settings (`/admin/settings`)

| Setting | Description |
|---|---|
| Kill Switch | Disables all AI-proposed actions across the org |
| Signal Thresholds | Churn %, renewal window, silent account days, expansion confidence |
| Queue Policy | Auto-approve toggle, TTL for pending actions, max pending limit |
| Notifications | Alert routing config |
| Integrations | Status indicators (Salesforce, Langfuse, Activepieces) |

> Note: Settings toggles are wired frontend-only in Phase 1A. Backend write endpoints are planned for Phase 2.

---

## 10. User Management

**Route:** `/settings/users`  
**Roles:** Admin only

### Layout

Three-column panel:
- Left: Role filter chips (RM / Manager / Executive / Admin)
- Center: User table (name, email, role, account scope count)
- Right: Selected user detail — permissions summary + account scope list (derived from `deriveAccountScope`)

> "Change role" workflow is planned for Phase 2.

---

## 11. Salesforce Sync (Background)

**Module:** `core/salesforce/sync.py`  
**Trigger:** On FastAPI startup + every 12 hours via asyncio background task

### What It Syncs

Fetches from Salesforce in parallel:
- All "Client" type Accounts
- `RM_Outreach__c` — health scores and churn data
- `Associates__c` — active placement counts per account
- `Case` — open escalations

### Derived Fields Computed During Sync

| Field | Logic |
|---|---|
| `tier` | ENT → Strategic, MID-MKT → Growth, SMB/Insurance → Core |
| `composite_health` | Derived from `Customer_Health__c` label + `Churn_Probability__c` |
| `risk` | High (churn ≥50% or score <5.0), Medium (5.0–7.0), Low (≥7.0) |
| `signal_vector` | 4-axis JSON (Engagement, Satisfaction, Retention Safety, Growth Orientation) |
| `themes` | HTML-formatted insight strings |
| `arr_usd` | `active_talent_count × $10,000` |

### Storage

Upserted into `pulse.sf_accounts` (Supabase Postgres) using `ON CONFLICT (account_id) DO UPDATE`.

---

## 12. Backend API Reference

**Base URL:** `/api`  
**Auth:** Header-based placeholder (`X-User-Id`, `X-User-Role`, `X-Report-Ids`) — OAuth in Phase 1B

### Accounts

| Method | Path | Description |
|---|---|---|
| GET | `/accounts` | Paginated list. Params: `tier`, `rm_id`, `rm_ids` (comma-separated), `page`, `page_size` |
| GET | `/accounts/{id}` | Full account health with `signal_vector`, `themes`, `churn_probability` |

### Actions

| Method | Path | Description |
|---|---|---|
| GET | `/actions` | List pending actions (scoped by caller role) |
| GET | `/actions/{id}` | Full action detail + history |
| POST | `/actions/{id}/approve` | Approve action as-is |
| POST | `/actions/{id}/modify` | Modify fields + approve |
| POST | `/actions/{id}/reject` | Reject with `reason_picker` + optional `free_text` |
| POST | `/actions/{id}/expire` | Mark action expired (TTL) |

### Submit

| Method | Path | Description |
|---|---|---|
| POST | `/submit/outreach` | Create `RM_Outreach__c` in Salesforce |
| GET | `/submit/opportunities` | List open Opportunities (supports `account_id` filter) |

### Support

| Method | Path | Description |
|---|---|---|
| POST | `/support/chat` | Streaming SSE chat endpoint (Claude + SOQL tool) |

### Profiles

| Method | Path | Description |
|---|---|---|
| GET | `/profiles/{type}/{entity_id}` | Read profile markdown |
| PUT | `/profiles/{type}/{entity_id}` | RM override of profile content |

---

## Key Design Principles

- **No auto-send** — every AI-proposed action requires explicit RM approval before anything reaches the client
- **Scope enforcement** — RBAC is enforced both server-side (actions API) and client-side (route guards + filter params)
- **Single source of truth** — all ARR, talent counts, and user hierarchy flow from `demo_characters.ts` and the Salesforce sync; nothing is hand-asserted in individual components
- **Real-data first** — accounts come from live Salesforce via 12-hour DB sync, not demo fixtures
- **Motion & accessibility** — `FadeLift` respects `prefers-reduced-motion`; Framer Motion `AnimatePresence` on queue cards

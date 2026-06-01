# Edge Pulse — Feature Documentation

> **Product:** Relationship Intelligence for Relationship Managers  
> **Stack:** React (Vite) + FastAPI + Postgres (Supabase) + Salesforce + Claude AI  
> **Branch:** `feature/salesforce-support-integration`  
> **Last updated:** 2026-06-01  
> **Status legend:** ✅ Done · ⚠️ Partial · 🔲 Planned (Phase 1 scope) · ❌ Not started

---

## Phase 1 Delivery Status

| Area | Status | Notes |
|---|---|---|
| Authentication & RBAC | ✅ Done | Google OAuth live; 4-role model |
| Account List Rail | ✅ Done | Search + risk/tier chips + scope |
| Account Workspace (3-col hero) | ✅ Done | Health ring, signal vector, themes |
| Action Queue UI | ✅ Done | Approve/modify/reject; 10s polling |
| Constellation View | ✅ Done | Force-graph + 3 overlay types |
| Executive Dashboard (CEO View) | ✅ Done | Stat cards, asks, team table |
| Outreach Submit Form | ✅ Done | Creates RM_Outreach__c in SFDC |
| Support AI Chat | ✅ Done | Claude + SOQL tool |
| Admin Panel (Signal Performance + Outcomes + Settings) | ✅ Done | Layer 8 Mechanisms 1 + 3 |
| User Management | ✅ Done | Role/scope view |
| Pulse Bar (Agent Presence) | ✅ Done | Breathing indicator on every screen |
| Salesforce Signal Source Adapter | ✅ Done | Accounts, RM_Outreach, Associates, Cases |
| Salesforce DB Sync (12-hr background task) | ✅ Done | Upserts to `pulse.sf_accounts` |
| Chorus Signal Source Adapter | ⚠️ Partial | Module exists (232 lines); not wired into live ingestion |
| Calendar Signal Source Adapter | ⚠️ Partial | Module exists (193 lines); not wired |
| Opportunity-Tracker Adapter | ⚠️ Partial | Module exists (149 lines); not wired |
| Memory Layer (Graphiti + Kuzu) | ⚠️ Partial | Driver + graph modules exist; not actively ingesting |
| Signal Definition Library (14 signals) | ⚠️ Partial | All 14 .py implementations exist; runtime wired; not triggered live |
| Skills Layer (11 skills) | 🔲 Planned | `run_skill()` stub only; skills 018-028 specs not implemented |
| Event Log + Reasoning Capture | ⚠️ Partial | Schema + log.py exist (538 lines); wired to DB |
| Action Queue Service (AI-proposed actions) | ⚠️ Partial | service.py exists; wired to `/actions` API |
| Per-account view (opt-in depth) | 🔲 Planned | Route exists; renders `Placeholder` component |
| Submission UI (Slack slash command) | ❌ Not started | Implemented as web form only; Slack command not built |
| Demo storyboard (DHR + Mendota + Cirventis) | 🔲 Planned | Anchors locked; storyboard (spec 046-047) not built |
| Demo HTML fallback | 🔲 Planned | Not built |
| Activepieces on Fly.io | 🔲 Planned | Status indicator in admin; deploy not done |
| Langfuse on Fly.io | 🔲 Planned | Status indicator in admin; deploy not done |
| Layer 8 Synthetic seed (spec 045a) | 🔲 Planned | Outcome tracking UI done; synthetic seed data not seeded |

---

## Table of Contents

1. [Authentication & RBAC](#1-authentication--rbac)
2. [Account List Rail](#2-account-list-rail)
3. [Account Workspace](#3-account-workspace)
4. [Action Queue](#4-action-queue)
5. [Constellation View](#5-constellation-view)
6. [Executive Dashboard (CEO View)](#6-executive-dashboard-ceo-view)
7. [Outreach Submit Form](#7-outreach-submit-form)
8. [Support AI Chat](#8-support-ai-chat)
9. [Admin Panel](#9-admin-panel)
10. [User Management](#10-user-management)
11. [Pulse Bar (Agent Presence)](#11-pulse-bar-agent-presence)
12. [Salesforce Sync (Background)](#12-salesforce-sync-background)
13. [Signal Source Adapters](#13-signal-source-adapters)
14. [Memory Layer](#14-memory-layer)
15. [Signal Definition Library](#15-signal-definition-library)
16. [Skills Layer](#16-skills-layer)
17. [Event Log & Reasoning Capture](#17-event-log--reasoning-capture)
18. [Backend API Reference](#18-backend-api-reference)

---

## 1. Authentication & RBAC

**Status: ✅ Done**

### Roles

| Role | Description |
|---|---|
| `rm` | Relationship Manager — sees only their own book of accounts |
| `manager` | Team manager — sees their accounts + all direct reports' accounts |
| `executive` | VP/C-suite — sees all accounts org-wide (read-only on queue) |
| `admin` | Full access to all features including admin panel |

### Auth Flow

- **Phase 1A (Dev):** Dev persona switcher in header (hidden in production). Default: `pulse-admin`.
- **Phase 1B (Live):** Google Workspace OAuth — `/api/auth/google/start` → Google consent → FastAPI `/auth/google/callback` → tokens saved to `pulse.google_sessions` → redirects to `/login?google=success&google_user_id=<id>`. Only emails in `ALLOWED_EMAILS` whitelist can authenticate.
- Session persisted in `localStorage` (`pulse_user_id`). Logout clears storage and sets a `sessionStorage` flag to block DEV auto-login.

### User Hierarchy (Real Salesforce Users)

```
Eddy Chen (executive — VP of Client Success)
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

All users have real Salesforce `sfUserId` (18-char) used to filter `owner_id` in the DB.

### Route Guards

- **RoleGuard** — wraps every route; redirects unauthorized roles.
- **AccountScopeGuard** — enforces RM/Manager scope on `/accounts/:id`; Execs/Admin bypass.

### Role → Default Route

| Role | Landing |
|---|---|
| `rm` | `/accounts` |
| `manager` | `/accounts` |
| `executive` | `/executive` |
| `admin` | `/actions` |

---

## 2. Account List Rail

**Status: ✅ Done**

**Route:** `/accounts` (left column) | **Roles:** RM, Manager, Executive, Admin

### Scope Filtering (Server-Side)

| Role | API filter | What they see |
|---|---|---|
| RM | `?rm_id=<sfUserId>` | Own accounts only |
| Manager | `?rm_ids=<mgr_sfId>,<rm1_sfId>,...` | Their accounts + team's |
| Executive | _(no filter)_ | All accounts (assigned + unassigned) |
| Admin | _(no filter)_ | All accounts (assigned + unassigned) |

### Search & Filters

- Real-time name search with clear (`×`) button — no API call, instant.
- **Risk chips:** All / High / Medium / Low
- **Tier chips:** All / Core / Growth / Strategic
- Count shows `N of total` when filtering; "Clear all" link when active.

### Account Cards

- Account name · next meeting / EBR date · Risk badge · ARR · composite health bar (`x/10`)
- Clicking sets selected account → updates center column + right-rail queue.

---

## 3. Account Workspace

**Status: ✅ Done (three-column hero) · 🔲 Per-account drill-down view planned**

**Route:** `/accounts` | **Layout:** 3-column grid

| Column | Width | Content |
|---|---|---|
| Left | 3/12 | Account List Rail |
| Center | 6/12 | Situational Hero + Signal Vector + Themes + Meeting Brief |
| Right | 3/12 | Per-account Action Queue |

### Center Column Panels

- **Situational Hero** — account name, tier, 270° conic-gradient health ring, churn probability, AI-RM positioning statement
- **Signal Vector Panel** — 4 axes: Engagement, Satisfaction, Retention Safety, Growth Orientation (percentage bars from `signal_vector` JSONB)
- **Verified Themes Panel** — AI-identified themes (e.g. "Churn risk signal", "Renewal window approaching")
- **Meeting Brief Panel** — last EBR + AI-generated briefing

### Per-Account Drill-Down (`/accounts/:id`)

Route and RBAC guard exist; renders `Placeholder` component. Full opt-in-depth view (spec 036-037) not yet implemented.

---

## 4. Action Queue

**Status: ✅ Done**

**Routes:** `/actions` (full page) · right rail in `/accounts` | **Roles:** RM, Manager, Admin

### Filters

| Filter | Options |
|---|---|
| Status | Active / Approved / All |
| Time | All time / Today / This week |
| Tier | Core / Growth / Strategic |

### Action Cards

Account name + tier badge · proposed action headline · risk indicator · **Expand → WhyDetailPanel**

### WhyDetailPanel

- Full AI reasoning context
- Editable fields (ModifyEditor)
- **Approve** / **Modify** / **Reject** (RejectModal with reason picker + free text)

### Per-Account Mode (Right Rail)

Queue scoped to selected account only; Status/Time/Tier filters hidden.

### Polling & Deep-Link

- Auto-refreshes every 10 seconds
- `/actions?rm=<rmId>` — deep-link from Constellation RM node click

---

## 5. Constellation View

**Status: ✅ Done**

**Route:** `/constellation` | **Roles:** RM, Manager, Executive, Admin | **Code-split:** ~200 kB gz

Interactive force-directed network graph of the full org: accounts, talent, RMs.

### Node Click Matrix

| Node | Click | Modifier+Click |
|---|---|---|
| Globe | `/executive` | — |
| Manager | Zoom into sub-graph | `/actions?manager=<id>` |
| RM | `/actions?rm=<id>` | — |
| Account | Toggle talent orbit | Set selected account → `/accounts` |

### RBAC Scoping

- RM: own book · Manager: team sub-graph · Executive/Admin: full org

### Overlay Cards (3 types)

1. **Cluster Pattern** — groups of at-risk accounts clustering
2. **RM Capacity Imbalance** — over/underloaded RM queues
3. **Escalation Tier-Jump** — accounts that jumped tiers unexpectedly

---

## 6. Executive Dashboard (CEO View)

**Status: ✅ Done**

**Route:** `/executive` | **Roles:** Executive, Admin

- **Stat cards:** Client Stickiness · Full-book health ring · Upsell opportunities + ARR
- **"What I'd Ask of You" band** — AI-generated asks directed at named RMs, with approve/edit buttons
- **Team Workload Table** — per-RM pending actions, approved this week, throughput trend
- **Book in Numbers** — total ARR, at-risk ARR, churn-exposure ARR (all from `active_placements × $10K`)

---

## 7. Outreach Submit Form

**Status: ✅ Done**

**Route:** `/submit` | **Roles:** RM, Manager, Executive, Admin

Creates `RM_Outreach__c` records directly in Salesforce. Sections:

1. Account & Opportunity (searchable dropdowns from SFDC)
2. Health & Risk (composite health, churn probability, expansion probability)
3. Meeting Details (EBR date, description, recording URL, transcript)
4. Sentiment (client sentiment assessment)
5. Competitive Intelligence (competitor mentions, positioning)
6. Feedback & Referral (category tagging, referral data)

POSTs to `/submit/outreach` → creates SFDC record → success confirmation.

> **Not yet built:** Slack slash command variant (v1.5+)

---

## 8. Support AI Chat

**Status: ✅ Done**

**Route:** `/support` | **Model:** Claude Sonnet 4.6

Streaming AI assistant with live Salesforce lookup via `query_salesforce` tool.

- Server-Sent Events streaming · conversation history in session · suggested starter questions · auto-resizing textarea
- **Allowed SOQL objects:** Account, Associates__c, RM_Outreach__c, Opportunity, Case
- DML blocked server-side · tool calls shown as collapsible chips with visible SOQL

---

## 9. Admin Panel

**Status: ✅ Done**

**Route:** `/admin/*` | **Roles:** Admin only

### Signal Performance (`/admin/signals`) — Layer 8 Mechanism 1

Table of 7 AI signals: precision score, RM satisfaction rating, trend indicator, fire rate.  
KPI cards: Avg precision, High-confidence signal count, Fires/week.

### Outcome Tracking (`/admin/outcomes`) — Layer 8 Mechanism 3

Closed-loop table: signal → proposed action → RM decision → outcome → revenue impact.  
KPI cards: Approval rate, Revenue protected, Revenue lost.

> **Not yet done:** Synthetic seed data (spec 045a). Table UI is built; real outcome records not populated.

### Admin Settings (`/admin/settings`)

| Setting | Status |
|---|---|
| Kill Switch (disables all AI-proposed actions) | UI wired; backend kill_switch.py exists |
| Signal Thresholds (churn %, renewal window, silence days, expansion confidence) | UI wired; backend settings.py exists |
| Queue Policy (auto-approve, TTL, max pending) | UI wired; backend wired |
| Notifications (alert routing) | UI only (Phase 2) |
| Integrations status (Salesforce, Langfuse, Activepieces) | Status indicators only |

---

## 10. User Management

**Status: ✅ Done**

**Route:** `/settings/users` | **Roles:** Admin only

Three-column panel: Role filter chips · User table (name, email, role, scope count) · Selected user detail (permissions + account scope list from `deriveAccountScope`).

> "Change role" workflow: Phase 2.

---

## 11. Pulse Bar (Agent Presence)

**Status: ✅ Done**

Persistent breathing indicator on every authenticated screen. Implemented in `PulseBar.tsx` + `PulseBarController.tsx`. Animates when the agent is processing (Framer Motion). Respects `prefers-reduced-motion`. Locked design: Pulse Bar (Breathing) per §6 design rule 25.

---

## 12. Salesforce Sync (Background)

**Status: ✅ Done**

**Module:** `core/salesforce/sync.py` | **Trigger:** FastAPI startup + every 12 hours

### What It Syncs

- All "Client" Accounts
- `RM_Outreach__c` — health scores, churn data
- `Associates__c` — active placement counts per account
- `Case` — open escalations (including descriptions)

### Derived Fields

| Field | Logic |
|---|---|
| `tier` | ENT → Strategic · MID-MKT → Growth · SMB/Insurance → Core |
| `composite_health` | From `Customer_Health__c` + `Churn_Probability__c` |
| `risk` | High (churn ≥50% or score <5) · Medium (5–7) · Low (≥7) |
| `signal_vector` | 4-axis JSON (Engagement, Satisfaction, Retention Safety, Growth Orientation) |
| `themes` | HTML-formatted AI insight strings |
| `arr_usd` | `active_talent_count × $10,000` |

Upserted into `pulse.sf_accounts` via `ON CONFLICT (account_id) DO UPDATE`.

---

## 13. Signal Source Adapters

**Status: ✅ SFDC done · ⚠️ Chorus/Calendar/Opp-Tracker modules built, not wired to live ingestion**

**Module:** `core/adapters/`

| Adapter | File | Lines | Status |
|---|---|---|---|
| Salesforce | `sfdc.py` | 322 | ✅ Live — wired to sync + support chat |
| Chorus | `chorus.py` | 232 | ⚠️ Module complete; ingestion pipeline not triggered |
| Calendar | `calendar.py` | 193 | ⚠️ Module complete; not wired |
| Opportunity-Tracker | `opportunity_tracker.py` | 149 | ⚠️ Module complete; not wired |

Base adapter interface in `base.py` + episode normalization in `episode.py`.

To complete Phase 1: wire Chorus, Calendar, and Opp-Tracker adapters into the ingestion pipeline and trigger from the event loop.

---

## 14. Memory Layer

**Status: ⚠️ Partial — modules exist; not actively ingesting**

**Modules:** `core/memory/`

| Component | File | Status |
|---|---|---|
| PulseKuzuDriver (FTS bootstrap subclass) | `driver.py` | ⚠️ Exists (76 lines); not connected to live episode ingestion |
| Three-graph schema | `graph.py` | ⚠️ Schema defined |
| Retrievers | `retrievers.py` | ⚠️ Query interface defined |
| Denylist | `denylist.py` | ✅ Test-account exclusion implemented |

Graphiti (temporal memory engine) and Kuzu (graph backend) are the locked choices per ADRs. Phase 1 requires connecting the signal source adapters → Episode normalizer → Graphiti ingestion.

---

## 15. Signal Definition Library

**Status: ⚠️ All 14 definitions implemented; runtime exists; not triggered live**

**Modules:** `core/signals/` + `02_planning/signals/` (specs)

| Signal | Implementation |
|---|---|
| `account_silence_pattern_v1` | ✅ |
| `churn_signal_competitor_mention_v1` | ✅ |
| `churn_signal_contact_disengagement_v1` | ✅ |
| `churn_signal_renewal_period_silence_v1` | ✅ |
| `churn_signal_sentiment_decline_v1` | ✅ |
| `client_termination_pattern_v1` | ✅ |
| `escalation_signal_case_pattern_v1` | ✅ |
| `escalation_signal_severity_jump_v1` | ✅ |
| `expansion_signal_job_posting_match_v1` | ✅ |
| `expansion_signal_verbal_capacity_mention_v1` | ✅ |
| `recognition_signal_advocacy_candidate_v1` | ✅ |
| `talent_burnout_signal_v1` | ✅ |
| `talent_growth_concern_v1` | ✅ |
| `talent_pay_concern_v1` | ✅ |

`runtime.py` exists to execute signal detection. Each definition has a corresponding `.md` spec in `02_planning/signals/`. No black-box detection — every mechanism is inspectable.

---

## 16. Skills Layer

**Status: 🔲 Planned — `run_skill()` stub only; specs 018-028 not implemented**

**Module:** `core/agent/runner.py`

The async-everything agent runner (ADR-001) exposes `run_skill(skill_id, ...)`. Currently a `NotImplementedError` stub per §6 rule 14 (no silent no-ops). Skills 01–11 (specs 018-028) are the outstanding backend work for Phase 1.

Skills to build:
- Skill 01: Account silence detection
- Skill 02: Churn signal triangulation
- Skill 03: Renewal window outreach
- Skill 04: Sentiment decline response
- Skill 05: Competitor mention response
- Skill 06: Escalation case response
- Skill 07: Talent burnout intervention
- Skill 08: Expansion intent detection
- Skill 09: Recognition + advocacy capture
- Skill 10: Client termination pattern
- Skill 11: Expansion intent from job posting

---

## 17. Event Log & Reasoning Capture

**Status: ⚠️ Partial — schema + log module exist; wired to DB**

**Module:** `core/events/`

| Component | Status |
|---|---|
| Event schema + types | ✅ Defined |
| `log.py` (538 lines) | ✅ Logging functions implemented |
| DB write path | ⚠️ Wired; not exercised without live skill runs |
| Query interface | ✅ `queries.py` exists |

Every agent action must log to the event log with reasoning attached (§6 rule 14). This becomes fully exercised once skills are wired.

---

## 18. Backend API Reference

**Status: ✅ Done**

**Base URL:** `/api` | **Auth:** `X-User-Id` + `X-User-Role` headers (OAuth token in Phase 1B)

### Accounts

| Method | Path | Description |
|---|---|---|
| GET | `/accounts` | Paginated list. Params: `tier`, `rm_id`, `rm_ids`, `page`, `page_size` |
| GET | `/accounts/{id}` | Full health: `signal_vector`, `themes`, `churn_probability` |

### Actions

| Method | Path | Description |
|---|---|---|
| GET | `/actions` | List actions (role-scoped) |
| GET | `/actions/{id}` | Full detail + history |
| POST | `/actions/{id}/approve` | Approve as-is |
| POST | `/actions/{id}/modify` | Modify fields + approve |
| POST | `/actions/{id}/reject` | Reject with reason |
| POST | `/actions/{id}/expire` | Mark expired (TTL) |

### Submit

| Method | Path | Description |
|---|---|---|
| POST | `/submit/outreach` | Create `RM_Outreach__c` in Salesforce |
| GET | `/submit/opportunities` | List open Opportunities (`account_id` filter) |

### Support

| Method | Path | Description |
|---|---|---|
| POST | `/support/chat` | Streaming SSE chat (Claude + SOQL tool) |

### Auth

| Method | Path | Description |
|---|---|---|
| GET | `/auth/google/start` | Redirect to Google OAuth consent screen |
| GET | `/auth/google/callback` | Exchange code, verify email, save tokens, redirect frontend |

### Profiles

| Method | Path | Description |
|---|---|---|
| GET | `/profiles/{type}/{entity_id}` | Read per-profile markdown |
| PUT | `/profiles/{type}/{entity_id}` | RM override of profile content |

---

## Key Design Principles

- **No auto-send** — every AI-proposed action requires explicit RM approval
- **No black-box detection** — every signal has a Signal Definition Library entry with a corresponding `.md` spec
- **Human-in-the-loop is the product** — Action queue is the hero surface
- **Scope enforcement** — RBAC enforced server-side (actions API) and client-side (route guards + filter params)
- **Real-data first** — accounts from live Salesforce via 12-hour DB sync
- **Tier-aware behavior** — SMB → more automation; Enterprise → more human-in-the-loop
- **Motion & accessibility** — `FadeLift` + Framer Motion `AnimatePresence`; `prefers-reduced-motion` respected
- **White-label** — no Anthropic/AI branding exposed to end users

---

## What's Left for Demo Day (June 30)

### Must-complete (Phase 1 scope)

1. **Wire signal source adapters** — Chorus, Calendar, and Opp-Tracker into live ingestion pipeline
2. **Skills 01–11** — implement `run_skill()` for all 11 skills (specs 018-028)
3. **Per-account drill-down view** — replace Placeholder at `/accounts/:id` (specs 036-037)
4. **Connect memory layer** — Graphiti + Kuzu receiving live episodes from adapters
5. **Layer 8 synthetic seed** — populate outcome records (spec 045a)
6. **Demo storyboard** — DHR Health Clinics + Mendota Insurance + Cirventis/Helix (specs 046-047)
7. **Activepieces on Fly.io** — deploy workflow engine (ADR-002)
8. **Langfuse on Fly.io** — deploy observability backend (ADR-003)

### Won't-do (v1.5+)

- Slack slash command for outreach submit
- Zoom Signal Source Adapter
- Slack Signal Source Adapter
- Product Adoption Monitor skill (Skill 07 deferred per §13)
- Dynamic Enterprise EBR-tie-in copy
- Demo HTML fallback (lower priority given live-data approach)

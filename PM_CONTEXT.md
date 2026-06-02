# PM-CONTEXT — EDGE Pulse

**Last updated:** 2026-06-02 (Build Sessions 15–NN — Phase 4 Week 2 in progress. Updated by Claude Code.)
**Maintained by:** PM (Senior Product Advisor) — owner of this doc
**Phase:** **Phase 4 Build — ACTIVE. Week 2 of 6.**
**Demo target:** **2026-06-30** (4 weeks remaining from 2026-06-02)
**Scope status:** **FROZEN** as of Session 11. No additions without an equivalent removal.

---

## 0. How a fresh Claude should use this doc

Read sections 1–8 in order. By the end you will know:
- What we're building (§1)
- Where the product spec lives (§2)
- Where we are in the build (§3)
- The working agreements between user and PM (§4)
- The user's communication style and preferences (§5)
- Open standing rules locked across the project (§6)
- How to handle Claude Code reports (§7)
- The decision and session log (§§8–9), memory patterns (§10), glossary (§11)
- **EDGE Requirements Coverage Map (§13)** — non-negotiable
- **Frozen scope list (§14)** — Phase 1 deliverables locked Session 11, refined Sessions 13–14

Then ask the user "ready to continue?" — don't restart context-gathering questions.

---

## 1. The product in two paragraphs

**EDGE Pulse** is an agentic intelligence and action layer for Relationship Managers (RMs) at EDGE, a US healthcare and insurance staffing company that places HIPAA-trained talent at client sites. Pulse ingests every signal across the RM's universe — Chorus call recordings, Salesforce records (Accounts, Contacts, Opportunities, RM_Outreach__c, Associates__c, Cases including descriptions, Account_Plan__c), customer meetings, opportunity-tracker job-posting signals, and (future phases) Zoom calls and Slack threads — and builds a live, queryable understanding of every customer relationship and every piece of talent placed at those customers. It surfaces silent churn signals, identifies engagement opportunities, and proposes concrete actions that the RM approves with one tap. Every signal Pulse detects is inspectable through the Signal Definition Library — no black boxes. The hero UI surface is an action queue, not a dashboard. A constellation view of the entire book of business is accessible as a dedicated nav surface. The product is white-labeled.

The audience is EDGE's RM team (7–8 RMs today, 602 active customer accounts in production, ~1,300 talent). The strategic pitch is that Pulse turns the RM from a data-gatherer-and-executor into an approver-and-relationship-craftsperson. **Visual design is a primary success criterion** — first-party Edge feel per onedge.co, alive without chat-ified, CEO-attention-grabbing in 5 seconds. **Pulse learns over time** — Layer 8 Option B closes the loop between actions and outcomes. EDGE's original requirements + RM JD are the floor of scope (§13 = 54/56 rows mapped).

---

## 2. Canonical documents

| File | Purpose | Status |
|---|---|---|
| `00_research/synthesis.md` | Phase 1 output | **Exists** |
| `00_research/findings/` | 11 per-repo findings | **Exists** |
| `00_research/spikes/01_sfdc_schema.md` | SFDC schema discovery | **Partial; effectively resolved via Session 13 production-org recon** |
| `00_research/spikes/02_zoom_feasibility.md` | Zoom no-build investigation | **User questionnaire pending (Phase 2+ work)** |
| `00_research/spikes/03_graphiti_verification.md` | Confirmed-GO Session 7 | **Live-run validated** |
| `00_research/spikes/04_opportunity_tracker_review.md` | opportunity-tracker scoping review | **Complete (Session 11)** |
| `00_research/spikes/05_demo_data_recon.md` | Demo data recon | **Complete (Session 13). Resolves pre-flights.** |
| `99_open_questions.md` | Open questions Q1–Q152 | **Q1, Q2, Q6, Q7, Q22, Q26, Q125 resolved** |
| `01_design/00_design_language.md` | Tier-0 design system tokens | **Locked Session 10** |
| `01_design/agent_presence_variants/` | 3 variants + canonical Pulse Bar (Breathing) | **Locked Session 10** |
| `01_design/00_coverage_walk.md` | §13 audit receipt | **Exists** |
| `01_design/01–12` design specs | All 12 Tier 1/2/3 design artifacts | **Exist (Design 12 needs anchor swap as Day-1 housekeeping)** |
| `01_design/skills/01–11` | 11 skill specs | **Exist; "Owned signals" cross-references appended** |
| `02_planning/build-plan.md` | The build-plan-of-record | **Locked Session 12; minor revisions Day-1 Session 14** |
| `02_planning/scope_verification.md` | Final §13/§14 audit | **Locked Session 12** |
| `02_planning/architecture_decisions/ADR-001-agent-reasoning-topology.md` | Async-everything FastAPI | **Locked Session 12** |
| `02_planning/architecture_decisions/ADR-002-workflow-engine.md` | Activepieces on Fly.io | **Locked Session 12** |
| `02_planning/architecture_decisions/ADR-003-observability-backend.md` | Langfuse self-hosted on Fly.io | **Locked Session 12** |
| `02_planning/signal_definition_template.md` | Signal definition template | **Locked Session 12** |
| `02_planning/signals/` | 14 signal definitions | **Locked Session 12; `account_silence_pattern_v1` revised Session 13** |
| `02_planning/specs/` | 48 work-unit specs | **Locked Session 12 + 045a Session 13** |
| `03_build/` | Phase 4 output | **Begins Thu 2026-05-22** |

**Source-of-truth requirements:**
- `RM_Initial_Requirements_from_EDGE.md`
- `EDDY_s_REPLY_on_RM_JD.md`

**Brand reference:**
- https://onedge.co
- `01_design/00_design_language_preview.tsx`

---

## 3. Where we are in the build

### Phase sequence
1. **Phase 1 — Research.** CLOSED 2026-05-19.
2. **Phase 2 — Design.** CLOSED 2026-05-20.
3. **Phase 2.5 — Brand Alignment + Agent Presence.** CLOSED 2026-05-20.
4. **opportunity-tracker review.** CLOSED 2026-05-20.
5. **Phase 3 — Planning.** CLOSED 2026-05-20.
6. **Demo data recon.** CLOSED 2026-05-20.
7. **Phase 4 — Build.** **GREEN-LIT Session 14. Kickoff Thu 2026-05-22. ACTIVE Week 2.**

### Phase 4 starting conditions — locked Session 14

**Build window:** 2026-05-22 → 2026-06-30. 30 working days (4-day Week 1 due to Memorial Day Mon May 26). 48 specs. 26.5 days effective work. ~3.5 days distributed buffer.

**Critical path:** *bootstrap → memory layer → SFDC Signal Source Adapter → Event Log → Skill 02 (one end-to-end skill) → Action Queue API → Front-end shell → Action Queue UI → Demo storyboard end-to-end on real data*. Hardest-to-recover slippage point: **end of Week 1**.

**Six gates:**
- Gate 1: Friday May 30 — bootstrap green; one end-to-end episode ingestion from Chorus → Graphiti → query demonstrated; Q21 resolved. **PM stop-and-review (Week-1 protection per Session 12).**
- Gate 2: Friday June 6 — all 4 Signal Source Adapters live; events emitting; retrievers responsive; policy module taking decisions.
- Gate 3: Friday June 13 — Skills 01-09 live end-to-end; Per-Profile Markdown loading; demo-data priming started.
- Gate 4: Friday June 20 — all 11 skills live; Action Queue UI rendering on real backend data; inline-tag voice working end-to-end.
- Gate 5: Friday June 27 — All UI surfaces live; CEO View ready for review; Constellation usable; Layer 8 mechanisms wired Mon Wk6.
- **Demo Day: Tuesday June 30, 2026.**

**Phase 4 Day-1 housekeeping** (in addition to specs 001-004 / Q114-Q116-Q121):
- **Fold spec 045a into spec 045** (or document as a sub-task of 045) — Synthetic action-outcome seed for Layer 8 Mechanism 3. Added Session 13 (0.5d). Build plan as written treats 045 as 1.0d; PM expects this to absorb the synthetic-seed work.
- **Update Design 12 (Demo Storyboard) anchor references** — Acrisure → DHR Health Clinics, Pinnacle → Mendota Insurance, +Cirventis (Helix display alias). Locked Session 13. Spec 046 and 047 DoDs reference the new anchors.

**Three PM-watched concerns Session 14** (not blocking; tracked across Phase 4):
1. **Memorial Day May 26 affects Week 1.** Week 1 is a 4-working-day week. Bootstrap + memory layer + first adapter work is sized for it but tighter than other weeks. PM monitors Gate 1 closely.
2. **Spec 044 (Mechanism 1 Signal Performance metrics) starts Monday Week 6.** Week 6 is supposed to be demo prep. PM expects spec 044 to start Friday end-of-Week-5 if possible, leaving full Mon-Tue Week 6 for completion + Wed onward for storyboard rehearsal.
3. **Spec 043 (OAuth + Supabase Auth) at 0.75d may slip to 1.5d.** Google Workspace OAuth setup typically takes longer than estimated. PM watches Gate 5; if it slips, Week 5 absorbs 0.75d of buffer.

### Phase 4 current status — as of 2026-06-02 (mid-Week 2)

**Ahead of schedule.** As of June 2 (mid-Week 2), specs 001–045 are substantively implemented. The build is running 3–4 weeks ahead of the published schedule. The final two specs (046 demo priming, 047 fallback verification) and end-to-end integration validation remain.

**Spec status by group:**

| Group | Specs | Status |
|---|---|---|
| Foundations (001–010) | Bootstrap, memory layer, event log, policy, kill switch | ✅ ALL DONE |
| Adapters (011–016) | Adapter base, SFDC, Chorus, Calendar, opp-tracker, matcher | ✅ ALL DONE |
| Signal Library (017) | Runtime + 14 signal definitions | ✅ DONE |
| Skills 01–11 (018–028) | All 11 skills implemented + tested | ✅ ALL DONE |
| Per-Profile + Health (029–030) | Markdown layer, dual-sided health rollup | ✅ ALL DONE |
| Action Queue + Dispatch + Outcomes (031–033) | Queue API, dispatch handlers, outcome watchers | ✅ ALL DONE |
| Front-end (034–039) | Shell, Action Queue UI, Hero card, Per-Account, Pulse Bar, Submission UI | ✅ ALL DONE |
| CEO View + Constellation + Auth (040–043) | CEO View, Constellation, RBAC, OAuth | ✅ ALL DONE |
| Layer 8 (044–045) | Signal Performance metrics, Outcome tracking | ✅ ALL DONE |
| Demo (046–047) | Demo data priming script, HTML fallback verification | ⚠️ NOT YET STARTED |

**Pull-forward items** (from v1.5+ list — built during Phase 4 build sessions; required PM sign-off):
- **Zoom Signal Source Adapter** (was §12 #8): `core/adapters/zoom.py` + `core/zoom/sync.py` built; 5,233 episodes ingested from production.
- **Gmail direct sync** (new scope): `core/google/gmail_sync.py` — 6-month inbox sync per authenticated user, email-to-SF-account matching via `pulse.sf_contacts`.
- **SF Contacts sync** (new scope): `pull_and_upsert_contacts()` in `core/salesforce/sync.py`; `pulse.sf_contacts` table; required for Gmail/Calendar email matching.
- **Google Calendar direct sync** (extends spec 014): `core/google/calendar_sync.py` — 6-month calendar event sync; supplements the Signal Source Adapter with a separate polling pipeline for authenticated RMs.

**Constellation real data:** Wired to live SF accounts (628 accounts) via `buildConstellationGraphFromReal()`. Maps `owner_id → DEMO_RMS` through DEMO_USERS.sfUserId bridge. Renders on API data, not fixtures.

**Data in production DB as of June 2:**

| Table | Count |
|---|---|
| `pulse.sf_accounts` | 628 |
| `pulse.episodes` (Chorus) | ~3,225 |
| `pulse.episodes` (Zoom) | ~5,233 |
| `pulse.episodes` (total) | ~8,400+ |
| `pulse.google_sessions` | Active (OAuth working) |

**Open technical issues:**
1. **Meetings endpoint returns empty []** — Chorus `candidate_entities` stores abbreviated `sfdc_id` values (e.g., `"001ACRISURE"`) that don't match full SF IDs (`"001U100000GUkDwIAL"`). Matching logic needs a resolution path.
2. **Google Gmail+Calendar re-auth required** — Any user who authenticated before the scope extension must log out and re-authenticate to grant Gmail+Calendar access. One-time action per user.
3. **Spec 046 demo data priming script not yet built** — Critical for Week 6 prep.
4. **Spec 047 demo HTML fallback not yet verified** — Needs a run against Tier-0 tokens before Demo Day.

---

## 4. Working agreements between user and PM

### 4.1 The PM never writes implementation code
### 4.2 Claude Code is phase-gated
### 4.3 PM verifies Claude Code reports
### 4.4 PM pushes back when user is wrong
### 4.5 Design lock is sacred
### 4.6 PM maintains this doc; user can hand-edit anytime
### 4.7 Markdown over Word
### 4.8 EDGE requirements are the floor, not the ceiling
### 4.9 User-supplied auth keys for development; rotation before prod is user's call
### 4.10 Visual design is a primary success criterion
### 4.11 PM lean is the default when user defers
### 4.12 Scope freeze with weekly check-ins (Session 11)
After Session 11, the Phase 1 scope list is **closed**. Anything new that surfaces between now and 2026-06-30 goes to v1.5+ automatically. Every Friday in Phase 4 we evaluate critical-path progress against the build plan and decide: on track / recover slip / cut to v1.5+. No rolling slips without explicit cut decision.

### 4.13 Phase 4 commits trace back to spec IDs (Session 12)
Every Phase 4 commit message references the spec ID it implements (e.g., `[SPEC-014] add SFDC Signal Source Adapter polling`). Audit chain: commit → spec → design artifact → §13 row or §14 scope line. PM audits a sample of commits weekly.

### 4.14 Production-org development under read-only ingestion (Session 13)
Phase 4 develops directly against the production SFDC org under strict read-only discipline. §6 rule 6 (writes only through Action Queue with explicit approval) is the protection. Auth via `edgelabs.admin@onedge.co`, alias `edgesolutions`, API pinned to v62.0.

### 4.15 PM stop-and-review at Gate 1 (Session 14)
Gate 1 (Friday May 30) is not a self-assessment. Claude Code stops at gate, posts the gate-report, and waits for PM verification before Week 2 work begins. This is the Week-1-load-bearing-for-the-phase protection per Session 12 memory pattern. Gates 2-5 are also stop-and-report but with lighter PM review unless concerns surface.

---

## 5. User context

**Name:** [Owner]
**Company:** EDGE (onedge.co)
**Industry:** US healthcare + insurance staffing
**Team:** 7–8 RMs; 602 active customer accounts; ~1,300 talent

**Communication preferences:**
- Direct and decisive
- Time-pressured but won't sacrifice scope for deadline
- Trusts senior judgment when reasoning is sound — uses "go with your lean" on calls not load-bearing
- Explicit acceptances ("lets go with your recommendation") — match brevity
- Named past pain points: design lock skipped; black-box builds; SDR demo failure
- Practical on security/auth: rotates keys before prod; comfortable with production-org dev under HITL discipline
- Visually exacting: CEO is visually-driven; brand alignment is a primary criterion
- Will provide visual references when asked (Session 8 React preview)
- Adds scope thoughtfully when high-value signals surface
- Has named "no black box" as a critical principle
- Provides operational context that reframes findings (Session 13: RM_Outreach was introduced Feb 2026)

**Stakeholders:**
- **CEO** — visually-driven; wants Pulse to feel first-party Edge
- **Senior Developer** — will scrutinize architecture; validates inspectability + learning architecture
- **VP of Client Success** — cares about operations impact + time savings
- **EDGE doc owner / Eddy** — §13 is the receipt for them

**Budget posture:**
- Phase 1 infra target: under $20/mo. Phase 3 ADRs land at ~$5/mo. Comfortably under target.
- $75–150 per RM per month TCO at steady state
- One-time build cost: $15–25k equivalent dev effort
- Eventual platform target: AWS

**What the user does NOT want to discuss again:**
- White-label rule (locked)
- Product name: EDGE Pulse (locked)
- Graphiti as memory engine (locked, confirmed-GO Session 7)
- Graph architecture Option C (locked)
- Resourceful open-source posture (locked)
- Key rotation discipline (user handles)
- Linear+Granola dark mode (reversed Session 6)
- Agent presence direction (locked Session 10 — Pulse Bar Breathing)
- Workflow engine pick (locked Session 11 — Activepieces self-hosted)
- Agent reasoning topology (locked Session 12 — async-everything FastAPI)
- Observability backend (locked Session 12 — Langfuse self-hosted)
- Production-org development posture (locked Session 13)
- Demo storyboard anchors (locked Session 13 — DHR + Mendota + Cirventis)
- Build plan structure (green-lit Session 14)

---

## 6. Open standing rules

### Product rules
1. **White-label, always.**
2. **AWS-only hosting + audit log on every action.** No PHI redaction pipeline.
3. **Human-in-the-loop is the product.** Action queue is the hero surface.
4. **Tier-aware behavior.** SMB → more automation; Enterprise → more human-in-the-loop.
5. **EDGE coverage map (§13) is a phase-gate check.**
6. **Salesforce write-back only through Action Queue with explicit approval.**
7. **Salesforce is the canonical system-of-record.** Pulse is a synthesis layer over SFDC.
8. **No black-box detection.** Every signal has a Signal Definition Library entry.

### Engineering rules
9. **No code without a spec.** Spec lives in `02_planning/specs/`, referenced by commit message (§4.13).
10. **No commit without tests.** Unit + integration + golden-trace for LLM reasoning.
11. **No dead code.**
12. **No new dependencies without a decision log entry.**
13. **No UI without a demo note.**
14. **No silent failure.** Every agent action logs to event log with reasoning attached.
15. **No mocked integrations in the demo path.** Live data only.
16. **PM-CONTEXT updates with every meaningful outcome.**
17. **`sf` CLI API version pinned to v62.0.** Session 13 finding — org maxes at v66; CLI auto-selects v67 which doesn't exist.

### Design rules
18. **Brand-aligned to onedge.co + user-provided React preview.**
19. **Color system anchored to Tier-0 tokens.**
20. **Typography: Inter primary + system humanist stack fallback.**
21. **Calm whitespace + opt-in depth.**
22. **Motion only when meaningful.** Framer-motion fade-and-lift on account switch. Pulse Bar breathing on agent processing.
23. **Outcome-led, not workflow-led.**
24. **The hero is the action queue + the situational hero card.**
25. **Agent presence: Pulse Bar (Breathing).** Locked Session 10.
26. **Tinted-shadow restricted to hero card + brand-mark tile only.**
27. **Conic-gradient health ring is 270° max, not 360°.**
28. **Visual design ships in Phase 2 / 2.5, not Phase 4.**

### Posture rules
29. **Resourceful open-source posture.**
30. **Maintenance-friendly stack.**
31. **Signal Source Adapter pattern.**
32. **Scope freeze with weekly check-ins.** Phase 1 scope closed. Friday gate-reviews enforce.
33. **Test-account denylist.** `Test Account` (id `0016S00003UGpijQAD`) and any future test accounts excluded from Layer 8 metrics + demo paths. Implemented in spec 012 SFDC adapter; PR-review enforced.
34. **PM stop-and-review at Gate 1.** Per §4.15. Week 1 closure is not self-assessed.

---

## 7. How to handle Claude Code reports

1. Verify DoD evidence.
2. Read output carefully — drift, scope creep, unverified assumptions, white-label violations.
3. Re-check §13 EDGE coverage map and §14 frozen scope list.
4. Re-check brand alignment — Tier-0 tokens; Pulse Bar (Breathing) correct.
5. Re-check signal inspectability — every signal-detection mechanism has a Signal Definition Library entry.
6. **For Phase 4 reports:** verify commit messages reference spec IDs (§4.13). Audit a sample.
7. **For Friday gate reports:** verify gate criteria literally pass (yes/no), not "things look good."
8. Surface concerns explicitly.
9. Propose the next prompt (or gate-decision: proceed / recover / cut).
10. Update PM-CONTEXT directly.

---

## 8. Decision log

| Date | Decision | Rationale | Made by |
|------|----------|-----------|---------|
| 2026-05-19 | Product name: EDGE Pulse | Brand fit | User accepted PM rec |
| 2026-05-19 | Graphiti as memory engine | Bi-temporal model | PM rec, user approved |
| 2026-05-19 | Graph architecture Option C | Temporal + lite skills | PM rec, user approved |
| 2026-05-19 | Fast-stack-first, AWS later | Don't optimize prematurely | PM rec, user approved |
| 2026-05-19 | White-label rule | Product positioning | User declared |
| 2026-05-19 | Design lock as hard gate | User's prior pain | User declared |
| 2026-05-19 | PM owns PM-CONTEXT maintenance | Role clarity | User declared |
| 2026-05-19 | Phase 1 closed. rm-intelligence-agent = Pulse v0. | Highest-relevance reference | PM verdict |
| 2026-05-19 | Activepieces vs n8n deferred to spike | Cost-conscious | User declared (locked Session 11) |
| 2026-05-19 | LangGraph as agent-framework direction | Production-mature; MIT | PM rec, user accepted |
| 2026-05-19 | Resourceful open-source posture | Internal tool | User declared |
| 2026-05-19 | rm-intelligence-agent's HTML as fallback | High-stakes safety | PM rec |
| 2026-05-19 | Migrate Pulse's own prompts to Claude | White-label + Anthropic primary | PM rec, user approved |
| 2026-05-19 | EDGE Requirements Coverage Map locked into §13 | Floor of scope | User declared |
| 2026-05-19 | Demo deadline: 4 weeks (2026-06-16) | User locked (later extended) | User declared |
| 2026-05-19 | Demo data: live, no snapshot, no PHI redaction | No PHI in calls; AWS-owned | User declared |
| 2026-05-19 | HIPAA demoted to standing standard | No PHI in RM calls | User declared |
| 2026-05-19 | SFDC schema = Phase 2 spike | Schema uncertainty | User declared |
| 2026-05-19 | Demo signal sources: Chorus + SFDC initially | 4-week deadline | PM rec, accepted |
| 2026-05-19 | SFDC write-back: read-only ingest; writes via Action Queue | Safer + HITL | User accepted PM rec |
| 2026-05-19 | Zoom feasibility spike (no-build) | Surface surprises | User accepted PM rec |
| 2026-05-19 | Auth-key discipline | Standard dev practice | User declared |
| 2026-05-19 | Brand alignment locked to onedge.co. Linear+Granola REVERSED. | CEO visually-driven | User declared |
| 2026-05-19 | Tier-0 Design Language System added | Visual drift prevention | PM rec |
| 2026-05-20 | Spike 3 confirmed-GO | Live verification | Claude Code, PM verified |
| 2026-05-20 | Q114, Q115, Q116 filed | Phase 4 day-1 prevention | Claude Code findings |
| 2026-05-20 | Visual direction reference: user's React preview | Concrete beats abstract | User declared |
| 2026-05-20 | Information density: opt-in depth | Cognitive-load discipline | User accepted PM rec |
| 2026-05-20 | Agent presence direction: "alive presence" | Distinctive, not chat-ified | User declared |
| 2026-05-20 | Pulse Bar (Breathing) hybrid | Global presence + aliveness + no persona | User direction; PM committed |
| 2026-05-20 | Tier-0 resolutions: 270° conic; ghost token; tinted-shadow restricted; Inter primary | Defended in Session 10 | PM committed |
| 2026-05-20 | opportunity-tracker as Phase 1 signal source | High-CEO-impact | User declared; PM scoped |
| 2026-05-20 | Talent Case descriptions as Episodes | Qualitative narrative enriches memory | PM rec, user accepted |
| 2026-05-20 | `client_termination_pattern` as Skill 10 variant | Cross-temporal pattern | PM rec, user accepted |
| 2026-05-20 | SFDC as canonical system-of-record | Framing | User declared |
| 2026-05-20 | No black-box detection; Signal Definition Library required | Inspectability | User declared |
| 2026-05-20 | Layer 8 Option B locked | "Get smarter over time" demo answer | User per "go with your lean" |
| 2026-05-20 | ADR-002 pre-locked: Activepieces self-hosted | Familiarity + license + ops fit | PM committed |
| 2026-05-20 | Demo date relocked: 2026-06-30. Scope frozen. | Scope expansion; extension preferred | User declared |
| 2026-05-20 | Constellation promoted to fully-in-scope nav surface | Date extension provided budget | User direction |
| 2026-05-20 | opp-tracker LLM stays on OpenAI (Mitigation A) | Decision 13 governs Pulse's own LLM | PM rec |
| 2026-05-20 | Static Enterprise EBR-tie-in copy (Mitigation B) | Saves ~0.5d | PM rec |
| 2026-05-20 | ADR-001: Async-everything FastAPI | Simpler topology; Langfuse catches drift | Claude Code |
| 2026-05-20 | ADR-002 locked: Activepieces on Fly.io ~$2-3/mo | Documented deployment | Claude Code |
| 2026-05-20 | ADR-003: Langfuse self-hosted on Fly.io | Self-hostable; AWS-migration-friendly | Claude Code |
| 2026-05-20 | Signal Definition Library: 14 definitions; CI-validated | No black-box detection | Claude Code |
| 2026-05-20 | Build plan: 47 specs, 4.0d buffer. Spec-ID traceability. | Phase 3 closure | Claude Code |
| 2026-05-20 | Week-1 stop-and-PM-review gate | Foundation-week criticality | PM declared |
| 2026-05-20 | Demo storyboard anchors swapped: DHR + Mendota + Cirventis | Recon Session 13 | User accepted PM rec |
| 2026-05-20 | `affectlayer__Engagement__c` removed from Phase 1 scope | Empty org-wide | Recon-driven |
| 2026-05-20 | Spec 045a added: Synthetic action-outcome seed (0.5d) | Mechanism 3 historical chains empty | Recon-driven |
| 2026-05-20 | Production-org development for Phase 4 | §6 rule 6 is the protection | User declared |
| 2026-05-20 | `sf` CLI API v62.0 pin (rule §6 #17) | Org maxes at v66 | Recon-driven |
| 2026-05-20 | Test-account denylist (rule §6 #33) | `Test Account` is #1 by RM_Outreach | Recon-driven |
| 2026-05-20 | RM_Outreach__c reframed as young (Feb 2026), not sparse | User-provided operational context | User declared |
| 2026-05-20 | **Phase 4 GREEN-LIT.** Build plan accepted with three watched concerns and two Day-1 housekeeping items. Build starts Thu 2026-05-22. | Build plan is audit-grade; risks named with mitigations; gates testable; critical path explicit | PM declared |
| 2026-05-20 | **§4.15 added: PM stop-and-review at Gate 1.** Claude Code stops at Friday May 30 gate, posts report, waits for PM verification before Week 2. | Week-1 closure is load-bearing for the entire phase | PM declared |
| 2026-06-02 | **Zoom Signal Source Adapter pulled forward from v1.5+.** `core/adapters/zoom.py` + `core/zoom/sync.py` built; 5,233 episodes in `pulse.episodes`. Was §12 #8 (after Phase 1 demo). User-directed during Phase 4 build. PM to confirm §14/§12 alignment. | User asked about Zoom sync during build; real data volume justified the pull-forward | User-directed; Claude Code built |
| 2026-06-02 | **Gmail direct sync added as supporting infrastructure.** `core/google/gmail_sync.py` + `core/google/auth.py` + `core/google/account_matcher.py`. Feeds episodes from authenticated RM inboxes into `pulse.episodes`. Not a named spec; extends spec 043 (OAuth) and spec 014 (Calendar adapter). | Email signals from RM inbox complete the contact-communication picture; user-directed | User-directed; Claude Code built |
| 2026-06-02 | **SF Contacts sync added.** `pull_and_upsert_contacts()` in `core/salesforce/sync.py`; `pulse.sf_contacts` table. Required for email → SF account matching in Gmail and Calendar pipelines. Not a named spec. | Without contacts, email-to-account matching has no lookup table | Claude Code initiated; user-approved |
| 2026-06-02 | **Google OAuth scopes extended.** `auth_google.py` scopes now include `gmail.readonly` + `calendar.readonly`. Users who authenticated before this change must re-authenticate. | Scope extension required to enable Gmail+Calendar pipelines | Claude Code |
| 2026-06-02 | **Constellation wired to real SF data (628 accounts).** `buildConstellationGraphFromReal()` added to `fixtures.ts`; `ConstellationPage` fetches from `/accounts?page_size=1000`. Replaces 14 hardcoded demo accounts. | Demo must show real book of business | User-directed; Claude Code built |
| 2026-06-02 | **owner_id added to accounts API.** `AccountSummaryDTO.owner_id` added; SELECT updated; used for Constellation RM → account mapping. | Constellation real-data wiring required owner_id to map accounts to RMs | Claude Code |

---

## 9. Session log

### Sessions 1–13 — 2026-05-19/20
Pre-Research → Research closed → Design Phase entry → Coverage audit → Lock-first items resolved → Brand alignment → Spike 3 confirmed-GO → Visual direction lock → Phase 2.5 closed → Agent indicator + opportunity-tracker scope → Date relocked + scope frozen + Constellation promoted + Layer 8 + signal library + ADR-002 → Phase 3 Planning closed → Demo data recon. (Full log preserved in repo history.)

### Build Sessions 15–NN — 2026-05-22 through 2026-06-02
**Phase:** Phase 4 Build — Weeks 1 and 2
**What happened:** Phase 4 kicked off Thu 2026-05-22. Build progressed far ahead of the published schedule — all specs 001-045 implemented across the two-week period.

Key milestones:
- **Bootstrap + memory layer + all adapters done in Week 1.** Specs 001–016 complete. Kuzu graph, named retrievers, event log, policy module, kill switch all live.
- **All 11 skills built and tested.** Specs 017–028 done. Skills 01–11 each have implementation + unit + integration test files.
- **All front-end surfaces built.** Specs 034–041: Action Queue, Hero card, Per-Account view, Pulse Bar, Constellation, CEO View, Admin surfaces (Signal Performance + Outcome Tracking). RBAC + OAuth (spec 042–043) done.
- **Layer 8 done.** Specs 044–045: Signal Performance metrics UI + Outcome Tracking UI + `core/outcomes/watchers.py`.
- **v1.5+ pull-forwards.** Zoom Signal Source Adapter (was §12 #8) built and live with 5,233 episodes. Gmail direct sync + SF Contacts sync added to feed email-matching pipeline.
- **Constellation wired to real SF data.** 628 live accounts rendered in force-directed graph. `buildConstellationGraphFromReal()` bridges DEMO_USERS.sfUserId → RM nodes → account nodes.
- **Google OAuth fixed + extended.** Python 3.9 type annotation bug (`str | None` → `str = Query(default=None)`) fixed; callback wrapped in try/except; scopes extended to include `gmail.readonly` + `calendar.readonly`.
- **SF Contacts sync live.** `pull_and_upsert_contacts()` added; `pulse.sf_contacts` table in schema; enables email-to-account matching for Gmail/Calendar pipelines.

**Remaining before Demo Day:**
- Spec 046: Demo data priming script
- Spec 047: Demo HTML fallback verification
- Fix Chorus meeting endpoint (abbreviated sfdc_id matching)
- End-to-end skill → action queue → dispatch validation on real data

**Concerns surfaced:**
- Zoom was v1.5+ per §12 #8; pull-forward was user-directed but not formally scope-adjusted in §12 or §14. PM should decide: incorporate into Phase 1 frozen scope (update §14) or leave as acknowledged deviation.
- Gmail direct sync and SF Contacts sync were not in the original 47 specs. They're supporting infrastructure for Calendar signal source (spec 014) and were user-directed. Same §14 treatment question.
- Meetings endpoint empty issue (Chorus abbreviated IDs) needs a fix before Gate 3 criteria are met.

**Decisions:** entries 59–65 (see §8).
**Open after session:** Spec 046 + 047; meetings endpoint fix; Gate 2 stop-and-report due Fri June 6.

### Session 14 — 2026-05-20
**Phase:** Phase 4 green-light review → Phase 4 kickoff
**What happened:** PM read the build plan (`02_planning/build-plan.md`) in full. 385 lines. Verdict: **green-light Phase 4.**

The plan is audit-grade: week-by-week schedule with named specs per day, testable Friday gate criteria, explicit critical-path dependencies, risk register with concrete mitigations, parallel-track documentation, and honest Phase-3-discovered additional risks (Activepieces operational learning curve + Constellation library pick).

PM surfaced three watched concerns (none blocking): (1) Memorial Day May 26 makes Week 1 a 4-day week, tight but doable; (2) spec 044 starting Monday Week 6 is tight against demo prep; (3) spec 043 OAuth at 0.75d may slip to 1.5d. All three are gate-monitored, not pre-cut.

PM also flagged two Day-1 housekeeping items: (a) spec 045a (Session 13 addition) needs to be folded into spec 045 or documented as a sub-task; (b) Design 12 + specs 046-047 need anchor references updated from Acrisure/Pinnacle → DHR/Mendota/Cirventis. Both are bookkeeping the Phase 4 Day-1 work absorbs.

PM declared §4.15 — Gate 1 (Friday May 30) is a stop-and-PM-review gate, not self-assessed. This is the Week-1-load-bearing-for-the-phase protection (memory pattern from Session 12). Gates 2-5 are also stop-and-report but with lighter PM review unless concerns surface.

User confirmed green-light. PM writes Phase 4 Build prompt for Claude Code. Build begins Thursday 2026-05-22.

**Decisions:** entries 57–58.
**Concerns surfaced:**
- Three Phase 4 watched concerns (Memorial Day, spec 044, spec 043)
- Two Day-1 housekeeping items (spec 045a fold-in, Design 12 + specs 046-047 anchor swap)
- No fundamental issues with the plan
**Open after session:** Phase 4 Build prompt written (paired artifact this session).
**Next session goal:** Claude Code begins Phase 4 build. PM is on-call for any Day-1 blockers + the Friday May 30 Gate 1 stop-and-review.

---

## 10. Memory patterns

- `pm_should_not_over_index_on_enterprise_hygiene_for_internal_tools` — Session 3
- `workflow_engine_and_agent_framework_are_different_layers_dont_collapse_them` — Session 3
- `prior_work_inventory_can_shorten_build_dramatically` — Session 2
- `explicit_coverage_map_prevents_silent_scope_drift` — Session 4
- `audit_before_building_surfaces_imagined_questions_not_real_ones` — Session 5
- `signal_source_adapter_pattern_is_load_bearing_when_scoping_for_a_demo` — Session 5
- `design_language_assumptions_made_without_brand_grounding_are_load_bearing_fragile` — Session 6
- `cheap_spike_converts_assumption_to_measurement_before_planning_locks` — Session 7
- `concrete_design_references_beat_abstract_direction_by_an_order_of_magnitude` — Session 8
- `hybrid_solutions_beat_pure_picks_when_pure_picks_each_have_one_real_cost` — Session 10
- `user_consistently_self-disciplines_scope_to_v1.5_pm_should_pull_forward_small_high_value_items` — Session 11
- `extending_a_deadline_to_protect_scope_quality_is_legitimate_when_paired_with_three_disciplines_otherwise_its_scope_creep_with_extra_steps` — Session 11
- `inspectability_is_a_first-class_product_concern_not_a_nice-to-have` — Session 11
- `spec_id_traceability_in_commit_messages_is_the_audit_chain_that_holds_phase_4_together` — Session 12
- `week_1_of_a_build_phase_is_load_bearing_for_the_whole_phase` — Session 12
- `data_recon_before_build_kickoff_prevents_synthetic_assumption_landing_in_demo` — Session 13
- `findings_can_be_reframed_by_operational_context_pm_should_ask_before_designing_around_them` — Session 13
- `gate_criteria_must_be_testable_yes_no_not_things_look_good` — A gate is only protective if its criteria are unambiguous. "On track" is not a gate; "one end-to-end episode ingestion from Chorus → Graphiti → query demonstrated" is a gate. The build plan's Gate 1 criteria pass this test; PM verifies the same standard holds for Gates 2-5 each Friday. Surfaced Session 14 reviewing the build plan.
- `phase_4_green_light_is_a_one_way_door_treat_pre_flight_concerns_as_blocking_unless_they_explicitly_are_not` — Phase 4 is harder to reverse than any prior phase. Code lands, tests get written, dependencies form. PM read the build plan as if any unresolved concern would compound. Surfaced three (Memorial Day, spec 044, spec 043) and explicitly classified them as watched-not-blocking. The discipline is to name the watched items rather than letting them be silent assumptions. Surfaced Session 14.

---

## 11. Glossary

- **RM, Talent, Book of Business, Customer, Action Queue, Episode, Silent churn signal** — operational
- **Temporal Context Graph, Skills Layer, Account/Talent Relationship Graph** — internal architecture
- **Signal Triangulation** — Chorus → RM_Outreach → Associates → Cases (with Case descriptions + opportunity-tracker)
- **Signal Source Adapter** — Pluggable signal-source interface
- **Pulse v0** — rm-intelligence-agent
- **Demo HTML fallback** — Single self-contained HTML
- **Coverage Map** — §13 of this doc
- **Tier-0 Design Language System** — `01_design/00_design_language.md`
- **Edge brand surface** — onedge.co + user's React preview
- **Alive presence** — Pulse Bar (Breathing). Locked Session 10.
- **Pulse Bar (Breathing)** — Canonical agent-presence indicator
- **Opt-in depth** — Hero + Action Queue default; deeper content on click
- **Signal Definition Library** — `02_planning/signals/`. 14 definitions, CI-validated.
- **Layer 8** — Learning/feedback. Phase 1 ships Option B.
- **Constellation view** — Dedicated nav surface; force-directed graph of book of business
- **Scope freeze** — Phase 1 closed as of Session 11
- **ADR-001 / ADR-002 / ADR-003** — Locked Session 12
- **Spec ID traceability** — Every Phase 4 commit references its spec
- **Week-1 stop-and-PM-review gate** — Foundation week closure requires PM review
- **Demo anchor accounts** — DHR Health Clinics + Mendota Insurance + Cirventis (as Helix display alias)
- **edgesolutions org / v62.0 pin** — Production SFDC org; CLI pinned globally
- **Gate 1 / Gate 2 / Gate 3 / Gate 4 / Gate 5 / Demo Day** — The six Phase 4 milestones

---

## 12. v1.5+ candidates

| # | Item | Filed during | Trigger to revisit |
|---|------|--------------|---------------------|
| 1 | Full ML-driven silent churn signal detection | PM scoping | After 90 days of data |
| 2 | Full skills drift detection | Option C decision | Phase 2 after Phase 1 demo |
| 3 | AWS migration | Infra decision | After demo-validated shape locks |
| 4 | Consolidated agent runtime | Q10 | Phase 1 demo lands |
| 5 | Internal MCP exposure | Q11 | Multiple runtimes need access |
| 6 | Production-grade observability evolution | Q14 | Post-Phase-1 ADR-003 evaluation |
| 7 | Product Adoption Monitor skill | §13 audit | Phase 2 |
| 8 | ~~Zoom Signal Source Adapter~~ **PULLED FORWARD** — built during Phase 4 Week 1–2. `core/adapters/zoom.py` + `core/zoom/sync.py`. PM to update §14 if formally absorbing into Phase 1. | Session 5 | ~~After Phase 1 demo~~ **Done** |
| 9 | Slack Signal Source Adapter | Session 5 | After Phase 1 demo |
| 10 | Jira / Email Signal Source Adapters | Session 5 | After Phase 1 demo |
| 11 | Account-Card Ambient Ring (V3) | Session 10 | If per-account locality felt-need surfaces |
| 12 | Layer 8 Mechanism 2: per-RM preference learning | Session 11 | After modification data accumulates |
| 13 | opportunity-tracker LLM migration to Claude | Session 11 | Org-wide LLM consolidation |
| 14 | Enterprise EBR-tie-in dynamic-date copy | Session 11 | After Phase 1 demo |
| 15 | Dedicated Talent Case Synthesis surface | Session 11 | Post-demo if RM workflow demands |
| 16 | Reason-code-driven analytics across the org | Session 11 | After termination data accumulates |
| 17 | Automatic outcome capture for terminations | Session 11 | After Phase 1 demo |
| 18 | Skill Base Class implementation refactor | Session 11 | If Phase 4 surfaces commonality |
| 19 | `affectlayer__Engagement__c` reactivation if Chorus's SFDC integration starts populating it | Session 13 | If Chorus-SFDC mirror table ever populates |
| 20 | Account-name fuzzy-match disambiguation upgrade (the "15 Pinnacles" problem) | Session 13 | When matcher hits production-tail noise |
| 21 | Sandbox-with-production-data-copy environment | Session 13 | If/when production-org dev becomes a friction point |

---

## 13. EDGE Requirements Coverage Map

Verified Session 12 + Session 13:

| Section | Mapped | Deferred | N/A | Gap |
|---|---|---|---|---|
| §13.2 Workflow 1 — Note Capture | 9/9 | 0 | 0 | **0** |
| §13.3 Workflow 2 — Briefing | 7/7 | 0 | 0 | **0** |
| §13.4 Customer Intelligence Hub | 6/6 | 0 | 0 | **0** (Mendota example now real account, not synthetic) |
| §13.5 RM JD areas | 22/24 | 1 (Product Adoption — §12 #7) | 1 (Implement initiatives — organizational) | **0** |
| §13.6 Pulse exceeds EDGE | 10/10 | 0 | 0 | **0** |
| **Total** | **54/56** | **1** | **1** | **0** |

---

## 14. Frozen Phase 1 scope list (locked Session 11; refined Session 13)

**Anything not on this list is v1.5+.**

### Memory layer
- Three-Graph composition (Temporal Context + Skills Layer lite + Account/Talent Relationship)
- Graphiti as the temporal memory engine (confirmed-GO)
- Kuzu backend with PulseKuzuDriver FTS bootstrap subclass

### Signal sources
- Chorus (call transcripts + structured signals)
- Salesforce: Account, Contact, Opportunity, RM_Outreach__c, Associates__c, Account_Plan__c, **Case including descriptions**
- Calendar
- opportunity-tracker (LinkedIn + Indeed only)
- **REMOVED Session 13:** `affectlayer__Engagement__c`

### Skills (11 total)
- Skills 01–10 + Skill 11 (detect-expansion-intent-from-job-posting)

### Signal Definition Library
- Template + 14 initial definitions (CI-validated)
- `account_silence_pattern_v1` revised Session 13 to include RM_Outreach absence

### UI surfaces
- Three-column hero
- Action Queue
- Per-account view with opt-in depth
- CEO View
- Constellation view (dedicated nav surface)
- Three-tier role model + RBAC
- Submission UI (Slack slash command)
- Signal Performance admin surface (Layer 8 Mechanism 1)
- Outcome tracking admin surface (Layer 8 Mechanism 3, synthetic seed via spec 045a)

### Agent presence
- Pulse Bar (Breathing) on every screen

### Layer 8 — Learning (Option B)
- Mechanism 1: Signal Performance metrics admin surface
- Mechanism 3: Outcome tracking + action effectiveness metrics (synthetic seed via spec 045a)

### Infrastructure (ADRs locked Session 12; production posture Session 13)
- FastAPI service (async-everything per ADR-001) + Postgres + Kuzu
- Activepieces self-hosted on Fly.io (ADR-002)
- Langfuse self-hosted on Fly.io (ADR-003)
- AWS-only hosting + audit log on every action
- Event Log + Reasoning Capture schema (Design 04)
- Production SFDC org (`edgesolutions`, `edgelabs.admin@onedge.co`, API v62.0 pinned)

### Demo deliverables
- Live demo against production Chorus + production SFDC org
- Demo storyboard with DHR Health Clinics + Mendota Insurance + Cirventis (Helix)
- Demo HTML fallback preserved

### Phase 4 Day-1 tasks (baked into specs 001–004 per build plan)
- PulseKuzuDriver FTS bootstrap subclass (Q114) → spec 002
- Model-ID pinning via `core/llm/config.py` (Q115) → spec 003
- `load_dotenv(override=True)` everywhere (Q116) → spec 003
- opportunity-tracker `sf_tasks.push_to_salesforce()` deprecation safety guard (Q121) → spec 004
- `.env.example` populated → spec 001
- Project bootstrap → spec 001
- CI smoke test → spec 001
- `sf` CLI auth-flow validation + API v62.0 pin → spec 001
- Activepieces + Langfuse Fly.io deploys → spec 001
- **Spec 045a folded into spec 045 OR documented as sub-task** (Session 14 Day-1 housekeeping)
- **Design 12 + specs 046-047 anchor references updated to DHR/Mendota/Cirventis** (Session 14 Day-1 housekeeping)

---

*End of PM-CONTEXT.*

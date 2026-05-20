# Phase 3 — §13 / §14 Scope Verification

**Purpose:** Phase 3's final gate — every PM_CONTEXT §14 frozen scope line maps to ≥1 Phase 4 spec, and every §13 EDGE Coverage row remains covered. Authority: PM_CONTEXT §14 + §13.

---

## §14 Frozen scope verification

### Memory layer

| §14 scope line | Spec(s) |
|---|---|
| Three-Graph composition (Temporal + Skills lite + Account/Talent Relationship) | 005 |
| Graphiti as temporal memory engine | 005, 002 |
| Kuzu backend with PulseKuzuDriver FTS bootstrap subclass | 002 |

### Signal sources (Signal Source Adapter pattern)

| §14 scope line | Spec(s) |
|---|---|
| Chorus | 011, 013 |
| Salesforce (full Phase 1 object surface including Case descriptions) | 011, 012 |
| Calendar | 011, 014 |
| opportunity-tracker (LinkedIn + Indeed only) | 011, 015, 016 |

### Skills (11 total)

| §14 scope line | Spec(s) |
|---|---|
| Skill 01 — detect-talent-signal | 020 |
| Skill 02 — prepare-customer-meeting-brief | 018 |
| Skill 03 — renewal-watcher | 019 |
| Skill 04 — talent-care | 021 |
| Skill 05 — escalation-router | 022 |
| Skill 06 — advocacy | 023 |
| Skill 07 — recognition | 024 |
| Skill 08 — onboarding | 025 |
| Skill 09 — coaching-signal-router | 026 |
| Skill 10 — cross-account-pattern-finder (incl. client_termination_pattern) | 007, 027 |
| Skill 11 — detect-expansion-intent-from-job-posting | 028 |

### Signal Definition Library

| §14 scope line | Spec(s) / artifact |
|---|---|
| Template at `02_planning/signal_definition_template.md` | exists |
| Initial 10–14 signal definitions in `02_planning/signals/` | exists (14 definitions) |
| No black-box detection — every signal has an inspectable definition | 017 (runtime enforces) |

### UI surfaces

| §14 scope line | Spec(s) |
|---|---|
| Three-column hero | 034, 035, 036, 037 |
| Action Queue (two-layer explainability, tier-aware approval matrix, modify/approve/reject, kill switch) | 031, 035, 009, 010 |
| Per-account view with opt-in depth | 036, 037 |
| CEO View (purple-rich, narrative voice) | 040 |
| Constellation view as dedicated nav surface | 041 |
| Three-tier role model + Overall view with RBAC | 042 |
| Submission UI (Slack slash command in v1) | 039 |
| Signal Performance admin surface (Layer 8 Mechanism 1) | 044 |
| Outcome tracking admin surface (Layer 8 Mechanism 3) | 045 |

### Agent presence

| §14 scope line | Spec(s) |
|---|---|
| Pulse Bar (Breathing) on every screen | 038 |

### Layer 8 — Learning (Option B)

| §14 scope line | Spec(s) |
|---|---|
| Mechanism 1: Signal Performance metrics admin surface | 044 |
| Mechanism 3: Outcome tracking + action effectiveness metrics | 045 |

### Infrastructure

| §14 scope line | Spec(s) / ADR |
|---|---|
| FastAPI service + Postgres + Kuzu (Phase 1) | 001, 005 |
| Activepieces self-hosted (ADR-002 pre-locked) | ADR-002, 001 |
| Observability backend (Phase 3 picks, ADR-003) | ADR-003 |
| Agent reasoning topology (Phase 3 picks, ADR-001) | ADR-001 |
| AWS-only hosting + audit log on every action | ADR-002 (deployment), 008 (audit) |
| Event Log + Reasoning Capture schema | 008 |

### Demo deliverables

| §14 scope line | Spec(s) |
|---|---|
| Live demo against production Chorus + SFDC data | 046, 048 (storyboard from Design 12) |
| Demo storyboard walks end-to-end with Acrisure + Pinnacle | Design 12 + 046 + 047 |
| Demo HTML fallback (`data/demo.html` from rm-intelligence-agent, preserved) | 047 |

### Phase 4 Day-1 tasks (baked into build plan)

| §14 scope line | Spec(s) |
|---|---|
| PulseKuzuDriver FTS bootstrap subclass (Q114) | 002 |
| Model-ID pinning via `core/llm/config.py` (Q115) | 003 |
| `load_dotenv(override=True)` everywhere (Q116) | 003 |
| opportunity-tracker `sf_tasks.push_to_salesforce()` deprecation safety guard (Q121) | 004 |
| `.env` in `.gitignore`, `.env.example` populated | 001 |
| Project bootstrap (Python venv, FastAPI skeleton, Postgres + Kuzu init, pytest) | 001 |
| CI smoke test | 001 |
| SFDC sandbox refresh (Q21) resolved | Day-1 user task (build-plan §3 item 8) |

**§14 verification: every scope line maps to at least one spec. Zero gaps.**

---

## §13 Coverage re-verification (Phase 3 view)

§13.5 + §13.6 received new rows Session 11; this walk verifies all §13.2–§13.6 rows remain covered. Cross-reference with `01_design/00_coverage_walk.md` (Phase 2 audit) — Phase 3 specs reaffirm the design-level coverage at the build-plan level.

### §13.2 Workflow 1

| EDGE ask | Spec |
|---|---|
| Meeting ends → webhook fires → workflow activates | 011, 013, ADR-002 |
| Submit voice note or text summary (30 sec) | 039 |
| Workflow captures meeting transcript | 013 |
| Sentiment score (1–10) extraction | 020 (Skill 01 produces multi-axis vector; composite 1-10 for UI) |
| Theme tags | 020 (Skill 01) |
| Urgency flag | 020 + Design 04 urgency field |
| 2-sentence summary | 020 |
| Push structured data to Salesforce via API | 032 (only via Action Queue per §6 rule 6) |
| Per-customer persistent knowledge thread | 005, 029 |

### §13.3 Workflow 2

All 7 rows covered by spec 018 (Skill 02 brief) + spec 014 (Calendar adapter).

### §13.4 Customer Intelligence Hub queries

All 6 example queries covered by retrievers (spec 006), Skill 01 (spec 020), Skill 06 (spec 023), Skill 10 (spec 027), Constellation/CEO View (specs 040/041).

### §13.5 RM JD areas

24 rows; 22 covered Phase 1, 1 deferred (Product Adoption Monitor → §12 #7), 1 N/A (Implement initiatives — organizational, not product).

**New Session 11 row** (Proactive customer-side expansion-signal detection) → spec 028 (Skill 11) + spec 015 (opp-tracker adapter).

### §13.6 Pulse-exceeds-EDGE rows

All 10 rows covered. Session 11's new row #10 (opp-tracker as expansion-intent signal source) → specs 015, 016, 028.

---

## Coverage verification result

**§14: 0 gaps.** Every frozen-scope line has at least one Phase 4 spec.
**§13.2: 9/9 covered.**
**§13.3: 7/7 covered.**
**§13.4: 6/6 covered.**
**§13.5: 23/24 covered + 1 deferred + 1 N/A — unchanged from Phase 2 audit + new Session 11 row covered.**
**§13.6: 10/10 covered (10 includes Session 11 addition).**

**Phase 3 → Phase 4 gate cleared.**

# EDGE Pulse — Build Plan (Phase 4)

**Phase:** 3 — Planning output; Phase 4's canonical build-plan-of-record
**Phase 4 window:** 2026-05-21 → 2026-06-30 (~30 working days; 6 weeks; weekly Friday gate-reviews)
**Scope status:** **FROZEN** (per PM_CONTEXT §14, locked Session 11)
**Authority:** This file references designs (`01_design/`), ADRs (`02_planning/architecture_decisions/`), signal definitions (`02_planning/signals/`), and per-spec work units (`02_planning/specs/NNN-*.md`). Phase 4 commits must reference a spec ID.

---

## §1 Plan overview

### Phase 4 timeline + spec totals

- **Working days:** 30 (Mon-Fri, 2026-05-21 through 2026-06-30; +1 weekend day if needed)
- **Spec count:** 47 specs in `02_planning/specs/`
- **Summed estimated effort:** 26.0 effective working days
- **Buffer:** 4.0 days distributed across the six weeks (~0.7 days/week). Per §6 rule 31, buffer is for *surprises within scope*, not for additions.

### Three ADRs locked

- **ADR-001 — Agent reasoning topology:** **Option A** (async-everything FastAPI with 60s middleware timeout + per-LLM-call timeout + cancellation propagation). Long-running scheduled aggregations (Skill 10 weekly; CEO View weekly) run *outside* the FastAPI request loop. Reversible to Option B (queue + worker) at a measured trigger.
- **ADR-002 — Workflow engine:** **Activepieces Community Edition, self-hosted on Fly.io.** Shared Supabase Postgres with `pulse`, `activepieces`, `langfuse` schemas. Seven Phase 1 flows committed to `pulse_workflows/`.
- **ADR-003 — Observability:** **Langfuse, self-hosted on Fly.io.** Co-located with Activepieces; ~$2-3/mo additional. Decorators on three Python modules (`core/agent/runner.py`, `core/memory/retrievers.py`, `core/llm/client.py`). Cross-linked to event log via `trace_id`.

### Critical-path summary (full schedule §4 below)

Critical path: **bootstrap → memory layer → SFDC Signal Source Adapter → Event Log → Skill 02 (one end-to-end skill) → Action Queue API → Front-end shell → Action Queue UI → Demo storyboard end-to-end on real data**.

The single hardest-to-recover-from slippage point is **end of Week 1**: bootstrap + memory layer + first adapter must be functional. If Week 1 closes without an end-to-end "ingest one Chorus episode → query Graphiti → retrieve context" demonstration, Week 2's parallel skill-development blocks become serial, eating buffer.

### Parallel work tracks (Phase 4)

Three tracks run mostly in parallel after Week 1:

- **Track A — Backend (ingestion + skills + dispatch)** — specs 005–033. Highest critical-path concentration.
- **Track B — Front-end (UI surfaces)** — specs 034–041. Can start in earnest Week 3 once Action Queue API is responding.
- **Track C — opportunity-tracker integration + matcher precision fix** — specs 015, 016. Runs in parallel with Track A in Weeks 1-2 because it touches a separate codebase. Independent of front-end.

A single dev in Phase 4 will swap between tracks; the tracks are documented to make the swap deliberate rather than implicit.

### Risk register summary (§6 below)

Top 5 risks, in order: **Q21 SFDC sandbox refresh**, **ADR-001 async correctness**, **live-data demo prerequisites**, **Layer 8 outcome attribution latency**, **scope-freeze pressure under the weekly gate**. Detailed mitigations in §6.

---

## §2 Work unit specs

Specs are listed in execution order. Each spec lives at `02_planning/specs/NNN-<name>.md`.

### Foundations (Day-1, Week 1)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 001 | Project bootstrap — venv, FastAPI skeleton, Postgres + Kuzu init, pytest, CI smoke test | 1.0d | §14 Infrastructure |
| 002 | Day-1 task: PulseKuzuDriver FTS bootstrap subclass | 0.25d | Q114 / §14 |
| 003 | Day-1 task: Model-ID pinning module + `load_dotenv(override=True)` discipline | 0.25d | Q115, Q116 / §14 |
| 004 | Day-1 task: opportunity-tracker `sf_tasks.push_to_salesforce()` deprecation guard | 0.25d | Q121 / §14 |
| 005 | Three-Graph composition: Kuzu schema + entity/edge types + namespaces | 1.5d | Design 01 |
| 006 | Named retrievers: get_customer_context / get_talent_context / get_rm_context | 1.0d | Design 01 |
| 007 | Cross-account retriever (Q77 — scheduled before Skill 10) | 0.5d | Design 01 / Q77 |
| 008 | Event Log + Reasoning Capture schema + emitter | 1.0d | Design 04 |
| 009 | Policy module + tier-aware approval matrix | 0.75d | Design 04, §6 rule 4 |
| 010 | Kill switch + admin config plumbing | 0.25d | Design 04 |

### Signal Source Adapters (Weeks 1-2)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 011 | Adapter contract + Episode envelope (base class) | 0.5d | Design 02 |
| 012 | SFDC Signal Source Adapter (read-only; full Phase 1 object surface including Case descriptions per Decision 35) | 2.0d | Design 02, §14 Signal sources |
| 013 | Chorus Signal Source Adapter | 0.75d | Design 02 |
| 014 | Calendar Signal Source Adapter (Google/MS — provider determined by Q33/Q23) | 0.75d | Design 02 |
| 015 | opportunity-tracker Signal Source Adapter (Postgres polling + Activepieces flow) | 1.0d | Spike 4, Design 02 |
| 016 | opportunity-tracker matcher precision fix (catalog schema upgrade + AI prompt + source narrowing) | 1.0d | Spike 4 §Q2 |

### Signal Definition Library runtime (Week 2)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 017 | Signal Definition Library loader + runtime (loads `02_planning/signals/*.md` definitions, evaluates against episodes) | 1.0d | §6 rule 8, §14 |

### Skills (Weeks 2-3)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 018 | Skill 02 — prepare-customer-meeting-brief (one of the two end-to-end Week-2 skills) | 1.0d | Design 05 + skill 02 |
| 019 | Skill 03 — renewal-watcher (the second Week-2 end-to-end skill) | 1.0d | Design 05 + skill 03 |
| 020 | Skill 01 — detect-talent-signal (signal extraction) | 1.0d | Design 05 + skill 01 |
| 021 | Skill 04 — talent-care | 0.5d | Design 05 + skill 04 |
| 022 | Skill 05 — escalation-router | 0.75d | Design 05 + skill 05 |
| 023 | Skill 06 — advocacy | 0.5d | Design 05 + skill 06 |
| 024 | Skill 07 — recognition | 0.5d | Design 05 + skill 07 |
| 025 | Skill 08 — onboarding | 0.5d | Design 05 + skill 08 |
| 026 | Skill 09 — coaching-signal-router | 0.5d | Design 05 + skill 09 |
| 027 | Skill 10 — cross-account-pattern-finder (with `client_termination_pattern` variant per Decision 36) | 1.0d | Design 05 + skill 10 |
| 028 | Skill 11 — detect-expansion-intent-from-job-posting | 0.75d | Design 05 + skill 11, Spike 4 §Q4 |

### Per-Profile + Health (Week 3)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 029 | Per-Profile Markdown Layer (loader, regenerator, override semantics) | 1.0d | Design 06 |
| 030 | Dual-Sided account health rollup | 0.75d | Design 07 |

### Action Queue + Dispatch + Outcomes (Week 3-4)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 031 | Action Queue API (back-end routes: list/approve/modify/reject/expire) | 1.0d | Design 03 |
| 032 | Action dispatch handlers (email via Gmail/Outlook OAuth; SFDC Task create; Calendar hold suggestion) | 1.0d | Design 03 |
| 033 | Outcome detection watchers (email reply / SFDC Task closed / Chorus EBR detection) | 0.75d | Design 03 |

### Front-end (Weeks 3-4)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 034 | Front-end shell — React + Vite + Tailwind + Tier-0 token plumbing | 0.75d | Design 11 ADR-005, Tier-0 |
| 035 | Action Queue UI (cards, ranking, opt-in depth, inline-tag-voice renderer) | 1.5d | Design 03 |
| 036 | Situational Hero card UI (per-account deep view, conic-gradient health ring) | 1.0d | Tier-0 §8.7/§8.8 |
| 037 | Per-Account view UI (signal vector, verified themes, meeting brief on opt-in click) | 0.75d | Tier-0, Design 06 |
| 038 | Pulse Bar (Breathing) implementation (Tier-0 §8.14) | 0.5d | Tier-0 §8.14, §6 rule 24 |
| 039 | Submission UI (Slack slash command per §14 / §13.2) | 0.75d | §13.2 |

### CEO View + Constellation + Auth (Week 4-5)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 040 | CEO View page (purple-rich; weekly composer; demo-HTML-fallback compatible renderer) | 1.5d | Design 08 |
| 041 | Constellation view (force-directed; sized by placements; colored by health; clickable to account) | 2.0d | §14 (Decision 38) |
| 042 | Three-Tier Role Model + RBAC enforcement | 0.75d | Design 09 |
| 043 | OAuth (Google Workspace) + Supabase Auth + auth chokepoint | 0.75d | Design 09 ADR-006 |

### Layer 8 (Week 5)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 044 | Layer 8 Mechanism 1 — Signal Performance metrics admin surface | 1.5d | Decision 37, §14 |
| 045 | Layer 8 Mechanism 3 — Outcome tracking + action effectiveness metrics | 1.0d | Decision 37, §14 |

### Demo (Week 6)

| ID | Title | Effort | Maps to |
|---|---|---|---|
| 046 | Demo data priming script (synthetic seed if real data is sparse) | 0.5d | Design 12 |
| 047 | Demo HTML fallback verification (rm-intelligence-agent renderer reuse against Tier-0 tokens) | 0.5d | Design 12, Decision 12 |

**Total: 26.0 effective working days against 30 working-day window → 4.0 days distributed buffer.**

(Day-1 tasks 002, 003, 004 are listed as specs for traceability but they execute on Day 1 alongside spec 001; their effort is parallel-overlapped, accounted for in the headline 26.0.)

---

## §3 Day-1 Phase 4 task list

Before any feature work begins (the morning of 2026-05-21):

1. **PulseKuzuDriver FTS bootstrap subclass (Q114).** Per spec 002. Subclass `KuzuDriver`; in `__init__` run `INSTALL FTS; LOAD EXTENSION FTS;` + 4 `CREATE_FTS_INDEX` statements. Tested by re-running the Spike 3 harness — 8 EDGE-shaped synthetic episodes ingest without the FTS error.
2. **Model-ID pinning module (Q115).** Per spec 003. Create `core/llm/config.py` with dated Anthropic model IDs (`claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`). Never use `-latest` aliases.
3. **Environment loading discipline (Q116).** Per spec 003. Use `load_dotenv(override=True)` everywhere in startup paths.
4. **opportunity-tracker safety guard (Q121).** Per spec 004. Add an explicit deprecation docstring + environment-variable guard on `opportunity-tracker/src/sf_tasks.py::push_to_salesforce()` that raises `RuntimeError` unless `PULSE_ALLOW_OPP_TRACKER_SFDC_WRITE=true` is set. This is upstream — a PR against the opportunity-tracker repo, not Pulse's repo.
5. **`.env.example`** at project root listing every required key:
   - `ANTHROPIC_API_KEY` (Phase 4 day-1)
   - `OPENAI_API_KEY` (embedder per Spike 3 §C)
   - `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN` *or* `sf` CLI auth path
   - `CHORUS_API_TOKEN`
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
   - `ACTIVEPIECES_API_URL`, `ACTIVEPIECES_API_TOKEN`
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (Skill 04/07 RM-mailbox sends; Spec 043 auth)
   - `PULSE_INTERNAL_API_TOKEN` (shared-secret between Activepieces and FastAPI per ADR-002)
6. **Project bootstrap.** Per spec 001. Python 3.12 venv; FastAPI skeleton with `/health`; Postgres connection (Supabase) + Kuzu local file path; pytest skaffold; lint (ruff) + type-check (pyright) config; `pre-commit` hook.
7. **CI smoke test.** Push hello-world commit that runs lint + test + the Spike 3 harness re-execution. CI must go green Day-1.
8. **SFDC sandbox refresh (Q21).** User task. Scheduled for Day-1 morning. Specs that depend on full schema describe (Q58, Q61, Q71, Q72, Q86 — note: Q22 already resolved) are gated on this completing — flagged on each affected spec.
9. **Activepieces self-hosted deploy on Fly.io.** Per ADR-002. `flyctl launch` + secrets configuration + first flow (`chorus_engagement_completed`) deployed and pointing at the FastAPI `/webhooks/chorus` endpoint.
10. **Langfuse self-hosted deploy on Fly.io.** Per ADR-003. Co-located with Activepieces; `LANGFUSE_*` env vars wired into Pulse's FastAPI service.

---

## §4 Critical-path schedule

### Week-by-week cadence with Friday gate-review markers

```
WEEK 1 — May 22-28  (Day-1: Thu May 22; gate Fri May 29 → next week begins Mon May 26 if Memorial Day; adjust)
==================================================================================
Mon Tue Wed | spec 001 Project bootstrap + Day-1 tasks 002/003/004
Wed Thu     | spec 005 Three-Graph composition
Thu Fri     | spec 011 Adapter contract
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ GATE 1: bootstrap green; one-end-to-end episode ingestion    ║
             ║ from Chorus → Graphiti → query demonstrated.                 ║
             ║ Q21 sandbox refresh resolved.                                ║
             ╚══════════════════════════════════════════════════════════════╝

WEEK 2 — May 29 - Jun 4
==================================================================================
Mon Tue     | spec 012 SFDC Adapter (largest single adapter spec; 2.0d)
Wed         | spec 013 Chorus Adapter
Wed         | spec 014 Calendar Adapter (parallel — different files)
Thu         | spec 015 opportunity-tracker Adapter + spec 016 matcher precision fix
Thu         | spec 006 retrievers + spec 007 cross-account retriever
Fri         | spec 008 Event log + spec 009 Policy module + spec 010 kill switch
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ GATE 2: all 4 Signal Source Adapters live; events emitting;  ║
             ║ retrievers responsive; policy module taking decisions.       ║
             ║ Skill 02 + Skill 03 to start Mon Week 3.                     ║
             ╚══════════════════════════════════════════════════════════════╝

WEEK 3 — Jun 5-11
==================================================================================
Mon         | spec 017 Signal Definition Library runtime
Mon Tue     | spec 018 Skill 02 prepare-customer-meeting-brief
Tue Wed     | spec 019 Skill 03 renewal-watcher
Wed         | spec 020 Skill 01 detect-talent-signal
Thu         | specs 021 Skill 04, 022 Skill 05, 023 Skill 06 (each 0.5-0.75d)
Fri         | specs 024 Skill 07, 025 Skill 08, 026 Skill 09 (each 0.5d)
Fri         | spec 029 Per-Profile Markdown Layer (in parallel)
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ GATE 3: Skills 01-09 live end-to-end (signal → skill →        ║
             ║ action-suggested event). Per-Profile Markdown loading.       ║
             ║ Demo-data priming script started.                            ║
             ╚══════════════════════════════════════════════════════════════╝

WEEK 4 — Jun 12-18
==================================================================================
Mon         | spec 027 Skill 10 (with client_termination_pattern variant)
Mon Tue     | spec 028 Skill 11 + spec 030 dual-sided health rollup
Tue Wed     | spec 031 Action Queue API + spec 032 dispatch handlers
Wed         | spec 033 outcome detection watchers
Thu         | spec 034 Front-end shell (Tier-0 token plumbing)
Thu Fri     | spec 035 Action Queue UI (cards, ranking, opt-in depth)
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ GATE 4: all 11 skills live; Action Queue UI rendering        ║
             ║ on real backend data. Inline-tag voice working end-to-end.   ║
             ╚══════════════════════════════════════════════════════════════╝

WEEK 5 — Jun 19-25
==================================================================================
Mon         | spec 036 Situational Hero card UI
Mon Tue     | spec 037 Per-Account view UI + spec 038 Pulse Bar (Breathing)
Tue         | spec 039 Submission UI (Slack slash command)
Wed Thu     | spec 040 CEO View page (purple-rich; weekly composer)
Thu Fri     | spec 041 Constellation view (largest UI spec; 2.0d)
Fri         | spec 042 RBAC + spec 043 OAuth (auth chokepoint)
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ GATE 5: All UI surfaces live. CEO View ready for review.     ║
             ║ Constellation usable. Layer 8 mechanisms wired Mon Wk6.      ║
             ╚══════════════════════════════════════════════════════════════╝

WEEK 6 — Jun 26-30 (5 days; demo on Tuesday Jun 30)
==================================================================================
Mon         | spec 044 Layer 8 Mechanism 1 (Signal Performance) — first half
Mon Tue     | spec 044 Layer 8 Mechanism 1 (continued) + spec 045 Mechanism 3
Tue         | spec 046 Demo data priming + spec 047 Demo HTML fallback verification
Wed         | Demo storyboard end-to-end rehearsal on real data (per Design 12)
Wed Thu     | Bug fixing + performance tuning + demo-day priming check (per Q110)
Thu eve     | Recorded screencast backup per Q111
Fri          ╔══════════════════════════════════════════════════════════════╗
             ║ DEMO DAY: Jun 30, 2026.                                       ║
             ║ Live demo against production data on the locked Tier-0 UI.    ║
             ║ Demo HTML fallback ready in a second tab.                     ║
             ║ Recorded screencast available as third-tier fallback.         ║
             ╚══════════════════════════════════════════════════════════════╝
```

### Friday gate-review checklist (every Friday)

Per §6 rule 31 + §4.12. Each Friday at end-of-day, evaluate:

1. **On track?** Specs scheduled this week completed (✓), partially completed (with cause), or skipped (with cause).
2. **Slip identified?** Single specs slipping into next week is acceptable if absorbed by buffer. Two-spec slip or any critical-path slip → decision required by EOD Friday.
3. **Decision (if slip):** *recover* (work weekend / parallelize / borrow buffer) OR *cut* (move spec to v1.5+; update §14 with a removal entry). **No rolling slips.** Per §6 rule 31.
4. **Buffer remaining:** Update running buffer count. If buffer hits zero before Week 6, force a cut.

### Critical-path dependencies (specs that block others)

- **001 → everything** (bootstrap must complete first)
- **002 → 005** (FTS bootstrap before any Graphiti use)
- **005 → 006 → all skills** (memory layer + retrievers before skills)
- **007 → 027** (cross-account retriever before Skill 10 — Q77)
- **008 → 011 → 012-015** (event log before adapters)
- **017 → all signal-detecting skills (020, 021-027)** (Library runtime before any rule-based signal definitions evaluate)
- **031 → 035** (Action Queue API before UI)
- **034 → 035-041** (front-end shell before any UI surface)
- **031, 032, 033 → 045** (action lifecycle before outcome tracking)

---

## §5 Test discipline (summarized; per-spec specifics in each spec file)

Per §6 rules 10 (no commit without tests) and 14 (no silent failure):

### Test categories

| Category | Coverage target | Scope |
|---|---|---|
| **Unit tests** | ~80% line coverage on logic-bearing code | Every pure function; mocked external dependencies |
| **Integration tests** | Every external integration (SFDC read/write, Chorus pull, Calendar webhook, opportunity-tracker Postgres poll, OAuth flow) | Real where API is stable; mocked at the boundary where instability would cause flake |
| **Golden-trace tests** | Every LLM-using skill + every Signal Definition with LLM mechanism | Record expected reasoning *shapes* (key tokens / structure / outputs), not exact strings, per §6 rule 10 |
| **Signal-definition fixture tests** | Every signal definition in `02_planning/signals/` | Each carries a fixture set (positive examples that should fire; negative examples that shouldn't) — becomes the regression suite when signals are tuned |
| **Demo-path test** | EDGE Workflow 1 + 2 + ≥3 §13.4 Customer Intelligence Hub queries | End-to-end on real data without any spec being skipped or stubbed (§6 rule 15) |
| **Performance smoke tests** | Spike 3 harness re-run | Every CI run; catches Graphiti-related regressions |

### CI policy

- Every PR runs: lint (ruff) + type-check (pyright) + unit + integration tests.
- Merge to main runs: all of the above + Spike 3 harness re-execution.
- Friday-evening cron: golden-trace test suite (~10 minutes; runs against live LLM); results posted to admin Slack channel.

---

## §6 Risk register

### Risk 1 — Q21 SFDC sandbox refresh blocked

**Description.** The SFDC sandbox alias has expired tokens (Spike 1). Full schema describe pass needs the user's manual refresh. Several specs depend on it: 016 (matcher precision fix needs the `Segment__c` value enum), 018-019 (Skill 02 + 03 need confirmed Opportunity.Type values per Q58), 021 (Skill 04 needs Talent contact email source per Q61), 025 (Skill 08 needs Account stage enum per Q71/Q72), 044 (Signal Performance metrics need `Customer_Health__c` picklist enum per Q86).

**Likelihood:** Low — user task; user has been responsive.
**Impact if hits:** Up to 1-2 days of rework if assumed schema mismatches reality.
**Mitigation:** (a) Schedule resolution for Day-1 morning Week 1. (b) Specs that depend flag their assumptions explicitly. (c) If Day-1 doesn't resolve, escalate to user same-day at the Friday Week-1 gate review.

### Risk 2 — ADR-001 async correctness bugs surface late

**Description.** Option A (async-everything) relies on every developer maintaining correctness — no blocking calls, no forgotten `await`, no shared-state deadlocks. The risk surface scales with skill count.

**Likelihood:** Medium — async bugs are real even in disciplined codebases.
**Impact if hits:** ~3 days of refactoring if a fundamental issue surfaces in Week 4-5; potentially demo-blocking if missed until Week 6.
**Mitigation:** (a) ADR-003 (Langfuse) catches async drift early — request traces with stalled spans become visible immediately. (b) Day-1 task adds `asyncio` lint rules (no `time.sleep` in handlers; `asyncio.run` only at script boundaries). (c) Spec 001 includes an async smoke test that runs 50 concurrent requests against a no-op endpoint to catch event-loop blocking early. (d) Migration to Option B is reversible at a measured trigger (per ADR-001).

### Risk 3 — Live-data demo prerequisites missing

**Description.** Demo storyboard (Design 12 + Q109/Q110) assumes Acrisure + Pinnacle exist in production with realistic histories. If they don't, the storyboard scenes 1-3 require synthetic substitutes.

**Likelihood:** Low — both customers are real EDGE accounts; rm-intelligence-agent already pulls their data successfully.
**Impact if hits:** ~0.5 day to wire synthetic substitutes per spec 046 (demo data priming script).
**Mitigation:** (a) Confirm presence with user in Week 1's Friday gate review. (b) Spec 046 builds the priming script to handle synthetic substitution if needed. (c) Demo HTML fallback (spec 047) always works regardless — third-tier safety.

### Risk 4 — Layer 8 outcome attribution latency

**Description.** Mechanism 3 (outcome tracking) depends on observable outcomes from approved actions. Email replies can take days; SFDC Task closures can take weeks. If outcomes lag, the Layer 8 metrics surface looks empty at demo time and the "Pulse gets smarter over time" narrative falls flat.

**Likelihood:** Medium — outcomes inherently lag actions.
**Impact if hits:** Demo Layer 8 surface looks aspirational rather than working.
**Mitigation:** (a) Seed the metrics surface with realistic historical-attribution data from rm-intelligence-agent's existing run history (~3 months back); spec 045 explicitly includes this seeding step. (b) The demo storyboard scene that walks Layer 8 mechanisms (Design 12 Scene 5 implicitly) shows the *architecture* rather than depending on real outcomes accumulating. (c) Mechanism 1 (Signal Performance) accumulates faster than Mechanism 3 (fires-per-day rather than outcomes-per-week); lead with Mechanism 1 in the demo.

### Risk 5 — Scope-freeze pressure under the weekly gate

**Description.** Six weeks of build will surface "we should also…" moments. Even disciplined teams negotiate scope in-build. §6 rule 31 + §4.12 commits to a hard scope freeze with Friday gate reviews, but the human pressure to absorb just-one-small-thing accumulates.

**Likelihood:** High — this happens on every project; the discipline is in the response, not in preventing the urge.
**Impact if hits:** Without discipline, ~2-4 days of v1.5+ items absorbed into Phase 1 over six weeks → demo slips.
**Mitigation:** (a) PM enforces at every Friday gate (§4.12). (b) Standing reminder text in each gate-review summary: "anything new goes to v1.5+ automatically." (c) Memory pattern `extending_a_deadline_to_protect_scope_quality_is_legitimate_when_paired_with_three_disciplines` is the explicit anchor — date is already extended, scope is closed.

### Additional surfaced during Phase 3 planning

**Risk 6 — Activepieces self-hosted operational learning curve.**
- Description: ADR-002 picks Activepieces partly on user-side familiarity (Vercel / GitHub Actions), but Activepieces specifically is new. Deploying it on Fly.io + writing the first 7 flows is ~0.5 day of estimated work; if the operational surface surprises, it could be 1-1.5 days.
- Mitigation: Spec 001's bootstrap includes Activepieces deploy as a Day-1 task; surprises surface immediately rather than late.

**Risk 7 — Constellation view (spec 041) is 2.0 days — the largest single UI spec.**
- Description: Force-directed graph rendering with clickable navigation + health-coloring + size-by-placements isn't trivial. The 2.0-day estimate assumes a library like `d3-force` or `react-force-graph` carries 60%+ of the work.
- Mitigation: Spec 041 documents the library pick at spec-author time; if exploration in Week 5 reveals the chosen library isn't a good fit, the constellation view degrades gracefully (per spec 041 DoD: minimum-viable constellation = nodes + click navigation, no animated forces).

---

## Cross-references

- **PM_CONTEXT §14 Frozen Scope List:** every scope line maps to one or more specs above.
- **§13 EDGE Coverage Map:** every row maps to a spec; final verification in this plan's appendix and in `01_design/00_coverage_walk.md`.
- **Open questions:** all open-but-pending Phase 3 dispositions surfaced as Q126-Q150 in `99_open_questions.md`.

---

## What this build plan is NOT

- **Not a re-design.** Per §6 rule 31, no design changes during Phase 4 without an explicit cut/scope-adjustment decision.
- **Not a contract that the user signs.** It's a working plan; PM and user re-evaluate at every Friday gate.
- **Not where the front-end Phase-4 code goes.** That's `03_build/front/` (Phase 4 commit target).
- **Not where the back-end Phase-4 code goes.** That's `03_build/api/` and `03_build/core/`.

---

*End of build plan. Phase 4 begins 2026-05-22.*

# EDGE Pulse — Research Synthesis (Phase 1)

**Phase:** Research (Phase 1)
**Scope:** 7 external reference repos + 4 prior-work folders in `ai-rm/`. See `findings/` for per-repo detail.
**Output gate:** This synthesis is the input to Phase 2 Design. No design lock is proposed here — this is a coherent *shape* for Phase 2 to start from.

---

## Top architectural inspirations

Ranked by impact on Pulse's actual build.

### 1. graphiti — the memory layer, already locked
Graphiti is the load-bearing element of Pulse's Temporal Context Graph and the single highest-impact reference in this audit. Apache 2.0, actively shipped, paper-credible (arXiv 2501.13956), multi-backend (Neo4j / FalkorDB / **Kuzu** / Neptune), with a bi-temporal edge model that gives Pulse first-class answers to "what was true about this customer last quarter?" — exactly the question the Senior Developer will ask. PM_CONTEXT §3 already locks Graphiti pending a quickstart spike; this audit confirms the choice. The custom-types facility means EDGE-specific entities (Customer, Talent, RM, Case, Placement) and edges (`placed_at`, `manages`, `raised_concern_about`, `replaced`) layer in cleanly without forking. Episodes give us per-fact provenance — the audit trail standing-rule (PM_CONTEXT §6 rule 10) is satisfied by the model, not by extra plumbing.

### 2. rm-intelligence-agent — Pulse v0
EDGE's own prior-work prototype is the most directly relevant reference of all. It already encodes EDGE's SFDC schema (`RM_Outreach__c`, `Associates__c` with placement statuses, risk-tagged `Case`), the Chorus v3 integration, the four-layer signal triangulation order (Chorus → RM_Outreach → Associates → Cases), the AI-RM first-person voice with inline `<num>/<bad>/<good>/<quote>/<em>` tags, and a working CEO-overview generator that produces a single self-contained `data/demo.html`. Phase 1 of Pulse is largely *re-architecture* of this codebase: same data flow, same outputs, but routed through Graphiti, surfaced via React + an action queue, and hardened with tests, reasoning capture, and Claude (not GPT) as the LLM.

### 3. Multi-Agent-Enterprise-CRM — the governance + action-queue blueprint
The repo's most important contribution is *vocabulary*: the **`productivity.action-suggested` / `action-approved` / `action-rejected` event triplet** is precisely the action-queue contract Pulse needs. Its **OPA-based approval policies** (`policies/agents/approval.rego`) are the cleanest answer to PM_CONTEXT §6 product rule 4 (tier-aware behavior). Its **kill switch and explainability engine** map onto the "no silent failure" rule. The implementation is too heavy to copy wholesale (Kafka + Weaviate + LangGraph + Ollama + multi-tenant Postgres RLS), but the *shapes* should anchor Phase 2 architecture. MIT-licensed, so adoption is unblocked at the legal layer.

### 4. b2b-sdr-agent-template-main — per-profile Markdown context layers
PM_CONTEXT memory `feedback_only_adopt_context_split` already locked this lift target. This audit confirms it. The 7-layer Markdown context system (IDENTITY/SOUL/AGENTS/USER/HEARTBEAT/MEMORY/TOOLS) is more than Pulse needs, but the *per-entity Markdown profile* idea — one editable file per Account, per Associate, per RM, read into the agent's context when reasoning about that entity — is exactly the "context priming layer" PM_CONTEXT names in its `project_context_priming` memory. MIT-licensed; portable.

### 5. SDRbot-main — Schema Sync + HITL discipline
The Schema Sync pattern — introspect the live CRM, codegen typed tool definitions for the agent — is the cleanest answer to "how does Pulse's agent reliably operate against EDGE's specific custom Salesforce objects?" without prompt-engineered guessing. The Safe Mode + Plan Review + Shell Allow-List triad is a clean encoding of HITL discipline. Session persistence, headless mode, and observability wiring are all directly applicable. MIT-licensed. Lift patterns rather than the LangChain dependency tree.

---

## Must-borrow components

Default to borrow when the component is commodity infrastructure or pre-validated EDGE IP. Each line below is *what* + *from where* + *license posture* + *integration shape*.

| Component | Source | License | Integration shape |
|---|---|---|---|
| **Bi-temporal context graph engine** | graphiti (`graphiti_core/`) | Apache 2.0 | Embed as a Python library; back with Kuzu in Phase 1, migrate to Neo4j or Neptune later via the existing `Driver` abstraction. Each Pulse signal becomes a Graphiti `Episode`; EDGE entities/edges defined via Pydantic custom types. |
| **`sf` CLI subprocess wrapper for SOQL** | rm-intelligence-agent (`src/sfdc_pull.py`) | EDGE-internal | Lift the function verbatim; refactor into a `salesforce_client.py` module. Keep `--target-org production`. |
| **Chorus v3 API integration** | rm-intelligence-agent (`src/chorus_pull.py`) | EDGE-internal | Lift verbatim; wrap in a small client class. Auth header shape and pagination already validated. |
| **Fuzzy account-name join (Chorus ↔ SFDC)** | rm-intelligence-agent (`src/rank_accounts.py`) | EDGE-internal | Lift the `fuzz_score` function verbatim. Reuse for any "two systems, same entity, no shared ID" join in Pulse. |
| **Hybrid deterministic + LLM matcher pattern** | opportunity-tracker (`src/matcher.py` + `src/ai_matcher.py`) | EDGE-internal | Reuse the *pattern* for tier-classifying signals: cheap rules first, LLM only for ambiguous cases. |
| **SQLite new-vs-seen state for idempotency** | opportunity-tracker (`src/state.py`) | EDGE-internal | Reuse the pattern (likely upgraded to Postgres in Pulse) to prevent duplicate action proposals within a window. |
| **Inline-tag voice rendering** (`<num>/<bad>/<good>/<quote>/<em>` → CSS) | rm-intelligence-agent (`src/render_demo.py`) | EDGE-internal | Lift the renderer; reuse in the React UI. Already calibrated to the Edge purple + Instrument Serif + JetBrains Mono aesthetic. |
| **EDGE 53-role catalog** | opportunity-tracker (`config/role-catalog.json`) | EDGE-internal | One canonical owner (likely opportunity-tracker remains the owner). Pulse reads it as a shared config artifact. |
| **Two-tier model strategy** (cheap-bulk + premium-synthesis) | rm-intelligence-agent (both extract + narrative scripts) | EDGE-internal | Reuse the *pattern*: route bulk extraction through Claude Haiku (cheap), route narrative synthesis through Claude Sonnet/Opus (quality). Aligns with $75–150/RM TCO budget. |
| **Per-profile Markdown context layers** | b2b-sdr-agent-template-main (`workspace/*.md`) | MIT | Replicate the pattern with EDGE-specific files: per-Account / per-Associate / per-RM profile Markdown. PM_CONTEXT already endorses. |
| **Action-event triplet vocabulary** (`action-suggested` / `-approved` / `-rejected`) | Multi-Agent-Enterprise-CRM (`schemas/events/productivity.action-*/`) | MIT | Adopt as the event-shape for Pulse's action queue. Payloads to be designed in Phase 2. |
| **OPA-or-equivalent policy externalization** | Multi-Agent-Enterprise-CRM (`policies/agents/`) | MIT | Phase 1 may use a thin Python/TS policy module with OPA-shape inputs/outputs; migrate to real OPA in Phase 2+. |
| **Schema Sync pattern** (CRM-introspect → typed-tool codegen) | SDRbot-main (likely `setup/` or `services/`) | MIT | Lift the pattern: deploy-time SOQL describe → generated typed tools per SFDC object Pulse touches. Avoids prompt-engineered field-name guesses. |
| **Safe Mode / Plan Review / Allow-List triad** | SDRbot-main (`tools.py`, `execution.py`) | MIT | Adopt as the implementation shape of HITL. The action queue *is* Plan Review made permanent. |
| **Skills as Markdown files in a numbered, lifecycle-staged library** | customer-success-skills (`skills-library/NN-stage/NNN-name.md`) | Inspiration only (license blocks direct embedding into a competing product) | Mimic the *structure*. Write Pulse's own skills under EDGE attribution: detect-quiet-customer, propose-EBR-prep, draft-expansion-ask, crisis-de-escalation-on-replacement, etc. |
| **Typed bidirectional relationships** | monica (validation of the pattern), Graphiti (the implementation) | Pattern; Graphiti is Apache 2.0 | Already supported by Graphiti edges. Decision: rely on Graphiti's edge model; do not maintain explicit inverse edges. Adopt monica's "how we met" provenance as a per-relationship field. |

**Default-to-borrow boundary:** anything in this list is commodity or pre-validated. Pulse-original work belongs in the next section.

---

## Must-build components

Things unique to EDGE Pulse that nothing in the reference set covers. This section scopes Phase 1's real work.

### 1. The Action Queue — UI surface and approval lifecycle
Multi-Agent-Enterprise-CRM gives us the event vocabulary; nothing in the audit gives us the *user surface*. The action queue is Pulse's hero (PM_CONTEXT §6 design rule 15) and must be designed against the Linear + Granola aesthetic. Includes: queue ranking logic, per-item explainability ("why is this here?"), approve/reject/modify flow, one-tap dispatch, post-action follow-up loop, tier-aware default approval thresholds, after-action outcome capture ("value receipt" pattern from customer-success-skills).

### 2. The Three-Graph Composition
PM_CONTEXT §11 glossary names three graphs:
- **Temporal Context Graph** — Graphiti, borrowed.
- **Skills Layer** — internal; ESCO-backed lite version in Phase 1, full drift detection in Phase 2 (Option C).
- **Account/Talent Relationship Graph** — custom relationship layer connecting Customers, Talent, and RMs.

How the three relate, how they share IDs, how queries fan out across them, where each lives physically (one Kuzu? three?) — *no reference covers this*. This is Pulse-original architecture work owed in Phase 2. The Three-Graph composition is one of the two or three things the Senior Developer will spend the most time on.

### 3. Pulse-Specific Skill Library (EDGE-authored, white-labeled)
The customer-success-skills repo validates the format but its content is SaaS-CS, not staffing. Pulse needs an EDGE-attributed library covering at minimum:
- *detect-quiet-customer* (silent churn signal)
- *propose-EBR-prep* (Executive Business Review preparation)
- *draft-expansion-ask* (placement upsell)
- *crisis-de-escalation-on-replacement* (Associate `Replaced/Terminated` status triggers)
- *referral-readiness* (when an RM should ask for a referral)
- *talent-check-in* (proactive Associate well-being)
- *placement-anniversary* (recognition)
- ~3–6 more, scoped in Phase 2.

These are EDGE IP and the differentiator. License-clean (own authorship), HIPAA-aware (no PHI in skill prose), white-label-aligned (no underlying tech named).

### 4. The Three-Tier Role Model + Overall View
PM_CONTEXT memory `project_role_model` names Admin / Manager / RM tiers plus a shared Overall view. Twenty's metadata-driven RBAC and Relaticle's tenant-context middleware are relevant patterns, but Pulse's specific shape — Admin sees everything, Manager sees their direct reports' books, RM sees their own book, Overall view is a deliberately collaborative cross-tier surface — is original. Needs explicit design.

### 5. CEO View (AI-as-CEO's-RM)
PM_CONTEXT memory `project_pizzazz_feature` is unambiguous: this is **not** a dashboard of RM activity but an AI-RM speaking to the CEO in first person, weekly cadence. rm-intelligence-agent already produced a v0 of this. The Phase 1 CEO View is a *narrative product surface*, not a chart. Visual-first per PM_CONTEXT §6 design rule 14. No reference repo guides the design — this is Pulse-original.

### 6. HIPAA-Aware Ingestion Pipeline
Healthcare Zoom transcripts may contain PHI. PM_CONTEXT §6 product rule 2 forbids deferring HIPAA. Pulse needs a redact-or-encrypt-or-segregate strategy for Chorus/Zoom transcripts *before* episodes are written into Graphiti. No reference repo addresses HIPAA. Pulse-original.

### 7. Signal Triangulation Logic
The order is locked (Chorus → RM_Outreach → Associates → Cases). The *fusion logic* — how a Chorus quote, an RM_Outreach Customer_Health rating, an Associate `Replaced` event, and a Risk-tagged Case combine into a single per-account health tier — is partially encoded in rm-intelligence-agent's `extract_signals` + `generate_narratives` pipeline but needs to be promoted to a first-class, testable component in Pulse. Pulse-original.

### 8. The Dual-Sided RM Model
PM_CONTEXT memory `project_rm_dual_sided` notes that RMs manage both Customer AND placed Associates; account health rolls up both sides. No reference repo's data model encodes this dual-sided rollup. Pulse-original. The Three-Graph composition needs to support it natively.

### 9. CEO Demo Deliverable Mode
PM_CONTEXT memory `project_ceo_demo` commits to a local Streamlit-style demo on 50 SFDC accounts qualified by Chorus call depth, focused on 3–5 narrative-strong standouts. rm-intelligence-agent's static-HTML output is the v0; Pulse needs a polished demo mode that combines the live action queue with the CEO narrative surface. The "ship a single self-contained HTML file" capability from rm-intelligence-agent should be preserved as a fallback demo mode for high-stakes presentations where infrastructure is unreliable.

### 10. Event Log + Reasoning Capture Schema
Multi-Agent-Enterprise-CRM gives us the event triplet shape but not a concrete payload schema for Pulse's domain. Every agent action must log: input signals consulted, skill triggered, model used, reasoning text, proposed action, approval state, executed-side-effects, and outcome. Pulse-original schema design in Phase 2.

---

## Conflicts and gaps

### Conflicts

- **n8n vs. real agent framework (LangGraph / Claude Agent SDK).** PM_CONTEXT §3 locks n8n for Phase 1; SDRbot and Multi-Agent-Enterprise-CRM both prefer LangGraph. n8n is right for Phase 1 (iterate fast, non-engineers can edit flows, no infra to operate) but n8n is a *workflow engine*, not an *agent runtime*. As the agent's reasoning becomes more multi-step, n8n will strain. PM_CONTEXT §12 candidate 4 already books the migration. **No conflict to resolve now; flag for Phase 2 to verify n8n carries Phase 1.**
- **Embedded Kuzu vs. server Neo4j for Graphiti backend.** PM_CONTEXT favors Kuzu (embedded, zero-ops, Apache 2.0); Graphiti's most-battle-tested driver is Neo4j. **Resolution path:** quickstart spike in Phase 2 with realistic volumes (≈ 530 customers × 12 months × multiple signals/customer/week). If Kuzu carries the load, stay; if it strains, switch to Neo4j Community.
- **Internal MCP exposure vs. direct tool calls.** Relaticle and SDRbot both lean on MCP as a CRM-tool surface; PM_CONTEXT's white-label rule forbids exposing MCP *to end users*. **Resolution:** MCP is fair game *internally* (between Pulse's services and the agent runtime) — it's an architecture choice, not a user-facing tech mention. Decide in Phase 2.
- **OPA now vs. inline-policy now-OPA-later.** Multi-Agent-Enterprise-CRM uses OPA from day one; Phase 1 ruthless-scope discipline argues against operating an OPA service. **Resolution:** Phase 1 ships a Python/TS policy module with OPA-shape inputs/outputs (action proposal + context → allow / deny / require-approval); upgrade to real OPA in Phase 2 only if scope and complexity demand it.
- **Single agent vs. supervisor + subagents.** SDRbot has a subagent loader; Multi-Agent-Enterprise-CRM has four named agents. PM_CONTEXT does not commit. **Resolution:** Phase 1 should default to a single agent with named skills; promote to subagents in Phase 2 only when concrete sub-tasks justify it.

### Gaps — places no reference covers

- **HIPAA-compliant Chorus / Zoom ingestion path.** None of the references address PHI. This is a hard original-design item.
- **The Action Queue UI as a hero surface.** Multi-Agent-Enterprise-CRM has a generic governance dashboard; nothing has a polished Linear/Granola-aesthetic action queue. We design from a blank page.
- **The dual-sided account-health rollup.** No CRM in the audit treats a single account as having both customer-side health AND placed-talent-side health. EDGE-original.
- **The CEO View as a narrative AI-RM voice.** rm-intelligence-agent has v0; nothing else comes close. Pulse-original.
- **The Three-Graph composition.** Graphiti gives us one graph. Pulse needs three integrated graphs (Temporal + Skills + Account-Talent). Original architecture work.
- **EDGE-specific skill library content.** Customer-success-skills validates the format; the content is wrong for staffing.
- **Cost model for episode-ingestion at scale.** Every signal triggers LLM extraction. Need a per-RM monthly TCO model before Build phase.

---

## Recommended starting architecture (high-level only)

This is a coherent shape for Phase 2 to start from — not a design lock.

```
                       ┌─────────────────────────────────────────┐
                       │   Signal Sources (per signal_triangulation)  │
                       │                                         │
                       │  Chorus v3  •  Zoom (TBD/Q4)  •  SFDC   │
                       │  Slack (out for v1)  •  Google News RSS │
                       │  Opportunity Tracker (job postings)     │
                       └────────────────┬────────────────────────┘
                                        │
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │   Ingestion Pipeline (n8n in Phase 1)   │
                       │   • Per-source connector                │
                       │   • PHI redaction step (HIPAA gate)     │
                       │   • Normalize → Episode envelope        │
                       └────────────────┬────────────────────────┘
                                        │
                                        ▼
       ┌────────────────────────────────────────────────────────────────────┐
       │                       Pulse Memory & Knowledge Layer                │
       │   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
       │   │ Temporal Context │  │  Skills Layer    │  │ Account/Talent    │ │
       │   │ Graph (Graphiti, │  │ (ESCO data; lite │  │ Relationship      │ │
       │   │ Kuzu backend)    │  │  in Phase 1)     │  │ Graph (Pulse-     │ │
       │   │ — Episodes,      │  │ — Talent skills, │  │ original)         │ │
       │   │   Entities,      │  │   role taxonomy  │  │ — Placements,     │ │
       │   │   bi-temporal    │  │                  │  │   ownership,      │ │
       │   │   Edges          │  │                  │  │   genesis         │ │
       │   └──────────────────┘  └──────────────────┘  └──────────────────┘ │
       │       Shared entity IDs (Customer/Talent/RM) across all three      │
       └────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
       ┌────────────────────────────────────────────────────────────────────┐
       │           Agent Layer (single supervisor agent, Phase 1)            │
       │   • Claude API (primary)                                            │
       │   • Schema-Synced typed Salesforce tools (lift SDRbot pattern)      │
       │   • EDGE-authored skill library (Markdown, lifecycle-staged)        │
       │   • Per-profile Markdown context layers (Account/Associate/RM)      │
       │   • Reasoning capture (every step logged with provenance)           │
       └────────────────┬────────────────────────────────────────────────────┘
                        │  proposes
                        ▼
       ┌────────────────────────────────────────────────────────────────────┐
       │          Policy / Governance Layer  (inline Python in Phase 1)      │
       │   • Tier-aware approval thresholds (SMB / Mid-Market / Enterprise)  │
       │   • Kill switch                                                     │
       │   • Audit log (every proposal + outcome)                            │
       │   • OPA-shape contracts; migrate to OPA in Phase 2 if warranted     │
       └────────────────┬────────────────────────────────────────────────────┘
                        │  emits  action-suggested events
                        ▼
       ┌────────────────────────────────────────────────────────────────────┐
       │                   Action Queue  (hero UI surface)                   │
       │   • React/TS, Linear + Granola design language, dark by default     │
       │   • One-tap approve / reject / modify                               │
       │   • Per-item explainability (inline-tag voice from rm-intel-agent)  │
       │   • CEO View as a narrative sibling surface                         │
       │   • Three-tier RBAC (Admin / Manager / RM) + Overall view           │
       └────────────────┬────────────────────────────────────────────────────┘
                        │  on approve
                        ▼
       ┌────────────────────────────────────────────────────────────────────┐
       │                       Action Dispatch                               │
       │   • Email (Gmail/Outlook), Salesforce task creation, Jira tickets,  │
       │     calendar holds, recognition notes                               │
       │   • Each handler emits action-executed event + outcome event        │
       │   • Outcome events feed back into the memory layer ("value receipts")│
       └────────────────────────────────────────────────────────────────────┘
```

**Where each agent runs:** single supervisor agent in Phase 1, hosted as part of the n8n pipeline + a small FastAPI service for the interactive API surface. Heartbeat runs on a schedule; interactive reasoning runs on demand.

**How signals enter:** through ingestion pipeline; PHI redaction is the HIPAA gate.

**How actions exit:** the action queue is the only path; nothing dispatches without an approval (auto- or human-).

**Where it physically runs in Phase 1:** PM_CONTEXT-locked fast-stack (Vercel front, Supabase/Neon DB, Claude API direct, n8n cloud). AWS migration after product shape locks.

---

## Risks surfaced during research

### License risks
- **AGPL infection: Twenty, Relaticle, Monica.** None of these can be lifted into Pulse without forcing Pulse itself to be AGPL. Risk is real if a future contributor unknowingly copies code from one of these into the repo. **Mitigation:** add a code-provenance check to PR review; explicitly enumerate "do not copy from" repos in `CONTRIBUTING.md` when it exists.
- **skills-ml non-commercial license.** Cannot embed code; must re-implement. **Mitigation:** treat as research-only; consume ESCO data directly via its CC BY 4.0 license.
- **REPlexus Community License on customer-success-skills.** "Internal business operations" permitted but "competing software product" prohibited. **Mitigation:** write our own EDGE-attributed skills; do not commit REPlexus files into Pulse's repo.

### HIPAA risks (the standing rule, made concrete by research)
- **Chorus / Zoom transcripts may contain PHI.** Graphiti stores episode text raw. **Mitigation:** PHI redaction step before episodes enter the graph; in-scope BAA with vendors; encryption at rest. Filed Q6 in `99_open_questions.md`.
- **Anthropic BAA status.** Pulse routes call content to Claude for extraction. Need a confirmed BAA. Filed Q6.
- **OpenAI in rm-intelligence-agent.** Current prototype uses GPT for extraction. Migrate to Claude before any production data flows. Filed Phase 2.

### Vendor / dependency risks
- **Graphiti as a single point of dependency.** Apache 2.0 is permissive but a bus-factor concern remains. **Mitigation:** Graphiti's `Driver` abstraction means we are not tied to a specific backend; Pulse's domain entities are defined via Pydantic and could be ported to a different temporal-graph engine if needed. Acceptable risk.
- **Kuzu's relative immaturity** vs. Neo4j. Embedded and OSS but smaller community. **Mitigation:** quickstart spike with realistic volumes in Phase 2 before locking.
- **n8n cloud as the orchestration backbone.** Acceptable for Phase 1; PM_CONTEXT §12 already books the migration.
- **Multi-Agent-Enterprise-CRM as a "reference" with unclear maturity.** Don't depend; reference only.

### Scaling risks
- **Cost of LLM-driven entity extraction at scale.** Every episode → at least one extraction LLM call + a dedup LLM call. Volume estimate: ~530 customers × hundreds of signals/yr each = tens of thousands of episodes/yr. At Claude Sonnet pricing this is non-trivial; the two-tier model strategy (Haiku for extraction, Sonnet for synthesis) mitigates but doesn't eliminate. **Mitigation:** budget model exercise in Phase 2; pre-commit to two-tier routing.

### Operational risks
- **n8n is not a real audit log.** "No silent failure" rule (PM_CONTEXT §6 rule 10) requires every agent action to log reasoning. n8n's run logs are not durable enough. **Mitigation:** Pulse must own its event log in Postgres regardless of where the agent runs.
- **"Demo HTML" vs. "live UI" parity drift.** rm-intelligence-agent's demo.html and the future live action queue could drift in voice and visual. **Mitigation:** the live UI's rendering pipeline should consume the same per-account narrative JSON the static HTML consumes.

### Adds to PM_CONTEXT §3 / §6 risk register
- **License-infection vector via copy-paste from AGPL references** (Twenty/Relaticle/Monica) — add to standing rules.
- **PHI-in-episode** as a HIPAA-rule corollary worth making explicit.
- **License-discipline check in PR review** — small process risk.

---

## Recommendations for the Design Phase

Order matters. What's earlier blocks what's later.

### Lock-first (cannot be deferred)
1. **HIPAA posture and PHI redaction strategy.** Without this, no Chorus/Zoom data can flow. Resolves Q4, Q5, Q6 in `99_open_questions.md`. Blocking everything downstream.
2. **Salesforce schema context.** Resolves Q3. Without it, Schema Sync codegen has nothing to bind to. Blocking the agent's tool surface.
3. **Real vs. synthetic data for the demo.** Resolves Q2. Drives ingestion-pipeline design (does it need to be production-grade in Phase 1 or just demo-grade?).
4. **CEO demo deadline.** Resolves Q1. Drives ruthless scope.

### Design-lock items (the Phase 2 deliverable)
5. **The Three-Graph composition.** One Kuzu? Three Kuzus? Shared entity-ID scheme? Cross-graph query interface? The single most architecturally consequential design call.
6. **The Action Queue surface.** Linear + Granola wireframes, item ranking logic, explainability shape, tier-aware approval thresholds.
7. **The Event Log + Reasoning Capture schema.** Concrete payload for `action-suggested`, `action-approved`, `action-rejected`, `action-executed`, `outcome-recorded`.
8. **The Per-Profile Markdown Layer specification.** Per-Account / per-Associate / per-RM profile shape; storage location; update cadence; authoring tool.
9. **The EDGE Pulse Skill Library — first 8–10 skills.** Names, triggers, inputs, guardrails, expected outputs.
10. **The CEO View design.** Narrative shape, cadence (weekly per PM_CONTEXT), inputs, voice spec.
11. **The Three-Tier Role Model.** Admin / Manager / RM scopes; Overall view spec; RBAC enforcement layer.
12. **The Dual-Sided account-health rollup.** How customer-side and talent-side combine into one health tier.

### Plan-phase items (defer to Phase 3)
13. **Spec-by-spec build plan with DoD per spec.** Ordered against the design lock.
14. **Test discipline.** Unit + integration + golden-trace per spec.
15. **Observability backend pick.** Langfuse / LangSmith / Opik / Claude-native — choose one.
16. **The Kuzu vs. Neo4j call (post-spike).**

### Build-phase items (defer to Phase 4)
17. Schema Sync codegen pipeline against the locked SFDC schema.
18. Chorus / Zoom / Opportunity-Tracker ingestion connectors.
19. The Three-Graph implementation.
20. The Agent + Skill Library wiring.
21. The Policy module.
22. The Action Queue UI.
23. The CEO View.

---

*End of synthesis. Phase 2 (Design) starts when the user green-lights this output. Per Pre-flight rules: no design specs have been written; no application code has been authored; no user-facing artifact in this synthesis names underlying technology by name.*

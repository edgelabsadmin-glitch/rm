# EDGE Pulse — Open Questions

Append-only list of things needing human input. Each question stays here until resolved; resolved questions move to a "Resolved" section at the bottom with the resolution noted.

---

## Q1: CEO demo deadline
**Raised during:** PM scoping (carried into Phase 1)
**Question:** When does the CEO demo need to land — two weeks, four weeks, or other?
**Why it matters:** Drives ruthless scope. A two-week deadline forces a static-HTML-style demo extending the existing `rm-intelligence-agent` output; a four-week deadline allows a live action-queue surface with one or two real agent skills wired end-to-end; longer allows a full three-graph + governance-layer demo.
**Recommended path:** Confirm with the user before Phase 2 starts. Default working assumption: 4 weeks, with the rm-intelligence-agent static HTML as a Week-1 fallback if anything slips.
**Status:** Open

## Q2: Real Salesforce / Chorus / Zoom data vs. synthetic data for the first demo
**Raised during:** PM scoping (carried into Phase 1)
**Question:** Does the first CEO demo run against real production data, against a frozen snapshot of production data, or against synthetic data?
**Why it matters:** Real-data demo is the most compelling but requires HIPAA posture confirmed (Q6) and live integrations stable; synthetic-data demo is faster to build but the CEO has previously rejected demos that felt "linear and not exciting" (PM_CONTEXT §5).
**Recommended path:** Frozen production snapshot for the top 5 accounts, redacted of PHI, ingested once and replayed deterministically. Real enough to feel real; safe enough to demo without HIPAA holds.
**Status:** Open

## Q3: Salesforce schema context
**Raised during:** PM scoping (carried into Phase 1); reinforced by Phase 1 reading of `rm-intelligence-agent/src/sfdc_pull.py` and PM_CONTEXT `reference_sfdc_schema`
**Question:** What are the canonical Salesforce objects, key custom fields, and relationships in scope for Pulse, and specifically the shape of the Account ↔ Talent linkage? `rm-intelligence-agent` already uses `RM_Outreach__c`, `Associates__c`, `Account_Plan__c`, `Case` w/ `Associate__c` lookup, `affectlayer__Engagement__c` — is this the complete set or is more in scope?
**Why it matters:** The Schema Sync codegen pattern (lifted from `SDRbot-main`) binds Pulse's agent tools directly to these objects/fields. Missing or stale schema means the agent operates on a wrong mental model. Also drives the Account/Talent Relationship Graph design.
**Recommended path:** User to produce a Salesforce schema context doc (or point Pulse at a SOQL-describe snapshot) before Phase 2 design lock. PM_CONTEXT §3 already lists this as an Open-before-Phase-1-can-produce-useful-synthesis item.
**Status:** Open

## Q4: Zoom plan + transcription capability
**Raised during:** PM scoping (carried into Phase 1)
**Question:** Is Cloud Recording + Audio Transcript enabled on EDGE's Zoom plan? Is AI Companion turned on? Which Zoom webhook events are subscribed? Is Zoom in or out of scope for Phase 1?
**Why it matters:** PM_CONTEXT §1 lists Zoom calls among Pulse's signal sources, but `rm-intelligence-agent` only integrates with Chorus today. If Zoom is out of scope for Phase 1, scope simplifies materially. If Zoom is in scope, we need the plan-level capability check before designing the ingestion connector and a HIPAA path for any transcript content.
**Recommended path:** Confirm scope (in or out for Phase 1) before Phase 2. If in scope, run a Zoom capability check immediately.
**Status:** Open

## Q5: Chorus plan + coverage
**Raised during:** PM scoping; reinforced by PM_CONTEXT `project_chorus_coverage_gap` (only 4 of 18 RMs host meetings)
**Question:** Does the current Chorus plan capture RM check-in calls or only sales/AE calls? Is API access (v3 engagements + v1 conversations) on the current plan, and what are the rate limits? Does account-centric ranking (already used by `rm-intelligence-agent`) cover enough of the book to be useful?
**Why it matters:** Chorus is the deepest signal source committed for Phase 1. The known coverage gap (4 of 18 RMs as hosts) is partially mitigated by ranking accounts rather than RMs, but it caps the signal density. Pulse may need to back off from Chorus-as-primary if coverage is too thin.
**Recommended path:** Confirm plan + API access in Phase 2 capability-check.
**Status:** Open

## Q6: HIPAA posture
**Raised during:** PM scoping (carried into Phase 1); reinforced by Phase 1 reading of Chorus/Zoom ingestion paths and Graphiti's raw-episode storage
**Question:** Does EDGE have a Business Associate Agreement (BAA) with Anthropic? With OpenAI (currently used by `rm-intelligence-agent`)? With Chorus, Zoom, the future hosting vendor? What is the data-residency requirement? What is the redaction posture for PHI in call transcripts?
**Why it matters:** PM_CONTEXT §6 product rule 2 forbids deferring HIPAA. Healthcare/insurance customers mean PHI is a real risk in call transcripts and case descriptions. Graphiti stores episodes raw; any PHI in an episode becomes a HIPAA exposure unless redacted before ingest.
**Recommended path:** User to confirm BAA status with each vendor. Phase 2 designs a PHI-redaction step (pattern-based + LLM-based) in the ingestion pipeline that runs *before* episodes enter the memory layer. This is **blocking** for any production data flow.
**Status:** Open

## Q7: EDGE doc delivery contract — scope expansion
**Raised during:** PM scoping (carried into Phase 1)
**Question:** Does the EDGE doc owner expect only the originally-scoped workflows, or is there license to deliver the expanded agentic scope that Pulse contemplates? PM_CONTEXT §5 records that the EDGE doc's cost estimate ($2-4k) was pushed back as optimistic for the true agentic scope ($15-25k).
**Why it matters:** Scope ambiguity downstream causes "we built more than was paid for" or "we built less than was needed." Affects how aggressively Phase 2 design pushes into agentic territory vs. workflow territory.
**Recommended path:** User to clarify with EDGE doc owner before Phase 4 (Build). Phase 2 design can proceed assuming the expanded scope but must produce a clear scope-boundary artifact the EDGE doc owner can sign off on.
**Status:** Open

---

## Questions surfaced during Phase 1 research

## Q8: Backend choice for Graphiti — Kuzu vs. Neo4j Community
**Raised during:** Phase 1 — `findings/graphiti.md`
**Question:** PM_CONTEXT §3 favors Kuzu (embedded, zero-ops, Apache 2.0). Is the load profile of EDGE Pulse (≈ 530 customers × dozens of signals/customer/year, growing) within Kuzu's comfortable operating envelope, or do we hit limits that force Neo4j?
**Why it matters:** Kuzu keeps Phase 1 fast and zero-ops. Neo4j is more battle-tested but adds infra. Wrong choice early means a migration mid-Build.
**Recommended path:** Phase 2 quickstart spike with realistic episode volumes (1 month of all signals across 10 representative accounts) against both backends. Decision after spike.
**Status:** Open

## Q9: ESCO data licensing surface for production
**Raised during:** Phase 1 — `findings/skills-ml.md`
**Question:** ESCO is CC BY 4.0 (clean for commercial use with attribution). What's the attribution surface — internal docs only, or does the white-label rule require us to hide the attribution even from RMs?
**Why it matters:** If user-facing attribution is required (CC BY), there's a tension with PM_CONTEXT §6 product rule 1 (white-label, no user-facing mention of underlying tech). Internal-only attribution is fine; user-facing attribution conflicts.
**Recommended path:** Confirm with user that CC BY attribution can live in internal docs / admin pages only, not in the RM-facing UI. If user-facing attribution is required by the license, consider O*NET (US Government public domain) as a substitute.
**Status:** Open

## Q10: Agent runtime — n8n carries Phase 1, or do we need LangGraph / Claude Agent SDK earlier than planned?
**Raised during:** Phase 1 — `findings/Multi-Agent-Enterprise-CRM.md`, `findings/SDRbot-main.md`
**Question:** PM_CONTEXT §3 locks n8n for Phase 1 orchestration. SDRbot and Multi-Agent-Enterprise-CRM both run on LangGraph. As Pulse's reasoning chains grow, will n8n strain? Should we plan the LangGraph migration earlier than the §12 v1.5+ candidate suggests?
**Why it matters:** Mid-Phase-1 migration is expensive. Knowing the strain point before we hit it lets us pre-architect for it.
**Recommended path:** Stay with n8n for Phase 1. In Phase 2 design, define a clean agent-interface abstraction so the runtime can be swapped without touching the agent's skill library, prompts, or tool surface.
**Status:** Open

## Q11: Internal MCP exposure within Pulse
**Raised during:** Phase 1 — `findings/relaticle.md`, `findings/SDRbot-main.md`
**Question:** Should Pulse's agent call Salesforce-operation tools via an internal MCP server (decouples agent framework from data layer), or via direct typed Python/TS function calls?
**Why it matters:** MCP gives clean swap-ability (any MCP-capable agent runtime can talk to Pulse's tools) but adds operational complexity. Direct calls are simpler in Phase 1 but tighter coupling.
**Recommended path:** Direct typed calls in Phase 1 (lift SDRbot's Schema Sync codegen pattern). Revisit MCP exposure in Phase 2 if/when we have multiple agent runtimes or external agents that need access.
**Status:** Open

## Q12: PHI redaction strategy — pattern-based, LLM-based, or hybrid
**Raised during:** Phase 1 — `findings/graphiti.md` open-questions
**Question:** How does Pulse redact PHI from Chorus / Zoom transcripts before episodes enter the memory layer? Regex/pattern-based (cheap, deterministic, brittle) or LLM-based (expensive, more accurate, non-deterministic) or hybrid?
**Why it matters:** This is the HIPAA-gate technology. Choice affects cost, latency, recall, and audit defensibility.
**Recommended path:** Hybrid — pattern-based first pass (catches most named entities, IDs, dates) then LLM-based second pass on flagged segments. Concrete design in Phase 2 after Q6 resolves.
**Status:** Open

## Q13: Per-RM monthly TCO at LLM scale
**Raised during:** Phase 1 — `findings/graphiti.md`, `findings/rm-intelligence-agent.md`
**Question:** What is the projected per-RM monthly LLM cost at expected Phase 1 episode volumes, given the two-tier model strategy (Haiku for extraction + dedup, Sonnet/Opus for narrative synthesis)?
**Why it matters:** PM_CONTEXT §5 budget posture is $75–150 per RM per month TCO at steady state. We need a budget model before commit, or we hit a financial wall at Build.
**Recommended path:** Phase 2 budget exercise using rm-intelligence-agent's actual token consumption as a baseline, scaled to expected Phase 1 episode volumes.
**Status:** Open

## Q14: Observability backend choice
**Raised during:** Phase 1 — `findings/SDRbot-main.md`
**Question:** LangSmith, Langfuse, Opik, or Claude-native tracing for Pulse's agent telemetry?
**Why it matters:** The "no silent failure" rule (PM_CONTEXT §6 rule 10) requires every agent action to log reasoning. Observability backend must be picked before Build because instrumentation hooks shape the agent's code structure.
**Recommended path:** Defer to Phase 2 with a strong default: Langfuse (OSS, self-hostable, clean Python SDK, no vendor lock). Revisit if Claude-native tracing matures.
**Status:** Open

## Q15: Where do the per-profile Markdown context layers live?
**Raised during:** Phase 1 — `findings/b2b-sdr-agent-template-main.md`
**Question:** Per-Account / per-Associate / per-RM Markdown profile files (lifted pattern from b2b-sdr template). Same git repo as the agent code (versioned)? Separate content repo? Backing a CMS surface for RM-facing edits? Generated on first ingestion, hand-authored, or hybrid?
**Why it matters:** Storage choice affects scaling, edit workflow, and how the agent reads them at runtime.
**Recommended path:** Phase 2 design lock. Default working assumption: stored in a Postgres table with a Markdown column, regenerated on signal-ingestion events with a hand-edit override layer.
**Status:** Open

## Q16: Integration contract between opportunity-tracker and Pulse
**Raised during:** Phase 1 — `findings/opportunity-tracker.md`
**Question:** How do Pulse and opportunity-tracker share data? Filesystem JSONL (current rm-intelligence-agent pattern)? Postgres table? HTTP webhook? n8n trigger?
**Why it matters:** opportunity-tracker is committed as Pulse's job-posting signal feeder. The contract shape affects deployment topology and signal-freshness latency.
**Recommended path:** Phase 2 design. Default working assumption: opportunity-tracker writes match records to a Postgres table; Pulse subscribes via n8n trigger.
**Status:** Open

## Q17: Role-catalog ownership between opportunity-tracker and Pulse
**Raised during:** Phase 1 — `findings/opportunity-tracker.md`
**Question:** Both opportunity-tracker and Pulse need EDGE's 53-role catalog. One canonical owner, or duplicated config?
**Why it matters:** Drift between two copies of the role catalog creates "Pulse thinks this is a Hottest match, opportunity-tracker doesn't" inconsistencies.
**Recommended path:** opportunity-tracker remains the canonical owner of `config/role-catalog.json`; Pulse reads it as a shared config artifact.
**Status:** Open

## Q18: Single agent vs. supervisor + subagents in Phase 1
**Raised during:** Phase 1 — `findings/SDRbot-main.md`, `findings/Multi-Agent-Enterprise-CRM.md`
**Question:** Phase 1 default: single supervisor agent with named skills, or supervisor + specialized subagents (draft-email, EBR-prep, etc.)?
**Why it matters:** Subagents add design surface and observability complexity. Worth it only if Phase 1 has concrete sub-tasks that benefit.
**Recommended path:** Default single agent + skills in Phase 1. Promote to subagents in Phase 2 if/when concrete sub-tasks justify the surface.
**Status:** Open

## Q19: License-discipline check in PR review
**Raised during:** Phase 1 — synthesis risk register
**Question:** How does Pulse prevent a contributor from copy-pasting AGPL code (from Twenty / Relaticle / Monica) into the repo by accident?
**Why it matters:** A single AGPL-tainted file makes the whole product AGPL-derivable. Hard to undo once committed.
**Recommended path:** A PR-review checklist line: "Did any code in this PR come from one of the known-AGPL reference repos? If yes, rewrite." Maybe a CI check that scans for distinctive comments from those repos.
**Status:** Open

## Q20: Demo HTML preservation as fallback mode
**Raised during:** Phase 1 — `findings/rm-intelligence-agent.md`
**Question:** After Pulse has a live React UI, should the "single self-contained HTML file" output of rm-intelligence-agent be preserved as a CEO-demo fallback for high-stakes presentations where infrastructure is unreliable?
**Why it matters:** A self-contained HTML demo is bulletproof — no network, no auth, no dependency on services being up. A great safety net for the CEO demo.
**Recommended path:** Yes. Phase 2 to define how the live UI's rendering pipeline and the static-HTML renderer share the same per-account narrative JSON, so the two outputs cannot drift.
**Status:** Open

---

## Phase 2 — Design (questions surfaced during design lock work)

The numbering convention continues from Q20. Q21–Q113 below correspond to items surfaced during the three capability spikes (Q21–Q26) and the twelve design artifacts (Q27–Q113). Most are tagged with the artifact that surfaced them.

## Q21: Salesforce sandbox auth token expired
**Raised during:** Spike 1 — `00_research/spikes/01_sfdc_schema.md`
**Question:** The `sandbox` alias in `sf` CLI returns "Unable to refresh session." Re-authentication needed via `sf org login web -a sandbox` (user interaction required). Spike 1 was bounded to known schema from `rm-intelligence-agent`; full describe pass for `Account_Plan__c`, `affectlayer__Engagement__c`, and complete picklist enumeration is blocked until refresh.
**Why it matters:** Blocks **Schema Sync codegen completeness** (Phase 4 task). Does NOT block Phase 2 design — known schema is sufficient to design against.
**Recommended path:** User runs `sf org login web -a sandbox` at convenience; Spike 1 reruns the describe pass and updates `01_sfdc_schema.md` §B.
**Status:** Open

## Q22: Account tier field name + values
**Raised during:** Spike 1
**Question:** Pulse's tier-aware behavior (§6 rule 4) reads tier from `Account.{Tier__c or Segment__c or similar}`. The exact field name and value set are not in `rm-intelligence-agent` code.
**Why it matters:** Drives policy routing in Design 04; drives Three-Tier Role Model variants in Design 09.
**Recommended path:** Spike 1 rerun after Q21 resolves.
**Status:** **RESOLVED 2026-05-20 via Spike 4** (`00_research/spikes/04_opportunity_tracker_review.md`). The field is **`Account.Segment__c`** — confirmed via `opportunity-tracker/src/salesforce_client.py:24`, which has been reading it in production. Sample values still need enumeration (Spike 1 rerun after Q21 sandbox refresh), but the field name is locked.

## Q23: Calendar source choice (Workflow 2 trigger)
**Raised during:** Spike 1 + Design 02
**Question:** Workflow 2's "24h-ahead meeting trigger" reads from SFDC `Event` records, Google Calendar API directly, or MS Graph?
**Why it matters:** Determines the Calendar Signal Source Adapter implementation.
**Recommended path:** Confirm EDGE's RM-calendar provider (Google vs. Outlook).
**Status:** Open

## Q24: Zoom feasibility questionnaire (8 sub-questions)
**Raised during:** Spike 2 — `00_research/spikes/02_zoom_feasibility.md`
**Question:** §A.1–A.8 of the Zoom spike memo: plan tier, Cloud Recording default, Audio Transcript toggle, AI Companion state, webhook subscriptions, retention policy, RM hosting coverage %, BAA/PII posture.
**Why it matters:** Not blocking Phase 1; defines Phase 2+ Zoom adapter effort and feasibility.
**Recommended path:** User checks Zoom Admin console (10-minute exercise).
**Status:** Open

## Q25: Embedder provider for Phase 1
**Raised during:** Spike 3 — `00_research/spikes/03_graphiti_verification.md` §C
**Question:** Graphiti separates LLM client (Claude) from embedder. Anthropic doesn't ship a public embedding model. PM recommendation: OpenAI `text-embedding-3-small`. User confirmation needed.
**Why it matters:** Adds a second LLM-vendor key (`OPENAI_API_KEY`) to `.env`.
**Recommended path:** Confirm OpenAI for Phase 1; self-hosted embedder at AWS migration.
**Status:** Open

## Q26: Anthropic API key provisioning for the live Graphiti spike
**Raised during:** Spike 3
**Question:** When does the user provide `ANTHROPIC_API_KEY` at the project root `.env` so Spike 3's harness can run live?
**Why it matters:** Phase 2 design lock proceeded on a *preliminary GO* verdict (Spike 3 §B). Full verdict closure requires the live run.
**Recommended path:** User drops the key in `.env`; run `python 00_research/spikes/03_graphiti/spike.py`; update the memo §F + §G.
**Status:** **RESOLVED 2026-05-20.** Keys provisioned; live spike ran; verdict converted to confirmed GO. See `00_research/spikes/03_graphiti_verification.md` §F + §G.

## Q27: `manages` edge — split or polymorphic
**Raised during:** Design 01
**Question:** `manages_customer` + `manages_talent` (two edges) vs. one polymorphic `manages` with a role property?
**Why it matters:** Affects query patterns and reassignment workflows.
**Recommended path:** PM recommends two edges in Phase 1; revisit if it bloats.
**Status:** Open

## Q28: Skill nodes — globally shared or per-Talent
**Raised during:** Design 01
**Question:** Globally shared (one node per skill code, all Talent with that skill link to it) vs. per-Talent skill nodes?
**Why it matters:** Globally shared enables "find all talent with skill X" cheaply.
**Recommended path:** PM recommends globally shared.
**Status:** Open

## Q29: Topic nodes — origin and dedup
**Raised during:** Design 01
**Question:** LLM-extracted Topics (e.g., "vendor consolidation", "AI displacement"). When does dedup run — first-extraction time, periodic pass, on-read?
**Why it matters:** Topic dedup quality determines cross-account pattern recall (Skill 10).
**Recommended path:** PM recommends LLM-extracted at first ingestion + Phase-2-end consolidation pass.
**Status:** Open

## Q30: Kuzu schema migration semantics
**Raised during:** Design 01
**Question:** When Phase 2 adds full skill drift detection, edge schemas change. How does Pulse handle schema migration on Kuzu?
**Why it matters:** Phase 3 planning concern.
**Recommended path:** Phase 3 planning.
**Status:** Open

## Q31: Workflow engine signature validation + idempotency forwarding
**Raised during:** Design 02 + Design 11
**Question:** Does the chosen workflow engine (n8n per ADR-001) support per-source signature validation + idempotency-key forwarding to adapter code paths?
**Why it matters:** Affects Design 02 ingestion-pipeline implementation.
**Recommended path:** Spike during Phase 3 / Phase 4 setup.
**Status:** Open

## Q32: SFDC CDC vs. polled SOQL for Phase 1
**Raised during:** Design 02
**Question:** Change Data Capture (Streaming API) vs. polled SOQL with `LastModifiedDate > X` for ingestion.
**Why it matters:** CDC = realtime but requires Streaming permission set; polled = simple and proven by `rm-intelligence-agent`.
**Recommended path:** PM recommends polled SOQL Phase 1, CDC Phase 2.
**Status:** Open

## Q33: Calendar provider — Google or Microsoft
**Raised during:** Design 02
**Question:** Same as Q23 (one consolidated question).
**Status:** Duplicate of Q23 — see there.

## Q34: Dead-letter review cadence
**Raised during:** Design 02
**Question:** How often does someone review `episodes_failed`?
**Recommended path:** PM proposes weekly.
**Status:** Open

## Q35: Backfill bounds per adapter
**Raised during:** Design 02
**Question:** How far back to ingest historical events when a new adapter ships?
**Recommended path:** PM proposes 30-day default, per-adapter configurable.
**Status:** Open

## Q36: Action Queue filter persistence
**Raised during:** Design 03
**Question:** Persist filter selections per-user across sessions?
**Recommended path:** PM proposes yes, browser localStorage.
**Status:** Open

## Q37: Bulk approve
**Raised during:** Design 03
**Question:** Should the Action Queue support multi-select + bulk approve in Phase 1?
**Recommended path:** PM proposes no in Phase 1; add in v1.5 if RMs ask.
**Status:** Open

## Q38: High-urgency notification escalation
**Raised during:** Design 03
**Question:** If a high-urgency item sits >1h undecided, ping the RM out-of-band?
**Recommended path:** PM proposes yes for `high` only.
**Status:** Open

## Q39: Action history UI depth
**Raised during:** Design 03
**Question:** How far back does the UI's Approved/Dispatched history go?
**Recommended path:** PM proposes 90 days in-UI; longer in audit log.
**Status:** Open

## Q40: Mobile / responsive scope
**Raised during:** Design 03
**Question:** Phase 1 mobile-responsive?
**Recommended path:** PM proposes no; v1.5+.
**Status:** Open

## Q41: Event log retention beyond 90 days
**Raised during:** Design 04
**Question:** Cold archive to S3 vs. full Postgres retention?
**Recommended path:** PM proposes full Postgres in Phase 1 (volume is low); cold archive at v1.5+.
**Status:** Open

## Q42: Reasoning text length cap
**Raised during:** Design 04
**Question:** 2KB inline cap; S3 link for longer?
**Recommended path:** PM proposes 2KB inline + S3 link-out.
**Status:** Open

## Q43: Multi-tenant analytics scope
**Raised during:** Design 04
**Question:** If Pulse ever multi-tenants, per-tenant schemas vs. shared table with tenant_id?
**Recommended path:** Phase 1 is single-tenant; revisit at multi-tenant time.
**Status:** Open

## Q44: Policy module rule format (Phase 1 vs. OPA)
**Raised during:** Design 04
**Question:** Phase 1 = Python code; v1.5+ OPA?
**Recommended path:** PM proposes Python pure functions with OPA-shape signatures for mechanical future migration.
**Status:** Open

## Q45: Outcome window per action type
**Raised during:** Design 04 + Design 03
**Question:** How long does Pulse wait before emitting `outcome-missing`?
**Recommended path:** PM proposes per-skill config: emails 7d, SFDC Tasks 14d, EBR briefs aligned with meeting date.
**Status:** Open

## Q46: Skill authoring tool
**Raised during:** Design 05
**Question:** Phase 1 = git PRs; v1.5+ admin UI for non-engineers?
**Recommended path:** PM proposes git PRs Phase 1; admin UI v1.5+.
**Status:** Open

## Q47: Skill versioning
**Raised during:** Design 05
**Question:** Keep older skill versions pinned for in-flight actions?
**Recommended path:** PM proposes yes; skills are versioned (`talent-care@v1`, `talent-care@v2`).
**Status:** Open

## Q48: Skill A/B testing
**Raised during:** Design 05
**Question:** v1.5+ desire to run two variants in parallel.
**Recommended path:** v1.5+.
**Status:** Open

## Q49: Skill scope field — per-customer / per-talent / global
**Raised during:** Design 05
**Question:** Formalize a `scope` field on the skill spec?
**Recommended path:** PM proposes yes.
**Status:** Open

## Q50: Signal taxonomy completeness
**Raised during:** Skill 01
**Question:** Are signal types complete?
**Recommended path:** PM proposes ship Phase 1 with current list; review against 100-episode sample after demo.
**Status:** Open

## Q51: Multi-axis sentiment vector dimensions
**Raised during:** Skill 01
**Question:** PM proposed warmth / frustration / urgency / momentum. User to confirm or revise.
**Status:** Open

## Q52: Topic node creation policy (same as Q29)
**Status:** Duplicate of Q29.

## Q53: RM-initiated query UX
**Raised during:** Skill 02
**Question:** Small dashboard query box, kept secondary per §6 rule 17?
**Recommended path:** PM proposes yes.
**Status:** Open

## Q54: Calendar attendee → Customer resolution failure
**Raised during:** Skill 02
**Question:** What if the calendar attendee doesn't resolve to a known Customer?
**Recommended path:** PM proposes low-urgency "unknown attendee" card.
**Status:** Open

## Q55: EBR detection without `EBR_Date__c` populated
**Raised during:** Skill 02
**Question:** Title-keyword fallback?
**Recommended path:** PM proposes yes ("EBR", "QBR", "quarterly review").
**Status:** Open

## Q56: Champion contact identification
**Raised during:** Skill 03 + Skill 06
**Question:** Who is the primary champion at a customer? Phase 1 fallback = most-recent Chorus-call customer-side participant. Phase 2 = explicit Champion field via Per-Profile Markdown.
**Status:** Open

## Q57: Renewal-watcher risk-weight tuning
**Raised during:** Skill 03
**Question:** Heuristic weights — tune via instrumentation post-demo.
**Recommended path:** Ship as-is, tune in v1.5.
**Status:** Open

## Q58: `Opportunity.Type` enumeration
**Raised during:** Skill 03
**Question:** Exact enum values for renewal type.
**Recommended path:** Spike 1 rerun (Q21).
**Status:** Open

## Q59: Talent-care cadence per role-type
**Raised during:** Skill 04
**Question:** 90-day blanket cadence vs. shorter for at-risk roles?
**Recommended path:** v1.5+.
**Status:** Open

## Q60: Email channel ownership (sender identity)
**Raised during:** Skill 04 + Skill 07
**Question:** Send from RM's mailbox (OAuth) vs. Pulse alias?
**Recommended path:** PM proposes RM mailbox via OAuth.
**Status:** Open

## Q61: Talent contact email source
**Raised during:** Skill 04
**Question:** Field name in `Associates__c` or linked `Contact`?
**Recommended path:** Spike 1 follow-up.
**Status:** Open

## Q62: Internal-team routing table source of truth
**Raised during:** Skill 05
**Question:** Hardcoded vs. configurable.
**Recommended path:** PM proposes hardcoded Phase 1, configurable v1.5.
**Status:** Open

## Q63: Team-lead User.Id mapping
**Raised during:** Skill 05
**Question:** Where does Pulse store the lead for each internal team?
**Recommended path:** PM proposes `pulse_team_leads.yaml` in Phase 1.
**Status:** Open

## Q64: Jira adapter timing
**Raised during:** Skill 05
**Question:** §13.2 mentions Jira; Phase 1 substitutes email+SFDC Task. Jira adapter is §12 #10.
**Recommended path:** Confirmed v1.5+.
**Status:** Open

## Q65: Champion identification heuristic (duplicate of Q56)
**Status:** Duplicate of Q56.

## Q66: Case-study artifact format
**Raised during:** Skill 06
**Question:** Out of Phase 1 scope.
**Recommended path:** v1.5+.
**Status:** Open

## Q67: Skill 06 / Skill 07 coordination
**Raised during:** Skill 06 + Skill 07
**Question:** Both can surface the same positive signal.
**Recommended path:** PM proposes shared rate-limit table keyed on (Customer, week).
**Status:** Open

## Q68: Recognition note sender identity (duplicate of Q60)
**Status:** Duplicate of Q60.

## Q69: VP-CS recognition surface
**Raised during:** Skill 07
**Question:** RM-facing recognition feels like it comes from VP-CS?
**Recommended path:** User to confirm VP-CS wants this surface.
**Status:** Open

## Q70: Positive-reply sentiment threshold
**Raised during:** Skill 07
**Question:** LLM-judged binary?
**Recommended path:** PM proposes binary with audit log.
**Status:** Open

## Q71: Account stage values for "new customer"
**Raised during:** Skill 08
**Question:** Exact enum for kickoff trigger.
**Recommended path:** Spike 1 rerun (Q21).
**Status:** Open

## Q72: Placement start date mapping
**Raised during:** Skill 08
**Question:** Does `Associates__c.Start_Date__c` map to actual placement start?
**Recommended path:** Spike 1 follow-up.
**Status:** Open

## Q73: Calendar hold mechanism
**Raised during:** Skill 08
**Question:** Manual suggestion vs. auto-booking.
**Recommended path:** PM proposes manual suggestion Phase 1; auto-booking v1.5+.
**Status:** Open

## Q74: Talent Dev team structure
**Raised during:** Skill 09
**Question:** Named coaches vs. generic queue.
**Recommended path:** User to clarify.
**Status:** Open

## Q75: Career-pathing data shape
**Raised during:** Skill 09
**Question:** Custom SFDC field vs. Per-Profile Markdown.
**Recommended path:** PM proposes Per-Profile Markdown.
**Status:** Open

## Q76: Skill 05 / Skill 09 deconfliction
**Raised during:** Skill 09
**Question:** Both can fire on the same Case.
**Recommended path:** PM proposes shared rate-limit table (parallels Q67).
**Status:** Open

## Q77: Cross-account retriever shape (Skill 10)
**Raised during:** Skill 10 + Design 01
**Question:** Exact-topic-match vs. embedding similarity?
**Recommended path:** PM proposes exact match Phase 1, similarity v1.5+.
**Status:** Open

## Q78: Pattern card pseudonymization mechanism
**Raised during:** Skill 10
**Question:** Phase 1 = simple replace; v1.5+ = sophisticated.
**Recommended path:** Filed.
**Status:** Open

## Q79: Pattern-surfacing cadence
**Raised during:** Skill 10
**Question:** Weekly default + intra-week trigger for severe themes.
**Recommended path:** PM proposes weekly default with severity-triggered intra-week.
**Status:** Open

## Q80: Profile content authority on conflict
**Raised during:** Design 06
**Question:** RM edits authoritative until re-merge?
**Recommended path:** PM proposes yes; v1.5+ may refine.
**Status:** Open

## Q81: Cross-profile coherence
**Raised during:** Design 06
**Question:** Same fact referenced in two profiles — consistency guarantee?
**Recommended path:** Phase 1 makes no guarantee; v1.5+ may.
**Status:** Open

## Q82: Profile export
**Raised during:** Design 06
**Question:** Export to PDF before sensitive meeting?
**Recommended path:** PM proposes yes; audit-log event when exported.
**Status:** Open

## Q83: Profile content sensitivity / scoping
**Raised during:** Design 06
**Question:** Per Design 09 role model.
**Recommended path:** PM proposes scope per Three-Tier Role Model.
**Status:** Open

## Q84: Profile staleness signal in UI
**Raised during:** Design 06
**Question:** "N days old" badge?
**Recommended path:** PM proposes subtle styling once >14 days unmodified.
**Status:** Open

## Q85: α/β weight tuning for dual-sided health
**Raised during:** Design 07
**Question:** Heuristic defaults; v1.5+ may fit to historical churn.
**Recommended path:** Filed.
**Status:** Open

## Q86: `Customer_Health__c` picklist enum
**Raised during:** Design 07
**Question:** Does it match Healthy/Stable/Watch/At-Risk/Escalated?
**Recommended path:** Spike 1 rerun (Q21).
**Status:** Open

## Q87: Per-industry-segment signal weighting
**Raised during:** Design 07
**Question:** Audit-failure heavier in Dental, etc.
**Recommended path:** v1.5+.
**Status:** Open

## Q88: Health-tier-change notification debouncing
**Raised during:** Design 07
**Question:** Avoid oscillation noise.
**Recommended path:** PM proposes ≥24h-hold rule before emitting `health-tier-changed`.
**Status:** Open

## Q89: Historical health-trajectory sparkline
**Raised during:** Design 07
**Question:** Phase 1 if cheap?
**Recommended path:** PM proposes yes.
**Status:** Open

## Q90: CEO View distribution list
**Raised during:** Design 08
**Question:** CEO + VP-CS; anyone else?
**Recommended path:** PM proposes default; configurable per Admin.
**Status:** Open

## Q91: Multi-recipient CEO View personalization
**Raised during:** Design 08
**Question:** Different sections per recipient?
**Recommended path:** v1.5+.
**Status:** Open

## Q92: Mobile email rendering for CEO View
**Raised during:** Design 08
**Question:** Single-column readability on phone.
**Recommended path:** PM proposes yes (demo.html-style inline CSS).
**Status:** Open

## Q93: CEO View voice consistency over time
**Raised during:** Design 08
**Question:** Pin model version + voice-spec file.
**Recommended path:** v1.5+ for voice-spec file; Phase 1 pins model version.
**Status:** Open

## Q94: "What I'd ask of you" inclusion threshold
**Raised during:** Design 08
**Question:** Composer-decided based on weekly signals.
**Recommended path:** Threshold tunable per Admin.
**Status:** Open

## Q95: `pulse_managers.yaml` source of truth
**Raised during:** Design 09
**Question:** YAML config Phase 1; SFDC user-hierarchy v1.5+.
**Recommended path:** Filed.
**Status:** Open

## Q96: VP of Client Success role mapping
**Raised during:** Design 09
**Question:** Admin vs. Manager tier.
**Recommended path:** PM proposes Admin.
**Status:** Open

## Q97: Cross-RM collaboration in Overall view
**Raised during:** Design 09
**Question:** "Ask a teammate" surface?
**Recommended path:** v1.5+.
**Status:** Open

## Q98: Audit-log access for Managers
**Raised during:** Design 09
**Question:** Manager sees their reports' event-log entries?
**Recommended path:** PM proposes yes, scoped.
**Status:** Open

## Q99: Departures handling — scope refresh cadence
**Raised during:** Design 09
**Question:** ~5-min lag from SFDC ownership change?
**Recommended path:** PM proposes that; on-demand admin re-derivation available.
**Status:** Open

## Q100: Single VPS vs. small Kubernetes
**Raised during:** Design 10
**Question:** Phase 1 deployment shape.
**Recommended path:** PM proposes single VPS.
**Status:** Open

## Q101: Container orchestration on the VPS
**Raised during:** Design 10
**Question:** docker-compose vs. nomad vs. bare Docker.
**Recommended path:** PM proposes docker-compose.
**Status:** Open

## Q102: Backup cadence for Kuzu DB
**Raised during:** Design 10
**Question:** Nightly + monthly retention.
**Recommended path:** PM proposes 30 daily + 12 monthly to S3-compatible store.
**Status:** Open

## Q103: AWS migration database path
**Raised during:** Design 10
**Question:** Kuzu → Neo4j, or stay on Kuzu.
**Recommended path:** Decision at AWS migration time.
**Status:** Open

## Q104: `simple-salesforce` vs. `sf` CLI in Pulse
**Raised during:** Design 10
**Question:** opportunity-tracker uses simple-salesforce; rm-intelligence-agent uses sf CLI. PM proposes standardize on sf CLI for Pulse.
**Recommended path:** sf CLI; opportunity-tracker stays as-is.
**Status:** Open

## Q105: n8n vs. Activepieces final call
**Raised during:** Design 11 ADR-001
**Question:** PM recommends self-hosted n8n.
**Recommended path:** User confirmation.
**Status:** Open

## Q106: Supabase vs. Neon final call
**Raised during:** Design 11 ADR-003
**Question:** PM recommends Supabase (auth bundled).
**Recommended path:** User confirmation.
**Status:** Open

## Q107: Hetzner vs. DigitalOcean for VPS
**Raised during:** Design 11 ADR-008
**Question:** PM proposes Hetzner (cheaper).
**Recommended path:** User confirmation.
**Status:** Open

## Q108: Static-site host: Vercel vs. Cloudflare Pages vs. Netlify
**Raised during:** Design 11 ADR-005
**Question:** PM proposes Vercel.
**Recommended path:** User confirmation.
**Status:** Open

## Q109: Demo-day environment
**Raised during:** Design 12
**Question:** Live production org or staging clone.
**Recommended path:** PM proposes production per Decision 16; static HTML as fallback.
**Status:** Open

## Q110: Demo-day rehearsal cadence
**Raised during:** Design 12
**Question:** Full rehearsal 48h before; data-priming check 24h before.
**Recommended path:** Filed.
**Status:** Open

## Q111: Recorded video backup for demo
**Raised during:** Design 12
**Question:** 15-min screencast 24h before demo day as a third-tier fallback.
**Recommended path:** PM proposes yes.
**Status:** Open

## Q112: Demo URL branding
**Raised during:** Design 12
**Question:** `pulse.onedge.co` or other.
**Recommended path:** User-decisive.
**Status:** Open

## Q113: Demo audience size
**Raised during:** Design 12
**Question:** Four named stakeholders only, or wider EDGE audience.
**Recommended path:** User-decisive; affects pacing.
**Status:** Open

---

## Phase 2 — post-spike findings (Q114–Q116, surfaced during the live Graphiti spike run)

## Q114: Graphiti × Kuzu FTS bootstrap — where does it live in Phase 4?
**Raised during:** Spike 3 live run 2026-05-20.
**Question:** Graphiti 0.29's `KuzuDriver.build_indices_and_constraints()` is a no-op; the Kuzu FTS extension is never installed and the four FTS indices (`episode_content`, `node_name_and_summary`, `community_name`, `edge_name_and_fact`) are never created. Without them, the first edge-resolution path during `add_episode` fails. **Where do we put the bootstrap in Phase 4 code?**
**Why it matters:** Without a fix, Pulse cannot ingest a single episode. The spike's harness contains a working bootstrap; Phase 4 needs an idiomatic home for it.
**Recommended path:** Ship a small `PulseKuzuDriver(KuzuDriver)` subclass under `03_build/core/graph/` whose `__init__` runs `INSTALL FTS; LOAD EXTENSION FTS;` + the four `CREATE_FTS_INDEX` statements (with `try/except` for "already exists"). Optionally upstream the fix to Graphiti via a PR. The subclass is the safer Phase 1 path.
**Status:** Open

## Q115: Explicit Anthropic model-ID pinning for Phase 4
**Raised during:** Spike 3 live run 2026-05-20.
**Question:** Graphiti 0.29 defaults to `claude-haiku-4-5-latest`, which the Anthropic API does not resolve (404). Pulse must pin pinned-date model IDs (e.g. `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`). Where do model IDs live as configuration?
**Why it matters:** Wrong default = entire LLM pipeline silently fails 404. Model rotation discipline is non-negotiable.
**Recommended path:** A single `03_build/core/llm/config.py` module that exports the pinned model IDs as constants + emits `LLMConfig` for Graphiti's clients. Every skill, retriever, and dispatch handler imports from this module — no string literals scattered across the codebase. Rotation = single-PR update.
**Status:** Open

## Q116: `.env` loading discipline — override=True or env scrub
**Raised during:** Spike 3 live run 2026-05-20.
**Question:** `load_dotenv()` defaults to `override=False`, which silently keeps an empty-string `ANTHROPIC_API_KEY` from the parent shell instead of using the `.env` value. Phase 4 startup code should never have this footgun.
**Why it matters:** Empty-key from a parent shell causes Pulse to fail at LLM-call time with a confusing 401, rather than at startup.
**Recommended path:** Phase 1 — use `override=True`. At AWS migration, move to a dedicated config layer (Pydantic Settings) that reads `.env` + env vars in a single explicit precedence order.
**Status:** Open

## Q117: Account-Card Ambient Ring as secondary agent-presence indicator (v1.5+)
**Raised during:** Session 10 (Pulse Bar Breathing hybrid lock)
**Question:** If post-Phase-1 use surfaces a felt need for per-account locality of agent presence (i.e., RMs want to know *which* account Pulse is working on without checking the queue), add the Account-Card Ambient Ring (Variant 3 from Phase 2.5) as a secondary indicator alongside the primary Pulse Bar.
**Why it matters:** V3 was the only variant communicating per-account locality. Phase 1 ships without it. If demand emerges, the variant is already designed and renderable (`01_design/agent_presence_variants/03_account_card_ring.html`) — it's an additive feature, not a redesign.
**Recommended path:** Defer to v1.5+ (filed as v1.5+ candidate #11 in PM_CONTEXT §12). Re-render Variant 3 against locked Tier-0 tokens when triggered. The Pulse Bar (Breathing) and the Account-Card Ring are visually compatible — they convey different information (global presence vs. per-account locality) and would compose without collision.
**Status:** Open (v1.5+ candidate)

---

## Phase 3 prep — opportunity-tracker review (Spike 4)

## Q118: Source narrowing — confirm "Glassdoor + Google removed"
**Raised during:** Spike 4 — `00_research/spikes/04_opportunity_tracker_review.md`
**Question:** User said "the third source never works." `jobboard_scanner.py:77` actually scans four: `["indeed", "linkedin", "glassdoor", "google"]`. Confirm: keep `["indeed", "linkedin"]` only?
**Why it matters:** Half-hour change; cleanest possible noise reduction. Decision needed before Phase 4 starts.
**Recommended path:** Narrow to LinkedIn + Indeed.
**Status:** Open

## Q119: Role catalog schema upgrade — full restructure or additive metadata
**Raised during:** Spike 4
**Question:** Promote `config/role-catalog.json` from flat strings to typed objects (`{name, remote_compatible, in_person_disqualifiers, aliases}`)? Or keep flat strings and add a parallel metadata file?
**Why it matters:** Schema upgrade is cleaner but breaks the existing loader. Parallel file is incremental but creates a second source of truth.
**Recommended path:** Full restructure. Loader change is ~5 lines (`role["name"]` instead of `role`); aligns with "no second source of truth" engineering principle.
**Status:** Open

## Q120: `off-scope` as a fourth tier value
**Raised during:** Spike 4
**Question:** Introduce a fourth `match_tier` value (`off-scope`) for on-site-only postings, OR silently filter to `tier=None` and never write the row?
**Why it matters:** `off-scope` preserves auditability (we know WHY a posting was excluded — useful for prompt tuning later). Silent filter loses the audit trail.
**Recommended path:** `off-scope` as a fourth tier. Pulse adapter skips ingestion (no Episode emitted); row persists in `expansion_intent_signals` with `processed_status='skipped:off-scope'`.
**Status:** Open

## Q121: opportunity-tracker's `sf_tasks.push_tasks_to_salesforce()` stays dormant
**Raised during:** Spike 4
**Question:** opp-tracker has a placeholder `push_tasks_to_salesforce()` function (`src/sf_tasks.py:79`). Confirm Phase 1 keeps this dormant so Pulse's Action Queue is the sole SFDC-write path (§6 rule 6).
**Why it matters:** Two write paths to SFDC = two approval surfaces. §6 rule 6 says only one.
**Recommended path:** Confirmed dormant. opp-tracker generates Task *recommendations* as data only; Pulse proposes them via Action Queue with human approval.
**Status:** Open

## Q122: opportunity-tracker's OpenAI dependency — migrate to Claude now or v1.5+?
**Raised during:** Spike 4 (Mitigation A in day-count estimate)
**Question:** Decision 13 says "migrate prompts from OpenAI to Claude before any production data flow." opp-tracker is currently OpenAI-based and is an *upstream* signal source (not user-facing). Migrate now (+0.5 days to Phase 4) or defer to v1.5+ (stays within Session 10 buffer)?
**Why it matters:** 0.5 days; PM_CONTEXT Decision 13 interpretation (spirit vs letter for upstream-only LLM use).
**Recommended path:** Defer to v1.5+. opp-tracker is internal-only; its LLM provider is implementation detail; no white-label violation. Contingent on PM accepting the Decision-13 spirit-vs-letter reading.
**Status:** Open

## Q123: Account tier field confirmed as `Segment__c` (resolves Q22)
**Raised during:** Spike 4
**Question:** Q22 asked for the SFDC Account tier field name. `opportunity-tracker/src/salesforce_client.py:24` reads `Segment__c` directly.
**Why it matters:** Resolves Q22. Phase 4 binds Pulse's tier policy to `Account.Segment__c`.
**Status:** **RESOLVED 2026-05-20 via this spike.** Field is `Account.Segment__c`. Value enumeration still pending Q21 (sandbox refresh).

## Q124: opportunity-tracker dashboard purple shade
**Raised during:** Spike 4
**Question:** opp-tracker's dashboard uses `BRAND = "#4a0f70"` (darker purple than Tier-0's `#6B46C1`). Re-skin to match Tier-0, or keep?
**Why it matters:** Visual coherence if RMs see both surfaces. Today the opp-tracker dashboard is admin-internal only.
**Recommended path:** Defer to v1.5+. Re-skin if the dashboard surfaces to RMs.
**Status:** Open (v1.5+ candidate)

## Q125: Skill 11 Enterprise EBR-tie-in pre-drafted language — Phase 1 or v1.5+?
**Raised during:** Spike 4 (Mitigation B in day-count estimate)
**Question:** Skill 11's Enterprise variant suggests pre-drafted EBR-tie-in language. Saves the RM a paragraph; ~0.25 days of Phase 4 scope.
**Recommended path:** Phase 1 ships *static* EBR-tie-in copy; dynamic-EBR-date insertion is v1.5+.
**Status:** **RESOLVED Session 11** — Mitigation B accepted (Decision log entry 41). Static copy in Phase 1; dynamic-date insertion deferred to v1.5+ candidate #14.

---

## Phase 3 Planning — questions surfaced during spec authoring (Q126–Q151)

## Q126: Champion identification heuristic (cross-references Q56/Q65)
**Raised during:** `02_planning/signals/churn_signal_contact_disengagement_v1.md`
**Question:** Phase 1 fallback = most-recent Chorus customer-side participant. Need to confirm this works in practice; may surface as a tuning need in Layer 8 metrics.
**Status:** Open (Phase 4 instrumentation will inform).

## Q127: Email-reply ingestion mechanism
**Raised during:** `churn_signal_contact_disengagement_v1.md`
**Question:** SFDC `Activity` records vs. pure-email-reply parsing (Gmail/Outlook OAuth)?
**Recommended path:** SFDC `Activity` is sufficient for Phase 1 (RM logs replies in CRM); pure-email parsing is v1.5+.
**Status:** Open.

## Q128: Confirmation of Skill 01's sentiment-vector axes
**Raised during:** `churn_signal_sentiment_decline_v1.md` (cross-references Q51)
**Question:** PM proposed warmth / frustration / urgency / momentum. User to confirm before Phase 4 codification.
**Status:** Open.

## Q129: Per-customer sentiment-baseline learning
**Raised during:** `churn_signal_sentiment_decline_v1.md`
**Question:** Some customers run hot (frustration tone is baseline); some run cold. v1.5+ Mechanism 2 could extend to per-Customer baselines.
**Status:** Open (v1.5+ filing).

## Q130: Renewal source priority (Opportunity vs Account_Plan__c)
**Raised during:** `churn_signal_renewal_period_silence_v1.md`
**Recommended path:** Opportunity first; Account_Plan__c as fallback. Pending Q21 sandbox refresh clarification.
**Status:** Open.

## Q131: Non-renewal customers (PAYG / month-to-month)
**Raised during:** `churn_signal_renewal_period_silence_v1.md`
**Status:** Open (v1.5+ filing).

## Q132: Competitor watch-list
**Raised during:** `churn_signal_competitor_mention_v1.md`
**Question:** Pre-populate a list of known competitors (Skill 01 weights matches higher)?
**Recommended path:** Yes; Admin-maintained in policy config.
**Status:** Open.

## Q133: Past-tense detection robustness for competitor mentions
**Raised during:** `churn_signal_competitor_mention_v1.md`
**Status:** Open; addressed by Skill 01 golden-trace tests.

## Q134: Composition of `expansion_signal_job_posting_match` + `expansion_signal_verbal_capacity_mention`
**Raised during:** `expansion_signal_verbal_capacity_mention_v1.md`
**Question:** When both fire on same customer in same window, one card or two?
**Recommended path:** One card (Skill 11 composition logic per spec 028).
**Status:** Open (Phase 4 implementation enforces).

## Q135: `general`-tier-by-account allowlist for job-posting signal
**Raised during:** `expansion_signal_job_posting_match_v1.md`
**Status:** Open (admin tuning post-launch).

## Q136: Talent welfare signal taxonomy completeness
**Raised during:** `talent_burnout_signal_v1.md` (also affects growth + pay variants)
**Recommended path:** Phase 1 covers burnout, growth, pay, AI-displacement. Week-1 review with VP-CS for additions.
**Status:** Open.

## Q137: Privacy guardrail behavior for pay-concern admin views
**Raised during:** `talent_pay_concern_v1.md`
**Recommended path:** Strip $ from RM-tier why_oneline only; Admin view shows full context.
**Status:** Open (spec 042 RBAC implements).

## Q138: Per-customer baseline for case-pattern signal
**Raised during:** `escalation_signal_case_pattern_v1.md`
**Status:** Open (v1.5+ Mechanism 2).

## Q139: Category-severity-floor defaults for case signals
**Raised during:** `escalation_signal_case_pattern_v1.md`
**Recommended path:** Separate signal (`escalation_signal_severity_jump_v1`) handles single-severe cases.
**Status:** Resolved — split into two signals.

## Q140: Severity-rank map confirmation for cases
**Raised during:** `escalation_signal_severity_jump_v1.md`
**Status:** Open — user to confirm ranking of Risk-Talent-Competency vs Risk-Talent-Resignation.

## Q141: `Advocacy_Participation_History__c` SFDC field existence
**Raised during:** `recognition_signal_advocacy_candidate_v1.md`
**Status:** Open; pending Q21 sandbox refresh. If absent, Phase 1 uses a Pulse-internal table.

## Q142: Stage-history tracking (Pulse-side mirror table)
**Raised during:** `client_termination_pattern_v1.md`
**Recommended path:** Yes — `pulse.associate_stage_history` table written by SFDC adapter (spec 012).
**Status:** Open; baked into spec 012 DoD.

## Q143: Conversion-to-permanent suppression heuristic
**Raised during:** `client_termination_pattern_v1.md`
**Status:** Open (v1.5+ explicit field).

## Q144: Per-customer silence baseline
**Raised during:** `account_silence_pattern_v1.md`
**Status:** Open (v1.5+).

## Q145: Data-gap → Layer 8 wiring
**Raised during:** `account_silence_pattern_v1.md`
**Status:** Open; baked into spec 044 (Layer 8 Mechanism 1) DoD.

## Q146: Consolidated `recognition_signal_v1` for Skill 07 structural triggers
**Raised during:** Skill 07 cross-reference append
**Status:** Open (v1.5+).

## Q147: Consolidated `onboarding_signal_*_v1` for Skill 08 structural triggers
**Raised during:** Skill 08 cross-reference append
**Status:** Open (v1.5+).

## Q148: Phase 4 Fly.io region selection
**Raised during:** spec 001 (Project bootstrap)
**Recommended path:** US East (closest to most EDGE customers + Anthropic API).
**Status:** Open; Week 1 user confirmation.

## Q149: `Topic` node creation policy (upfront curated vs. LLM-extracted with dedup)
**Raised during:** spec 005 (Three-Graph composition)
**Recommended path:** LLM-extracted with dedup pass at end of Phase 4 Week 3.
**Status:** Open.

## Q150: Signal versioning at runtime
**Raised during:** spec 017 (Signal Definition Library runtime)
**Question:** When `v2` of a signal lands, does the runtime support both `v1` (deprecated) and `v2` simultaneously?
**Recommended path:** Yes; controlled by `pulse_settings.active_signal_versions` config.
**Status:** Open.

## Q151: Force-graph library final pick for Constellation view
**Raised during:** spec 041 (Constellation view)
**Question:** react-force-graph vs d3-force vs cytoscape.
**Recommended path:** PM picks at spec-author time post-Week-4 exploration.
**Status:** Open.

## Q152: ruff B008 FastAPI exemption breaks on type-annotated `Depends()`
**Raised during:** spec 031 (Action Queue API)
**Question/finding:** ruff's `flake8-bugbear` B008 ("do not call functions in argument defaults") special-cases FastAPI's `Depends`/`Query`/`Header` so the standard `param = Depends(fn)` default doesn't trip the lint — but ONLY when the parameter is annotated with a primitive type (`str`, `int`, …). When the dependency is annotated with a **custom class** (e.g. `caller: Caller = Depends(require_caller)`), ruff fails to recognize it as a FastAPI dependency and raises B008 on every such route. Bisected and reproduced (a `str`-annotated `Depends` passes; the same call annotated `Caller` fails). `Query`/`Header` are unaffected.
**Recommended path / fix:** Use the modern FastAPI `Annotated` form — `caller: Annotated[Caller, Depends(require_caller)]` — which is B008-clean and the FastAPI-recommended style. Applied throughout `api/actions.py` and `api/dispatch.py`. **Future-team note:** prefer `Annotated[T, Depends(...)]` for all DI params (not just custom-class ones) to avoid the foot-gun; do NOT reach for `# noqa: B008` or add `fastapi.Depends` to `extend-immutable-calls` (the existing primitive-annotated routes in `api/admin/kill_switch.py` rely on the built-in exemption and need no config change).
**Status:** Resolved (informational finding; no action needed beyond the Annotated convention).

## Q153: SFDC read-latency SLO — `sf` CLI per-query floor vs <500ms target
**Raised during:** spec 012 all-8-objects verification (Spike 6, Gate-2 deliverable)
**Question/finding:** The all-8-objects benchmark (`03_build/scripts/sfdc_bench.py`, N=10/object against production) verified reachability **PASS (8/8)** but measured per-query **p95 ≈ 2.5s** (p50 ≈ 1.5s) — ~3–5× over the <500ms target. Root-cause isolated: a 1-row query costs ~1.8s while `sf --version` boots in ~0.2s, so the ~1.5s floor is **per-invocation org-auth + JSForce connection setup inside `sf data query`**, not Salesforce API compute or result-set size. No SOQL tuning can bring the `sf`-subprocess path under 500ms.
**Recommended path:** Accept for Phase 1 — the 500ms SLO does not apply to the SFDC poll path. Production ingestion is the Activepieces `sfdc_poll_changes` 5-min cron (latency-insensitive; ~12s/cycle for all 8 objects ≪ 5-min budget); the latency-sensitive `/webhooks/sfdc` → ingest hop never calls `sf`. For any future **interactive/real-time** SFDC read, replace the per-query `sf` subprocess with a persistent authenticated REST client (reuse one access token + an `httpx` pool, or `simple-salesforce`) to drop the ~1.5s setup. **v1.5+ optimization; no Phase-1 code change.**
**Status:** Open (informational; remedy deferred to v1.5+ interactive-read work). See `00_research/spikes/06_sfdc_all_objects_verification.md`.

## Q154: opportunity-tracker repo adoption — DEdge-max (gone) → Pulse-owned sibling
**Raised during:** Session 16 (Phase-4 Week 4-5 follow-up)
**Question/finding:** The upstream `DEdge-max/opportunity-tracker` repo became unreachable (account/mailbox shut down) and its production daily scan stopped running. Pulse depends on opportunity-tracker as an expansion-signal source (specs 015/016), but the last-known-good code existed only as a local working copy (`ai-rm/opportunity-tracker/`, a clone of the now-dead origin) — with uncommitted local edits, so it needed careful adoption rather than a blind push.
**Recommended path / resolution:** Adopt the code into a Pulse-owned sibling repo **`edgelabsadmin-glitch/pulse-opp-tracker`** with fresh `[INIT]` history (acknowledges origin, claims no continuity). Landed on that repo's `main`: SPEC-004 SFDC-write safety guard (`[OPP-001]`) and SPEC-015 mirror-write into `pulse.expansion_intent_signals` (`[OPP-015]`), plus a Fly.io deploy bundle (`[OPP-001]`) that **supersedes Decision 39** — the daily job moves from GitHub Actions to a Fly cron worker (`pulse-opp-tracker.fly.dev`, app `pulse-opp-tracker`, region `sin`). **SPEC-016 matcher precision fix is NOT yet applied** (the prepared patch was absent from the adopted code; deferred — see spec 016 note). A stray uncommitted default-password edit in `dashboard/app.py` was dropped, not carried forward. Push to GitHub and the Fly deploy are operator steps (the authenticated `gh` account lacks access to the target repo).
**Status:** Resolved (Session 16, 2026-05-21).

---

## Resolved

### Session 5 (2026-05-19) — Lock-first items
- **Q1** — CEO demo deadline. **Resolved: 4 weeks; target 2026-06-16.**
- **Q2** — Real Salesforce / Chorus / Zoom vs. synthetic data. **Resolved: live production data; no PHI redaction needed; no PHI in RM calls.**
- **Q6** — HIPAA posture. **Resolved: demoted from gating workstream to standing standard (§6 rule 2). RMs don't talk about patient information; AWS-only hosting + audit log are sufficient.**
- **Q7** — EDGE doc scope expansion vs. agentic. **Resolved: §13 EDGE Coverage Map locked into PM_CONTEXT; EDGE doc is the floor of scope, Pulse exceeds it (§13.6).**

### 2026-05-20 — Spike 3 live run
- **Q26** — Anthropic API key provisioning for live Graphiti spike. **Resolved: keys provided 2026-05-20; live spike executed; preliminary GO converted to confirmed GO.** Ingestion P95 8.9s/episode; cross-entity query 0.3s; cross-entity correctness verified (vendor-consolidation theme returned only the Acrisure edge, did not over-recall to Pinnacle). See `00_research/spikes/03_graphiti_verification.md` §F + §G. Three Phase-4 engineering findings filed as Q114 (FTS bootstrap), Q115 (model-ID pinning), Q116 (`.env` override).

### 2026-05-20 — Spike 4 (opportunity-tracker review)
- **Q22 / Q123** — Account tier field. **Resolved: `Account.Segment__c`** confirmed via `opportunity-tracker/src/salesforce_client.py:24`. Value enumeration still pending Q21 (sandbox refresh).

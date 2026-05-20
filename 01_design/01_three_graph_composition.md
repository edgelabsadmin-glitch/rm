# Design 01 — Three-Graph Composition

**Phase:** 2 (Design)
**Tier:** 1 — first-week lock
**Status:** Draft, Phase 2

---

## Purpose

Define how Pulse's three internal knowledge structures — **Temporal Context Graph**, **Skills Layer**, and **Account/Talent Relationship Graph** — fit together. This is the single most architecturally consequential design call in Phase 2. It determines: where entities live, how queries traverse them, how the agent receives context, and what physical infrastructure runs.

Per glossary (PM_CONTEXT §11), all three names are **internal only** — the white-label rule (§6 rule 1) means none of these names surface in user-facing copy.

---

## Inputs

- **Episodes** from the Signal Source Adapter layer (Design 02). One Episode per signal — a Chorus call summary, an `RM_Outreach__c` update, an `Associates__c` stage change, a risk-tagged `Case`, a calendar event.
- **Canonical EDGE entity IDs** from Salesforce: Account.Id, Contact.Id, Associates__c.Id, User.Id (RM identity), Case.Id, plus role-catalog codes for talent roles.
- **Skill taxonomy** — a small ontology of placed-talent skills, derived initially from EDGE's 53-role catalog (Insurance / Medical / Dental verticals) supplemented by canonical occupational data. Phase 1 keeps this lite; Phase 2+ adds full drift detection (Option C in PM_CONTEXT §3).

## Outputs

- **A queryable, bi-temporally-aware context surface** that the agent layer (Design 03 / 05) reads from to answer questions like §13.4 examples: *"how many people at Mendota feel burned out?"*, *"prep me for my Pinnacle meeting"*, *"has sentiment at TechCorp improved since we launched their AI tool?"*
- **Cross-graph identity guarantees** — a single SFDC Account.Id resolves to the same Customer node across all three graphs.
- **A structured `ContextBundle`** returned to the agent on demand, containing temporal facts + relationship neighbors + relevant skill mappings for a given entity-of-interest.

---

## Behavior

### Composition model — one logical graph, three lenses

Phase 1 ships **one physical embedded graph database** (Kuzu, per PM_CONTEXT §3 lock and Spike 3 GO verdict). The three "graphs" named in PM_CONTEXT §11 are **logical lenses over the same store**, distinguished by node/edge type namespaces. This is the simplest viable composition and avoids cross-store join overhead.

```
                         ┌──────────────────────────────────────┐
                         │           Single Kuzu instance        │
                         │   (embedded; ~/.pulse/state/kuzu.db)  │
                         │                                       │
   ┌─────────────────┐   │  ┌────────────────────────────────┐  │
   │ Signal Source   │──▶│  │  Episodes (provenance layer)   │  │
   │ Adapters        │   │  │  — every signal becomes one    │  │
   │ (Design 02)     │   │  └────────────────────────────────┘  │
   └─────────────────┘   │             │                         │
                         │             ▼                         │
                         │  ┌────────────────────────────────┐  │
                         │  │  Entity Nodes (typed)          │  │
                         │  │  Customer • Talent • RM •      │  │
                         │  │  Case • Contact • Opportunity  │  │
                         │  └────────────────────────────────┘  │
                         │             │                         │
                         │             ▼                         │
                         │  ┌────────────────────────────────┐  │
                         │  │  Edges (bi-temporal, typed)    │  │
                         │  │  placed_at • manages • raised_ │  │
                         │  │  concern_about • replaced_by • │  │
                         │  │  speaks_in_call • has_skill •  │  │
                         │  │  reports_to • mentions         │  │
                         │  └────────────────────────────────┘  │
                         │             │                         │
                         │  ┌──────────┴──────────┐              │
                         │  ▼                     ▼              │
                         │ Lens A:           Lens B:             │
                         │ Temporal          Skills (lite):      │
                         │ Context Graph     Talent → Role →     │
                         │ — uses Episode +  Skill nodes;        │
                         │ Entity + Edge     uses has_skill edge │
                         │ with valid/       └──────────┬────────┘
                         │ invalid times                │
                         │                              ▼
                         │                  Lens C:                
                         │                  Account/Talent         
                         │                  Relationship Graph     
                         │                  — uses Customer/       
                         │                  Talent/RM nodes +      
                         │                  placed_at / manages /  
                         │                  reports_to edges       
                         └──────────────────────────────────────┘
```

**Why one physical graph, three lenses?**
- The three "graphs" share most entities (every Customer appears in all three; every Talent appears in two). Splitting them physically forces synthetic cross-store joins on every query.
- Kuzu handles bi-temporal queries natively, and the bi-temporal edges live across all three lenses (a `has_skill` edge from a Talent to a Skill node also has a `valid_at`/`invalid_at` interval — it's still temporal).
- Single-store keeps the operational surface tiny in Phase 1 (one DB file, one backup, one upgrade path). Aligns with the resourceful-OSS posture (§6 rule 18) and the under-$20/mo Phase 1 infrastructure target (PM_CONTEXT §5).

**When would we split?** If Phase 2+ skill drift detection generates 10–100× the edges of the Temporal Context Graph (e.g., snapshotting every talent's skill profile weekly), Lens B may move to its own store. Filed as v1.5+ candidate.

### Entity types (Phase 1 lock)

Declared as Pydantic models, passed to Graphiti as `entity_types`:

| Type | SFDC source | Internal ID | Notes |
|---|---|---|---|
| **Customer** | `Account` | `Account.Id` | Tier (SMB/Mid-Market/Enterprise) carried as property. |
| **Talent** | `Associates__c` | `Associates__c.Id` | Stage (Active/Replaced/Terminated) carried as property; stage transitions create bi-temporal `was_in_stage` edges. |
| **RM** | `User` (where role = RM) | `User.Id` | RM identity; owns Customer + Talent records. |
| **Contact** | `Contact` | `Contact.Id` | Customer-side stakeholder (champion, decision-maker, detractor). |
| **Case** | `Case` (risk-tagged only) | `Case.Id` | The formal-issue layer. Risk category carried as property. |
| **Opportunity** | `Opportunity` | `Opportunity.Id` | Renewal/expansion pipeline. |
| **Skill** | `Role__c` enum + role-catalog.json | catalog-code | A skill is a normalized occupational tag (e.g. `medical-coder-ii`). Phase 1 = lite; Phase 2 adds drift detection. |
| **AccountPlan** | `Account_Plan__c` | `Account_Plan__c.Id` | Strategic plan; read-only in Phase 1. |

### Edge types (Phase 1 lock)

Declared as Pydantic models, passed to Graphiti as `edge_types`. **All edges are bi-temporal** (`valid_at`, `invalid_at`, `created_at`, `expired_at`) per Graphiti's model:

| Edge | From → To | Examples |
|---|---|---|
| `placed_at` | Talent → Customer | "Marcus Wells placed at Acrisure as Dental Coder II from 2026-01-15 to 2026-05-10." |
| `manages` | RM → (Customer or Talent) | Books-of-business edge. Two flavors: `manages_customer` and `manages_talent` — kept distinct because RMs can be reassigned independently on each side. |
| `raised_concern_about` | (Customer or Talent) → (Customer or Talent or Topic) | A specific worry surfaced in a call or note. |
| `replaced_by` | Talent → Talent | Chain of replacement; sourced from `Prior_Associate_Replaced__c`. |
| `speaks_in_call` | Contact or RM → Episode | Provenance: which human said what in which call. |
| `has_skill` | Talent → Skill | Phase 1 lite. Phase 2 adds drift tracking. |
| `reports_to` | Contact → Contact | Customer-side org chart, when known. |
| `mentions` | Episode → (Customer or Talent or Topic) | Extracted by the LLM during ingestion. |
| `escalated_via` | Case → (Talent or Customer) | Joins risk-tagged Cases to the entity they're about. |
| `has_plan` | Customer → AccountPlan | Strategic-plan attachment. |

### Cross-graph identity scheme

**The rule:** Salesforce IDs are the canonical key for every entity that originates in Salesforce. Pulse maintains an `id_map` table outside Kuzu (in Postgres — see Design 10) for non-SFDC entities (Skills from the role-catalog; Topics extracted by the LLM).

```
SFDC Id (e.g. "001A5000003j2nXIAQ")     ┐
                                          │
                                          ├──▶ Pulse internal entity_id (Kuzu node)
Role-catalog code (e.g. "ins-coder-ii")  ┤
                                          │
LLM-extracted topic slug                  ┘
```

**Why a single canonical key per entity (not multiple IDs per type):**
- The agent layer asks "tell me about Customer X" and needs *one* answer that joins temporal facts + relationships + skills.
- Cross-system writes (Action Queue → Salesforce) need a single ID to write back to (`Account.Id`, not a Pulse-internal UUID).
- Backup/restore semantics are clearer with a single key per entity.

### Cross-graph query interface — the ContextBundle

The agent layer never queries the graph directly. Instead, it calls **one of three named retrievers**:

```python
# Pseudocode — Phase 4 implementation contract

ContextBundle = TypedDict({
    "entity": EntityRef,               # The focal Customer/Talent/etc.
    "temporal_facts": list[Fact],      # Bi-temporal edges + episode quotes,
                                        # ranked by relevance + recency
    "relationships": list[Edge],       # Direct neighbors (1-hop)
    "skills": list[SkillBinding],      # Only when entity is a Talent
    "recent_episodes": list[Episode],  # Top N raw episodes for quote-citing
    "as_of": datetime,                 # Bi-temporal point-of-view
})

def get_customer_context(customer_id, as_of=None) -> ContextBundle: ...
def get_talent_context(talent_id, as_of=None) -> ContextBundle: ...
def get_rm_context(rm_id, as_of=None) -> ContextBundle: ...
```

**Behavior:**
- Each retriever runs a Graphiti hybrid search (semantic + BM25 + graph traversal) bounded to the entity's neighborhood.
- The retriever assembles `temporal_facts`, `relationships`, and `recent_episodes` from the same Kuzu instance using the entity-type/edge-type filters above.
- `skills` is populated only for Talent retrievers (Lens B traversal).
- The agent receives a single bundle and reasons over it; never issues raw Cypher/SOQL.

**Why named retrievers, not "raw graph query":**
- The Senior Developer review will reject any pattern where the agent's runtime is itself authoring database queries unbounded.
- Named retrievers are testable in isolation (golden-trace test per retriever).
- Named retrievers are the natural surface for caching, rate-limiting, and auditing (Design 04 event log includes which retrievers were called).
- Skill files (Design 05) declare which retrievers they require — explicit dependency graph, not implicit.

### Physical home

| Component | Phase 1 | Phase 2+ |
|---|---|---|
| Kuzu DB file | `~/.pulse/state/kuzu.db` (single VPS) | AWS EBS volume + snapshot policy |
| `id_map` table | Postgres (Supabase or Neon, per fast-stack-first lock) | RDS Postgres |
| Backup cadence | Nightly snapshot of `kuzu.db` to S3-compatible object store | Per AWS migration plan §12 #3 |

---

## EDGE Coverage references

This artifact covers, in §13:

- **§13.2 Workflow 1** row "Per-customer persistent knowledge thread" — directly satisfied by the Temporal Context Graph lens with bi-temporal edges.
- **§13.3 Workflow 2** rows "Aggregate sentiment, identify red flags" and "Generate structured brief" — the ContextBundle is the data structure the briefing skill (Design 05) consumes.
- **§13.4 Customer Intelligence Hub** — every example query in §13.4 is a `get_customer_context()` call with a follow-up filter, except "Which talent across ALL accounts have raised pay concerns this quarter?" which is a graph-wide search bounded by a relationship type (`raised_concern_about`) and a time window.
- **§13.5 JD area "Talent Relationship & Engagement"** — the dual-Talent edge model (`placed_at`, `manages_talent`, `has_skill`) directly supports talent-side workflows as a first-class concern.
- **§13.6 #2** — replaces EDGE's "persistent Claude conversation per customer" misconception with the correct shape (a temporal context graph).

---

## Open questions

- **Q27** — Should `manages` be two distinct edges (`manages_customer`, `manages_talent`) or one polymorphic edge with a `role` property? Two edges is more explicit; one is more compact. PM recommendation: two edges in Phase 1 for clarity; reconsider if it bloats the graph.
- **Q28** — Should `Skill` nodes be globally shared (one node per skill code, all Talent with that skill link to it) or per-Talent (each Talent has its own skill nodes)? Globally shared is the conventional shape and enables "find all talent with skill X" cheaply. PM recommendation: globally shared.
- **Q29** — Where do `Topic` nodes come from (e.g., "vendor consolidation", "AI displacement", "burnout")? LLM-extracted on first ingestion, with a dedup pass? Hand-curated taxonomy? PM recommendation: LLM-extracted with a Phase-2-end pass to consolidate near-duplicates.
- **Q30** — Custom-types schema versioning. When Phase 2 adds full skill drift detection, edge schemas change. How does Pulse handle a schema migration on Kuzu? Filed for Phase 3 planning.

---

## What this is NOT

- **Not three physical graph databases.** One Kuzu instance with logical lenses. Splitting is a v1.5+ candidate, not a Phase 1 goal.
- **Not a generic knowledge-graph layer that anyone can query.** The agent calls *named retrievers*; ad-hoc graph queries are an internal admin tool only.
- **Not a place where derived analytics live.** Aggregations (per-Customer health scores, cross-account patterns) are computed by skills (Design 05) on top of `ContextBundle`s, not stored as nodes in the graph. The graph stores *facts and relationships*, not *opinions*.
- **Not where Pulse stores audit logs.** Audit and reasoning capture live in Postgres (Design 04). Mixing operational state into the temporal graph would confuse the bi-temporal semantics.
- **Not user-facing.** The names "Temporal Context Graph", "Skills Layer", "Account/Talent Relationship Graph" are internal. No UI surface mentions them. No copy references them.

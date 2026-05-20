# Spec 005 — Three-Graph composition (Kuzu schema + entity/edge types + namespaces)

**Maps to:** §14 Memory layer; Design 01 (Three-Graph composition); §13.2 row "Per-customer persistent knowledge thread."
**Depends on:** specs 001, 002 (bootstrap + PulseKuzuDriver).
**Effort:** 1.5 days.

## Description

Implement the Three-Graph composition per Design 01. Single physical Kuzu instance with three logical lenses (Temporal Context, Skills Layer lite, Account/Talent Relationship) discriminated by node-type / edge-type filters. Pydantic models for the Phase-1-locked entities and edges. Namespaces for multi-RM isolation per Design 01 §"Cross-graph identity scheme."

The substantive work is two-fold: (a) declare the typed entities (Customer, Talent, RM, Contact, Case, Opportunity, Skill, AccountPlan) and edges (`placed_at`, `manages`, `raised_concern_about`, `replaced_by`, `speaks_in_call`, `has_skill`, `reports_to`, `mentions`, `escalated_via`, `has_plan`) per Design 01 §"Entity types"/§"Edge types"; (b) wire them into Graphiti's `entity_types` / `edge_types` constructor params so the LLM extraction respects them.

## Inputs

- Graphiti 0.29 installed.
- `PulseKuzuDriver` from spec 002.
- `make_llm_config()` from spec 003.
- The schema in Design 01.

## Outputs

- `03_build/pulse/core/memory/types.py` exporting Pydantic models for the 8 entities + 10 edges from Design 01.
- `03_build/pulse/core/memory/graph.py` exporting a `make_graphiti(db_path)` factory that constructs Graphiti with `PulseKuzuDriver` + Pulse's typed entities/edges + `AnthropicClient(make_llm_config("haiku"))` for extraction + `OpenAIEmbedder()` (Spike 3 §C) for embeddings.
- An `id_map` Postgres table (per Design 01 §"Cross-graph identity scheme") with schema documented in spec 008.

## Definition of Done

- [ ] All 8 entity Pydantic models match Design 01 §"Entity types" exactly.
- [ ] All 10 edge Pydantic models match Design 01 §"Edge types" exactly.
- [ ] `make_graphiti()` returns a usable instance; ingesting one Episode produces typed entities and edges (verified by querying back via Cypher/Kuzu).
- [ ] Bi-temporal queries work: ingest one Episode at `valid_at=t1`; query "as_of t0" returns no edge; query "as_of t1+1" returns the edge.
- [ ] Namespace isolation works: two Episodes in different namespaces do not cross-pollinate (verified by query).
- [ ] Golden-trace test: ingesting the Spike 3 synthetic dataset (8 episodes) produces the expected Customer entities (Acrisure + Pinnacle) and expected `placed_at` / `raised_concern_about` edges.

## Tests

- **Unit:** model-validation tests for each entity + edge type.
- **Integration:** Spike 3 harness adapted to use `make_graphiti()` — passes end-to-end.
- **Golden-trace:** the 8-episode dataset produces a known node + edge count (recorded as fixture).

## Signal definitions involved

None directly — this spec provides the substrate that all signals query.

## Open questions

- **Q149:** Should `Topic` nodes be created upfront for the cross-account pattern themes (e.g., "vendor consolidation", "AI displacement"), or LLM-extracted at first ingestion? PM proposes LLM-extracted with dedup pass at end of Phase 4 Week 3 (Q29 disposition). Filed.

## What this is NOT

- Not the named retrievers (spec 006).
- Not the cross-account retriever (spec 007).
- Not where Episodes come from (specs 011-015).

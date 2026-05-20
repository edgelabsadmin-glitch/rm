# Spec 006 — Named retrievers

**Maps to:** §14 Memory layer; Design 01 §"Cross-graph query interface — the ContextBundle"; multiple §13.4 rows.
**Depends on:** spec 005.
**Effort:** 1.0 day.

## Description

Implement the three named retrievers Design 01 specifies: `get_customer_context`, `get_talent_context`, `get_rm_context`. Each returns a `ContextBundle` dataclass containing temporal facts (bi-temporal edges + episode quotes), 1-hop relationships, skill bindings (for Talent), recent episodes for citation, and an `as_of` timestamp.

The agent layer (skills) never queries the graph directly — only via these named retrievers. This is the chokepoint that satisfies §6 rule 8 (no black-box detection) at the data-retrieval level: every retriever call is loggable and testable in isolation.

## Inputs

- Graphiti instance from spec 005.
- `entity_id` (SFDC Account.Id / Associates__c.Id / User.Id).
- Optional `as_of: datetime` for bi-temporal queries.

## Outputs

- `03_build/pulse/core/memory/retrievers.py` exporting:
  - `async def get_customer_context(customer_id: str, as_of: datetime | None = None) -> ContextBundle`
  - `async def get_talent_context(talent_id: str, as_of: datetime | None = None) -> ContextBundle`
  - `async def get_rm_context(rm_id: str, as_of: datetime | None = None) -> ContextBundle`
- `ContextBundle` dataclass (typed-dict form per Design 01 §"Cross-graph query interface").

## Definition of Done

- [ ] All three retrievers async (per ADR-001).
- [ ] Each retriever runs a Graphiti hybrid search bounded to the entity's neighborhood.
- [ ] `temporal_facts`, `relationships`, `recent_episodes` populated correctly given Spike 3 fixture data.
- [ ] `skills` only populated when entity is Talent (Lens B traversal).
- [ ] `as_of` parameter produces different results vs. current-time queries on bi-temporal fixtures.
- [ ] Langfuse `@observe()` decorator wrapped around each retriever (per ADR-003 §"What gets instrumented").

## Tests

- **Unit:** mocked Graphiti — verify each retriever calls the right search recipe + assembles the right bundle.
- **Integration:** real Graphiti with Spike 3 fixture — `get_customer_context("acrisure_id")` returns the expected entity + ≥3 edges + ≥2 episodes.
- **Golden-trace:** Langfuse trace tree shows `retriever_get_customer_context` span with nested `graphiti.search` span.

## Signal definitions involved

None directly — retrievers serve every signal definition that needs current/historical context.

## Open questions

None.

## What this is NOT

- Not the cross-account retriever (spec 007 — separate because it has different scope semantics).
- Not where signals fire — retrievers serve signals; firing logic is in skill / signal-definition runtime.

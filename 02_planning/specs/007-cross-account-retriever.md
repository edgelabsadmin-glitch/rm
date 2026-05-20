# Spec 007 — Cross-account retriever

**Maps to:** §14 Memory layer; Design 01 (open question Q77 disposition); Skill 10 dependency.
**Depends on:** spec 005.
**Effort:** 0.5 day. **Scheduled explicitly before Skill 10 (spec 027) per build-plan Cluster 4 spec-ordering principle 3.**

## Description

Implement `find_pattern_across_customers(theme: str, time_window_days: int = 30)` — the cross-account retriever Skill 10 (`cross-account-pattern-finder`) depends on. Phase 1 implementation per Q77 disposition: exact topic-node match in Graphiti (look up the `Topic` node by name; return all `mentions` edges from any Customer to that Topic node in the time window). Embedding-similarity matching is deferred to v1.5+.

Output is a list of `CrossAccountMatch` records: `(customer_id, customer_name, episode_id, quote, date)`. Skill 10 aggregates these into pattern cards.

## Inputs

- Graphiti instance from spec 005.
- `theme: str` — the topic name (matches a `Topic` node's `name` property).
- `time_window_days: int` (default 30).
- Optional `min_support: int` (default 3) — minimum distinct customers required for the result to be considered a pattern (Skill 10 enforces; this retriever returns all matches).

## Outputs

- `03_build/pulse/core/memory/retrievers.py` adding:
  - `async def find_pattern_across_customers(theme: str, time_window_days: int = 30, min_support: int = 3) -> list[CrossAccountMatch]`
- `CrossAccountMatch` dataclass.

## Definition of Done

- [ ] Function is async; Langfuse-instrumented.
- [ ] Exact-topic-node match works: given a `Topic` node "vendor consolidation" with edges to 3 distinct Customers, the call returns 3+ matches.
- [ ] Time-window filter works: matches outside the window are excluded.
- [ ] `min_support` is informational only (returned in result metadata); the retriever does NOT filter on it — Skill 10 makes that call.
- [ ] Demographic-denylist guardrail is enforced at retriever level: matches whose Topic name appears in the protected-class denylist (`pulse/core/memory/denylist.py`) raise `ValueError` (Skill 10 should never request such themes — defense in depth).

## Tests

- **Unit:** mocked Graphiti.
- **Integration:** Spike 3 fixture + an added Topic node — verify cross-customer match.
- **Negative:** call with a denylisted theme raises ValueError.

## Signal definitions involved

- `client_termination_pattern_v1` — Skill 10's cross-account aggregation of this signal uses this retriever.
- Cross-customer aggregations of `churn_signal_competitor_mention_v1`, `expansion_signal_verbal_capacity_mention_v1`, `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1`, `escalation_signal_case_pattern_v1` all consume this retriever via Skill 10.

## Open questions

- See Q77 (cross-account retriever shape disposition — exact match Phase 1, embedding similarity v1.5+).
- See Q78 (pseudonymization mechanism — implemented in Skill 10, not here).

## What this is NOT

- Not Skill 10 — Skill 10 (spec 027) consumes this retriever; the retriever is dumb infrastructure.
- Not embedding-similarity search — Phase 1 exact-match only.
- Not where pseudonymization happens — Skill 10's responsibility.

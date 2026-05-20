# Skill 10 — cross-account-pattern-finder

**Lifecycle stage:** expansion (and intelligence — the "agentic upgrade" §13.6 row 1)
**Phase:** 1
**Tier-aware:** no (patterns are cross-customer; the *action* derived from a pattern may be tier-aware).
**Scope:** global (only Phase 1 skill with global scope).

## Trigger
**Schedule-driven (weekly Sunday 10:00 local).** Runs across all customers in the book of business (per-RM scope first; then optionally a roll-up across the whole org for Admin and VP of Client Success consumption).

## Inputs
- Retrievers required: a new **cross-account retriever** (Design 01 Q to file: `find_pattern_across_customers(theme, time_window)`). Phase 1 implementation: graph-wide search for `mentions` and `raised_concern_about` edges of the same Topic across multiple Customer entities.
- External calls (READ ONLY): none beyond graph queries.
- Per-Profile Markdown read: relevant Customer profiles when patterns surface.
- Policy inputs: none beyond default.

## Behavior
Surfaces **recurring themes across multiple customers** that no single-customer view would catch. Examples from the EDGE doc and synthetic spike data:
- *"3 customers in the last 30 days raised vendor consolidation concerns"* — Sales / VP of CS should know.
- *"5 talent across the Insurance vertical mentioned AI displacement concerns"* — Talent Dev should plan a cohort response.
- *"4 customers asked about expanding to dental coding in the last 60 days"* — Sales has a fertile expansion segment.

Output is a small set of **pattern cards** rather than per-customer action cards. Each pattern card:
- Names the theme.
- Cites at least 3 customers / talent involved with verbatim quotes.
- Proposes a portfolio-level response (e.g., "schedule a Sales meeting on vendor-consolidation messaging", "Talent Dev to prepare AI-displacement cohort training").

The pattern cards land in the **Overall view** of the Action Queue (Design 03 + 09), not in any single RM's My Queue, because they don't have a single owner.

**Reasoning** is multi-cited: each pattern card lists the customers and the verbatim quotes that ground the pattern.

## Guardrails
- **Minimum support threshold:** a pattern requires ≥3 customers (or ≥3 talent for talent-side patterns) to qualify. Two customers is a coincidence; three is a pattern.
- **No demographic patterns.** The skill does not surface patterns by ethnicity, gender, age, or any protected class. Hard rule. The Phase 4 implementation has an explicit denylist.
- **No customer-individuation in cross-account outputs delivered outside Pulse.** If a pattern card is exported (e.g., to a Sales lead's email), customer names are pseudonymized unless the recipient is an Admin or the customer's own RM.
- **Frequency cap:** a single theme should not generate a pattern card more than once per month even if the support continues to grow. Updates reflected in the existing card's "evidence accumulating" indicator.

## Output / Proposed action shape
```yaml
action_type: pattern-surface
delivery_channel: action_queue_overall_view + optional_email_to_sales_lead
body:
  pattern_theme: <short label>
  pattern_description: <one paragraph>
  support_cardinality: {customers: N, talent: M}
  verbatim_evidence:
    - {customer: <name>, quote: <text>, source: <episode_ref>}
    - ... (≥3)
  proposed_portfolio_response:
    audience: <sales | talent-dev | cs-leadership | leadership>
    recommended_motion: <short description>
modifiable_fields: [body.proposed_portfolio_response.recommended_motion]
```

## Tier variants
None (patterns span tiers by definition).

Approval mode: human-required (portfolio motions are high-leverage); approver is typically Admin / VP of Client Success.

## Outcome detection
- Approved → emailed → reply / motion booked within 14 days → `outcome-recorded` type `pattern-acted-on`.
- No movement after 30 days → `outcome-missing`.

## EDGE Coverage
- §13.4 example "Which talent across ALL accounts have raised pay concerns this quarter?" — this skill's class of query.
- §13.4 example "Which Helix talent flagged the AI tool as impacting their work value?" — cross-customer slice when multiple customers' talent flag the same AI tool.
- §13.6 #1 "Action Queue + agentic action proposals (Pulse exceeds EDGE doc with propose/approve/execute)" — cross-account pattern surfacing is *the* agentic upgrade.

## Open questions
- **Q77** — Cross-account retriever shape (Q for Design 01 to address). Specifically: how is "same theme" determined — exact topic-node match? Embedding similarity? PM proposes: exact topic-node match in Phase 1 with embedding similarity as a v1.5+ enhancement.
- **Q78** — Pseudonymization mechanism. Phase 1 = simple replace (Customer-A, Customer-B). v1.5+ could be more sophisticated. Filed.
- **Q79** — Pattern surfacing cadence. Weekly Sunday is the default; some patterns may need faster cycles. PM proposes: weekly default, with a "high-urgency cross-account signal" intra-week trigger reserved for severe themes (e.g., 5 customers raising the same red flag in 48h).

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `client_termination_pattern_v1` | **Primary consumer.** Cross-temporal client-side risk pattern locked Session 11 (Decision 36). Skill 10 aggregates across customers to find cohort patterns (e.g., dental-vertical termination rate elevated across 3 customers). |
| `churn_signal_competitor_mention_v1` | Cross-account aggregator. If multiple customers mention the same competitor in same window → pattern card. |
| `expansion_signal_verbal_capacity_mention_v1` | Cross-account aggregator. If multiple customers in same vertical mention same expansion theme → pattern card for Sales. |
| `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1` | Cross-account aggregators. If a cohort of placed talent in same role-family raises the same concern → pattern card for Talent Dev. |
| `escalation_signal_case_pattern_v1` | Per-customer pattern that Skill 10 promotes to cross-customer when ≥3 customers share the pattern. |

Skill 10 is the **aggregator**: it does not detect signals itself; it composes pattern cards from cross-customer occurrence of signals defined elsewhere. Its golden-trace tests verify:
- The cross-account retriever (Q77) correctly identifies same-theme signals across customers.
- The minimum-support threshold (≥3 customers) is honored.
- The demographic-denylist guardrail (no patterns by protected class) is enforced.
- The `client_termination_pattern_v1` aggregation produces the cross-temporal cohort view described in the signal definition's Example 2.

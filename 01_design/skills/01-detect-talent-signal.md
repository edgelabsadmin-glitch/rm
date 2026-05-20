# Skill 01 — detect-talent-signal

**Lifecycle stage:** operations
**Phase:** 1
**Tier-aware:** no (signals are tier-agnostic; downstream skills apply tier rules)

## Trigger
**Episode-driven.** Fires on every newly-ingested Episode where `content_type ∈ {text, json}` and the Episode has at least one candidate Customer or Talent entity. In practice: every Chorus call summary, every `RM_Outreach__c` update, every `Associates__c` stage change, every risk-tagged `Case`.

## Inputs
- Retrievers required: `get_customer_context()` and/or `get_talent_context()` for the candidate entities on the Episode (Design 01).
- External calls: none beyond the Episode payload itself.
- Per-Profile Markdown read: none (this skill produces signal; profiles aggregate it).
- Policy inputs: none — this skill's output is a *signal*, not an action, so it doesn't hit the approval gate.

## Behavior
Extracts the structured signal vocabulary from the Episode and writes it back as bi-temporal edges on the memory graph (per Design 01 `mentions` and `raised_concern_about` edge types). Lifts the prompt and signal schema from `rm-intelligence-agent/src/extract_signals.py`, ported to Claude (per Decision 13).

Signal taxonomy (Phase 1, evolving):
- **Churn signals:** competitor mentions, pricing pressure, vendor-consolidation, downsizing, escalation tone, replacement asks
- **Expansion signals:** new role asks, scaling talk, positive feedback, referral readiness
- **Talent welfare:** burnout, growth concerns, AI-displacement concerns, pay concerns, work-quality stress
- **Operational:** schedule changes, payment issues, ADP-related, audit failures
- **Sentiment vector:** multi-axis (warmth, frustration, urgency, momentum) per Decision 4.4 pushback — *not* a single 1–10. Composite 1–10 derived for UI surfacing only (§13.2 row).
- **Verbatim quotes preserved** for citation by downstream skills (`<quote>` inline tag voice; per `rm-intelligence-agent` pattern).

**Reasoning structure (Design 04 §"Reasoning capture"):**
```
[skill: detect-talent-signal]
[context: Episode=<id>, source=<chorus|sfdc|...>]

Signals consulted:
  - Episode subject + body (or structured payload)
  - <num>2</num> candidate entities pre-tagged by adapter

Reasoning:
  Extract churn/expansion/welfare signals from this episode. Preserve
  verbatim client quotes. Skip if episode is purely scheduling or
  candidate-interview with no client commentary (matches Pulse v0
  guardrail).

Proposed action: none (this skill emits signal edges, not actions)
```

## Guardrails
- **Do not extract signals from EDGE-side speakers** unless they are reporting a client quote. Internal RM speculation is not a signal. The skill MUST attribute signals to the **client** speaker, not to EDGE employees.
- **Do not invent quotes.** If a verbatim cannot be lifted from the Episode, emit a paraphrased signal but leave the quote field null.
- **Do not extract from scheduling-only episodes.** Episodes whose entire content is "Meeting moved to 3pm" emit zero signals.
- **Do not write to Salesforce.** Signals are graph-internal; SFDC writes go through Action Queue (§6 rule 6).
- **Respect the white-label rule.** Reasoning text and signal labels never mention underlying tech.

## Output / Proposed action shape
This skill does **not** propose actions. It emits:
- `mentions` edges from Episode → Topic/Customer/Talent nodes
- `raised_concern_about` edges from Customer/Talent → Topic
- Multi-axis sentiment vector as a property on the relevant edge or on a `was_in_sentiment_state` bi-temporal edge attached to the Customer/Talent node
- Verbatim quote strings carried on edges where applicable

Downstream skills (`03-renewal-watcher`, `05-escalation-router`, etc.) reason over these emitted signals.

## Tier variants
None (signals are tier-agnostic).

## Outcome detection
Not applicable — this skill emits structured graph data, not actions. Quality is measured indirectly: do downstream skills produce useful proposals from this skill's output? Tracked via the policy module's rejection-rate dampening (Design 04 rule 4).

## EDGE Coverage
- §13.2 row "Sentiment score (1–10) extraction" — composite from multi-axis vector
- §13.2 row "Theme tags (burnout, growth, AI displacement, etc.)" — taxonomy above
- §13.2 row "2-sentence summary" — emitted as a property on the Episode for downstream consumption
- §13.4 example "How many people at Mendota feel burned out?" — burnout signals enable this filter
- §13.4 example "Which Helix talent flagged the AI tool as impacting their work value?" — AI-displacement signals enable this
- §13.4 example "Which talent across ALL accounts have raised pay concerns this quarter?" — pay-concern signals enable cross-account query

## Open questions
- **Q50** — Signal taxonomy completeness. The Phase 1 list is lifted from rm-intelligence-agent + EDGE doc examples. After Phase 1 demo, run a sample of 100 episodes through and surface any signal types missed.
- **Q51** — Multi-axis sentiment vector dimensions. PM proposed warmth / frustration / urgency / momentum. User to confirm or revise.
- **Q52** — Topic node creation policy (Q29 from Design 01). LLM-extracted with dedup pass — when does dedup run?

## Owned signals (Phase 3 cross-reference)

Skill 01 is the **upstream extractor** — it does not "fire" signals in the action-proposal sense; it produces the structured tags (signal labels + sentiment vectors + verbatim quotes) that the signal definitions in `02_planning/signals/` consume to make fire/don't-fire determinations.

Skill 01 produces the underlying tags consumed by the following signal definitions:

| Signal ID | Skill 01 produces | Fired by |
|---|---|---|
| `churn_signal_sentiment_decline_v1` | per-episode `sentiment_vector` (4 axes) | rule on aggregated trajectory |
| `churn_signal_competitor_mention_v1` | `competitor_mentions` with `tone` | Skill 01 LLM-extraction + downstream rule |
| `expansion_signal_verbal_capacity_mention_v1` | `expansion_mentions` with `directness` | Skill 01 LLM-extraction + downstream rule |
| `talent_burnout_signal_v1` | `talent_welfare_signals` with `type=burnout` | Skill 01 LLM-extraction + downstream rule |
| `talent_growth_concern_v1` | `talent_welfare_signals` with `type=growth_concern` | Skill 01 LLM-extraction + downstream rule |
| `talent_pay_concern_v1` | `talent_welfare_signals` with `type=pay_concern` | Skill 01 LLM-extraction + downstream rule |
| (positive-quote tagging used by) `recognition_signal_advocacy_candidate_v1` | `signal=positive_quote` edges | downstream aggregation |

**Skill 01's golden-trace tests (per §6 rule 10) verify the per-tag extraction quality.** Each signal definition above carries its own additional golden-trace tests verifying that the *fires/doesn't-fire* logic is correct given Skill 01's outputs.

No black-box detection (§6 rule 8): every tag Skill 01 emits maps to a Signal Definition Library entry with plain-English semantics.

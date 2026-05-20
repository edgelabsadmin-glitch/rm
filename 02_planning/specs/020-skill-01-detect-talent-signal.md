# Spec 020 — Skill 01 — detect-talent-signal

**Maps to:** §14 Skills (Skill 01); `01_design/skills/01-detect-talent-signal.md`; §13.2 rows (sentiment / theme tags / 2-sentence summary); §13.4 example rows.
**Depends on:** specs 005, 006, 008, 011 (this skill runs on every Episode ingestion).
**Effort:** 1.0 day.

## Description

The upstream signal extractor. Runs episode-driven on every new Episode where `content_type ∈ {text, json}` and the Episode has ≥1 candidate Customer/Talent entity. Calls Claude Haiku (per spec 003 model pin) with the lifted-and-ported-from-rm-intelligence-agent prompt; produces structured tags (`competitor_mentions`, `expansion_mentions`, `talent_welfare_signals`, `sentiment_vector`, `positive_quotes`, etc.) that are written back as bi-temporal edges on the graph and consumed by all downstream signal definitions.

This skill is the **bridge between raw Episodes and the Signal Definition Library** — every LLM-extracted tag becomes the input to one or more signal definitions' rule evaluators.

## Inputs

- Each newly-ingested Episode (spec 011's pipeline fires Skill 01 as a post-ingest hook).
- Claude Haiku via spec 003's config.
- Per `01_design/skills/01-detect-talent-signal.md` §"Owned signals" — Skill 01 produces tags consumed by 7 signal definitions.

## Outputs

- `03_build/pulse/skills/skill_01_detect_talent_signal.py`.
- Prompt at `03_build/pulse/skills/prompts/skill_01_extraction.txt` — versioned.
- Per Episode: `mentions`, `raised_concern_about`, `was_in_sentiment_state` edges in Graphiti + verbatim-quote strings on edges.
- Reasoning capture event per execution.

## Definition of Done

- [ ] Runs on every Episode ingestion within 5s P95 (Haiku call latency target).
- [ ] Multi-axis sentiment vector (warmth / frustration / urgency / momentum per Q51) per Episode.
- [ ] Verbatim quotes preserved (no paraphrase) — verified by golden-trace fixture against rm-intelligence-agent's existing output shape.
- [ ] Skip-rule honored: scheduling-only / candidate-interview-only Episodes emit zero signals.
- [ ] Tag attribution to *client* speaker, not EDGE-side (per Skill 01 guardrail).
- [ ] No SFDC writes from this skill.
- [ ] Langfuse traces show per-Episode reasoning.

## Tests

- **Unit:** prompt-string assembly + LLM-response parsing.
- **Integration:** ingest one Chorus Episode → Skill 01 fires → expected edges and tags exist in Graphiti.
- **Golden-trace:** the rm-intelligence-agent fixture (one Acrisure EBR transcript) produces the same tag set when run through Skill 01 (allowing for prompt-port variance).

## Signal definitions involved

Per `01_design/skills/01-detect-talent-signal.md` §"Owned signals" table — Skill 01 produces underlying tags for `churn_signal_sentiment_decline_v1`, `churn_signal_competitor_mention_v1`, `expansion_signal_verbal_capacity_mention_v1`, `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1`, and `recognition_signal_advocacy_candidate_v1`'s positive_quote tagging.

## Open questions

Q50 (taxonomy completeness), Q51 (sentiment axes), Q52 (Topic dedup), Q132 (competitor watch-list), Q133 (past-tense detection robustness) — all in `99_open_questions.md`.

## What this is NOT

- Not a signal evaluator (those are the Signal Definition Library at spec 017).
- Not where signals fire as action proposals (that's downstream skills 03/04/05/06/etc.).
- Not the place to tune skill prompts at runtime — prompts are versioned files committed in PRs.

# Spec 003 — Model-ID pinning module + `.env` loading discipline

**Maps to:** §14 Phase-4-Day-1 tasks; Q115, Q116 (both filed during Spike 3 live run).
**Depends on:** spec 001.
**Effort:** 0.25 day.

## Description

Two related Phase-4 Day-1 discipline items rolled into one spec:

1. **Model-ID pinning module** (Q115). Graphiti 0.29 defaults to `claude-haiku-4-5-latest`, which the Anthropic API does not resolve (404). Create `pulse/core/llm/config.py` exporting dated model IDs as constants + a `make_llm_config()` factory that returns `LLMConfig` instances for Graphiti's clients. Every Pulse code path that constructs an LLM client imports from here — no model-ID string literals scattered across the codebase.
2. **`.env` loading discipline** (Q116). `load_dotenv()`'s `override=False` default lets empty parent-shell env vars (like the empty `ANTHROPIC_API_KEY` found in Spike 3) win over the `.env` file. Standardize on `load_dotenv(override=True)` in every startup path; add a lint rule that flags `load_dotenv()` calls without `override=`.

## Inputs

- The Anthropic model lineup confirmed via Spike 3: `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`.
- The OpenAI embedder per Spike 3 §C: `text-embedding-3-small`.
- `python-dotenv` installed.

## Outputs

- `03_build/pulse/core/llm/config.py` exporting:
  - `ANTHROPIC_HAIKU = "claude-haiku-4-5-20251001"`
  - `ANTHROPIC_SONNET = "claude-sonnet-4-6"`
  - `ANTHROPIC_OPUS = "claude-opus-4-7"`
  - `OPENAI_EMBEDDER = "text-embedding-3-small"`
  - `def make_llm_config(model: str, max_tokens: int = 4000) -> LLMConfig` factory.
- A ruff rule (or pre-commit grep check) that fails the build if `load_dotenv()` is called without `override=` explicitly.
- A short README section "Environment Loading" explaining the discipline.

## Definition of Done

- [ ] `pulse/core/llm/config.py` exists with the four constants + factory.
- [ ] No `claude-*-latest` strings exist anywhere in `03_build/` (CI grep check).
- [ ] All `load_dotenv()` calls in `03_build/` pass `override=True` (CI grep check).
- [ ] Unit test asserts `make_llm_config("haiku")` returns an `LLMConfig` whose `.model == ANTHROPIC_HAIKU`.
- [ ] Spec 002's PulseKuzuDriver + spec 005's memory layer construct `AnthropicClient(config=make_llm_config("haiku"))` — no inline model strings.

## Tests

- **Unit:** `test_make_llm_config_returns_pinned_model_id`; `test_no_latest_aliases_in_codebase` (grep-based meta-test).
- **Integration:** the Spike 3 harness re-execution after this spec lands — verifies the live LLM call uses the pinned model and succeeds.

## Signal definitions involved

None.

## Open questions

None — Q115 + Q116 are filings of this work.

## What this is NOT

- Not the LLM client wrapper itself (that's wired in spec 008 / 017 / per-skill specs).
- Not where prompt strings live — that's per-skill.
- Not where embedding model is *invoked* — only where the model ID is *declared*.

# Bedrock Migration + Opus-Primary Fallback — Design

**Date:** 2026-07-01
**Status:** approved (design)

## Goal

Route **all Claude/LLM calls through Amazon Bedrock** (IAM auth, no standalone
Anthropic API key at runtime) and flip model tiering to **Opus-primary → Sonnet-fallback
for every feature**, with an explicit fallback on every LLM call site. **Keep OpenAI**
for Graphiti embeddings (unchanged). Do **not** re-run the analysis backfill.

## Verified facts (live-probed 2026-07-01)

- Bedrock on-demand requires **inference profiles** (base model IDs are not invokable).
  Confirmed working via `converse` on this account (us-east-1):
  - Opus → `us.anthropic.claude-opus-4-7`
  - Sonnet → `us.anthropic.claude-sonnet-4-6`
  - Haiku → `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- The `anthropic` SDK (>=0.49, installed) ships `AnthropicBedrock`, same Messages API
  (incl. `tools` + `tool_choice`), auth via the boto3 default credential chain.
- The Graphiti/Kuzu graph is **ephemeral** in prod (local container disk, no volume) →
  no vector store to migrate; embeddings stay on OpenAI, untouched.
- App Runner service `pulse-api` has **no instance role** today → one must be created
  for `bedrock:InvokeModel`.

## Architecture

### 1. Provider factory — `core/llm/provider.py` (new)
One function returns an Anthropic-compatible client:
- `LLM_PROVIDER=bedrock` (new default) → `AnthropicBedrock(aws_region=AWS_REGION)`
- else → `Anthropic(api_key=ANTHROPIC_API_KEY)` (rollback switch; also used in unit tests)

All call sites obtain their client from here instead of instantiating `anthropic.Anthropic`
directly. Single switch, single place to change.

### 2. Model tiering — `core/llm/config.py`
- `LLM_PRIMARY = OPUS`, `LLM_FALLBACK = SONNET`.
- Bedrock model IDs (inference profiles) added; a `MODEL_ID(provider, tier)` resolver
  maps tier → the direct Anthropic model ID or the Bedrock profile ID depending on
  `LLM_PROVIDER`.
- Graphiti extraction stays **Haiku-primary** with a **Sonnet fallback**.

### 3. Fallback wrapper — `core/llm/fallback.py` (new)
`call_with_fallback(fn, *, primary, fallback, log_label)`: calls `fn(model_id)` with the
primary model; on any exception (or an explicit `LLMFallback` raised by the caller for a
quality miss) retries once with the fallback model; re-raises if both fail. Returns the
first successful result. This is the "fallback for everything" mechanism for the
plain-text call sites.

The **analysis agent** already has a *quality*-based fallback (validation-gate driven):
today Sonnet→Opus; flip to **Opus→Sonnet** (change the default model in `agent.py` +
`analyst._MODELS` ordering). No wrapper needed there — the orchestration stays but its
order inverts.

### 4. Call sites (6) migrated to factory + fallback
`core/analysis/analyst.py`, `core/inbox/reply.py`, `core/llm/rm_style.py`,
`api/client_chat.py`, `api/support.py`, `core/llm/client.py`.
- Non-streaming calls wrap in `call_with_fallback` (Opus→Sonnet).
- Streaming chat (`client_chat`, `support` if streamed) falls back on connection/initial
  error only (no mid-stream retry) — documented limitation.

### 5. Graphiti → Bedrock
`core/memory/graph.py`: the `AnthropicClient` LLM is built from the provider/region so it
runs on Bedrock (Haiku profile). **Embedder unchanged** (`OpenAIEmbedder`).
`core/llm/config.py` `make_llm_config` gains a Bedrock-aware path (Graphiti's
`AnthropicClient` supports a Bedrock base or we pass the profile ID + rely on the SDK).

### 6. Auth / infra
- Create IAM role **`pulse-apprunner-bedrock`**: trust `tasks.apprunner.amazonaws.com`,
  policy `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream` on the three
  inference-profile ARNs (+ the underlying foundation-model ARNs, which on-demand
  profile invocation also requires).
- `aws apprunner update-service --instance-configuration InstanceRoleArn=…` → sets the
  role (triggers a deployment).
- Runtime env: add `AWS_REGION=us-east-1`, `LLM_PROVIDER=bedrock`. `ANTHROPIC_API_KEY`
  may remain as a rollback path but is not used when `LLM_PROVIDER=bedrock`.
- Local dev / container: boto3 uses `~/.aws` creds.

## Error handling
- Bedrock throttling/5xx on primary → wrapper falls back to Sonnet; if both throttle,
  the exception propagates (caller already handles LLM errors today).
- Analysis agent: Opus gate-fail → Sonnet; both fail → `needs_review` (unchanged
  semantics, inverted order).

## Testing
- `tests/test_llm_fallback.py`: wrapper calls primary first; on primary raising, calls
  fallback; returns fallback result; both-raise re-raises. (mocked `fn`.)
- `tests/test_analysis_agent.py`: existing fallback tests updated for Opus-primary order.
- Provider factory unit test: returns Bedrock client when `LLM_PROVIDER=bedrock`, direct
  client otherwise (no network).
- **Live smoke** (container + `~/.aws`): analyze 1 account end-to-end through Bedrock
  Opus; assert a matrix row is produced. Run before deploy.

## Rollout
1. Branch, implement, unit tests + ruff + pyright green, CI green.
2. Create IAM role + policy (idempotent script using existing AWS creds).
3. `update-service` to attach instance role + set `LLM_PROVIDER`/`AWS_REGION` env.
4. Deploy (merge to main). Health-check: `/health` + one live analysis via Bedrock in prod.
5. Rollback: set `LLM_PROVIDER=` (unset) → falls back to direct Anthropic key.

## Cost
Opus-primary ≈ 5× Sonnet per token on the interactive + analysis paths. Accepted.
No immediate re-backfill; the incremental loop refreshes matrices on Opus as data changes.

## Out of scope
OpenAI embeddings (kept), re-embedding, re-backfill, changing signal logic.

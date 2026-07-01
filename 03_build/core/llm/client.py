"""
SPEC-018 — async Anthropic text-completion client (ADR-001 timeouts, ADR-003
Langfuse @observe). Distinct from Graphiti's AnthropicClient (which does
structured entity extraction during ingestion); this is the skills' synthesis
path (Sonnet/Opus prose + JSON).

Models come from core.llm.config (pinned IDs, Q115). Each call is bounded by the
per-model timeout (timeout_for) so a hung LLM call can't exceed the ADR-001
request budget.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from langfuse.decorators import observe

from core.llm.config import _MODEL_DEFAULTS, timeout_for

_client: Any = None


def _get_client() -> Any:
    """Lazily build the async Anthropic client for the active provider (Bedrock or direct)."""
    global _client
    if _client is None:
        from core.llm.provider import async_anthropic_client

        _client = async_anthropic_client()
    return _client


@observe(name="llm_complete")
async def complete(
    model: str,
    prompt: str,
    *,
    system: str = "",
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Return the text completion for a single user prompt, bounded by the
    per-model timeout (ADR-001).

    `temperature` defaults to None and is omitted from the request: newer Opus
    models reject the parameter ("temperature is deprecated for this model"), and
    omitting it is accepted by every pinned model. Pass an explicit value only
    for a model known to accept it.
    """
    budget = _MODEL_DEFAULTS.get(model, {"max_tokens": 4096})["max_tokens"]

    async def _once(model_id: str) -> str:
        kwargs: dict = {
            "model": model_id,
            "max_tokens": max_tokens or budget,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        resp = await asyncio.wait_for(
            _get_client().messages.create(**kwargs), timeout=timeout_for(model)
        )
        return "".join(getattr(b, "text", "") for b in resp.content)

    # Caller's model is primary; fall back to Sonnet on failure. Model IDs are
    # resolved for the active provider inside the wrapper.
    from core.llm.fallback import acall_with_fallback

    return await acall_with_fallback(_once, label="llm_complete", primary=model)


def parse_json(text: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating ```json fences and
    surrounding prose."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(0))

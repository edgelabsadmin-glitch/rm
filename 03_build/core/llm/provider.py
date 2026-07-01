"""
Provider factory — the single place that builds the Anthropic client.

  LLM_PROVIDER=bedrock  → AnthropicBedrock (IAM auth via the boto3 credential chain)
  otherwise (default)   → Anthropic (ANTHROPIC_API_KEY)

Model IDs are resolved separately (core.llm.config.resolve_model), so callers keep
using the pinned ANTHROPIC_* constants and this + the resolver handle the provider
difference. Sync and async variants mirror the two Anthropic SDK client families.
"""

from __future__ import annotations

import os
from typing import Any

from core.llm.config import aws_region, llm_provider, load_env


def anthropic_client() -> Any:
    """Sync Anthropic-compatible client for the active provider."""
    load_env()
    import anthropic

    if llm_provider() == "bedrock":
        return anthropic.AnthropicBedrock(aws_region=aws_region())  # type: ignore[attr-defined]
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def async_anthropic_client() -> Any:
    """Async Anthropic-compatible client for the active provider."""
    load_env()
    import anthropic

    if llm_provider() == "bedrock":
        return anthropic.AsyncAnthropicBedrock(aws_region=aws_region())  # type: ignore[attr-defined]
    return anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

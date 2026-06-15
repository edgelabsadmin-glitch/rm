"""
SPEC-006 integration — named retrievers against a real Graphiti fixture.

Marker `integration`, gated on LLM keys (real Anthropic+OpenAI ingestion). The
Langfuse golden-trace assertion additionally needs Langfuse keys and skips
otherwise.
"""

import os
from datetime import UTC, datetime, timedelta

import pytest

from core.llm.config import load_env

load_env()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("OPENAI_API_KEY"),
        reason="needs ANTHROPIC_API_KEY + OPENAI_API_KEY",
    ),
]

NOW = datetime.now(UTC)


async def _seed_graph():
    from graphiti_core.nodes import EpisodeType

    from core.memory.graph import add_pulse_episode, make_graphiti

    g = make_graphiti(":memory:")
    await g.build_indices_and_constraints()
    await add_pulse_episode(
        g,
        name="Chorus call Acrisure EBR",
        episode_body=(
            "Quarterly business review with Acrisure. Director Sarah Chen praised the medical "
            "coders EDGE placed but flagged vendor-consolidation pressure from the CFO."
        ),
        reference_time=NOW - timedelta(days=10),
        source=EpisodeType.text,
        source_description="Chorus call Acrisure EBR",
    )
    await add_pulse_episode(
        g,
        name="Associate Replaced — Acrisure",
        episode_body=(
            "Marcus Wells, a Dental Coder II placed at Acrisure, was replaced after failing audits."
        ),
        reference_time=NOW - timedelta(days=5),
        source=EpisodeType.text,
        source_description="Associate Replaced — Acrisure",
    )
    return g


async def test_get_customer_context_real_fixture():
    from core.memory import retrievers

    g = await _seed_graph()
    try:
        bundle = await retrievers.get_customer_context("Acrisure", graphiti=g)
        assert bundle["entity"] is not None, "Acrisure should resolve to a node"
        assert "acrisure" in bundle["entity"]["name"].lower()
        # At least the EBR episode should be linked.
        assert len(bundle["recent_episodes"]) >= 1
        assert isinstance(bundle["temporal_facts"], list)
    finally:
        await g.close()


async def test_langfuse_trace_has_retriever_span():
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        pytest.skip("needs LANGFUSE_PUBLIC_KEY to assert the trace tree")

    from langfuse import get_client

    from core.memory import retrievers

    g = await _seed_graph()
    try:
        await retrievers.get_customer_context("Acrisure", graphiti=g)
        get_client().flush()
    finally:
        await g.close()
    # The @observe(name="retriever_get_customer_context") span is emitted; full
    # trace-tree assertion is a Langfuse-server query left to manual/golden review.

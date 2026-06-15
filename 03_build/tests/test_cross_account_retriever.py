"""
SPEC-007 unit tests — cross-account retriever + protected-class denylist.

Mocked Graphiti (no LLM/DB). The real-fixture cross-customer match lives in
tests/test_retrievers_integration.py-style integration is exercised here behind
the `integration` marker.
"""

import os
from datetime import UTC, datetime

import pytest

from core.llm.config import load_env
from core.memory import denylist, retrievers

# Load .env at import so the integration test's skipif sees the LLM keys.
load_env()

NOW = datetime(2026, 5, 20, tzinfo=UTC)


class _Driver:
    def __init__(self, *, topic_exists=True, match_rows=None):
        self.topic_exists = topic_exists
        self.match_rows = match_rows or []
        self.last_kwargs: dict = {}

    async def execute_query(self, q: str, **kw):
        self.last_kwargs = kw
        if "LIMIT 1" in q and "n.name" in q:  # _resolve_entity (topic)
            return (
                ([{"uuid": "topic-1", "name": "vendor consolidation"}], None, None)
                if self.topic_exists
                else ([], None, None)
            )
        if "MENTIONS" in q and "list_contains" in q:  # cross-account query
            return (self.match_rows, None, None)
        return ([], None, None)


class FakeGraphiti:
    def __init__(self, **kw):
        self.driver = _Driver(**kw)

    async def search(self, *a, **k):
        return []


def _match_row(cid, name, epid):
    return {
        "customer_id": cid,
        "customer_name": name,
        "episode_id": epid,
        "quote": "CFO wants to cut vendor count 20%",
        "date": NOW,
    }


async def test_denylisted_theme_raises():
    g = FakeGraphiti()
    with pytest.raises(ValueError, match="protected-class"):
        await retrievers.find_pattern_across_customers("racial composition of teams", graphiti=g)


@pytest.mark.parametrize(
    "theme", ["vendor consolidation", "AI displacement", "burnout", "pay compression"]
)
def test_legitimate_themes_pass_denylist(theme):
    assert denylist.is_protected_theme(theme) is False


@pytest.mark.parametrize(
    "theme", ["age of workforce", "religious accommodation", "pregnancy leave", "disability rate"]
)
def test_protected_themes_caught(theme):
    assert denylist.is_protected_theme(theme) is True


async def test_exact_topic_match_returns_all_customers():
    rows = [
        _match_row("u-a", "Acrisure", "ep-1"),
        _match_row("u-b", "Mendota Insurance", "ep-2"),
        _match_row("u-c", "DHR Health Clinics", "ep-3"),
    ]
    g = FakeGraphiti(match_rows=rows)
    matches = await retrievers.find_pattern_across_customers(
        "vendor consolidation", time_window_days=30, graphiti=g
    )
    assert len(matches) == 3
    assert {m.customer_name for m in matches} == {
        "Acrisure",
        "Mendota Insurance",
        "DHR Health Clinics",
    }
    assert all(isinstance(m, retrievers.CrossAccountMatch) for m in matches)


async def test_min_support_is_not_a_filter():
    rows = [_match_row("u-a", "Acrisure", "ep-1")]
    g = FakeGraphiti(match_rows=rows)
    # Only 1 match but min_support=3 — retriever still returns it; Skill 10 decides.
    matches = await retrievers.find_pattern_across_customers(
        "vendor consolidation", min_support=3, graphiti=g
    )
    assert len(matches) == 1


async def test_unresolved_topic_returns_empty():
    g = FakeGraphiti(topic_exists=False)
    matches = await retrievers.find_pattern_across_customers("nonexistent theme", graphiti=g)
    assert matches == []


async def test_time_window_passed_as_cutoff():
    g = FakeGraphiti(match_rows=[])
    await retrievers.find_pattern_across_customers(
        "vendor consolidation", time_window_days=7, graphiti=g
    )
    cutoff = g.driver.last_kwargs.get("cutoff")
    assert cutoff is not None
    # ~7 days back from now.
    delta_days = (datetime.now(UTC) - cutoff).days
    assert 6 <= delta_days <= 7


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("OPENAI_API_KEY"),
    reason="needs ANTHROPIC_API_KEY + OPENAI_API_KEY",
)
async def test_cross_account_real_fixture_executes():
    """Real Kuzu: validates the list_contains + double-MENTIONS Cypher runs and
    the call returns well-formed matches (exact counts are covered by unit
    tests; LLM labelling is non-deterministic)."""
    from datetime import timedelta

    from graphiti_core.nodes import EpisodeType

    from core.llm.config import load_env
    from core.memory.graph import add_pulse_episode, make_graphiti

    load_env()
    g = make_graphiti(":memory:")
    await g.build_indices_and_constraints()
    try:
        for cust in ("Acrisure", "Mendota Insurance"):
            await add_pulse_episode(
                g,
                name=f"Chorus call {cust}",
                episode_body=(
                    f"On the call, {cust}'s operations director raised vendor consolidation: "
                    "the CFO wants to cut vendor count by 20% this fiscal year."
                ),
                reference_time=datetime.now(UTC) - timedelta(days=3),
                source=EpisodeType.text,
                source_description=f"Chorus call {cust}",
            )
        matches = await retrievers.find_pattern_across_customers(
            "vendor consolidation", time_window_days=30, graphiti=g
        )
        assert isinstance(matches, list)
        assert all(isinstance(m, retrievers.CrossAccountMatch) for m in matches)
    finally:
        await g.close()

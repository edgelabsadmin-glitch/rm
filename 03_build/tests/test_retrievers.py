"""
SPEC-006 unit tests — named retrievers over a mocked Graphiti.

No LLM/DB: a FakeGraphiti returns canned search edges and Cypher rows so we can
assert each retriever calls the right search (centred on the resolved node) and
assembles the right ContextBundle, including bi-temporal `as_of` filtering and
Talent-only skills. The real-fixture + Langfuse-trace tests live in
tests/test_retrievers_integration.py.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from core.memory import retrievers

NOW = datetime(2026, 5, 20, tzinfo=UTC)
T_OLD = NOW - timedelta(days=30)
T_INVALIDATED = NOW - timedelta(days=5)  # an edge that ended 5 days ago


class _Driver:
    def __init__(self, name: str):
        self._name = name
        self.searched_center: str | None = None

    async def execute_query(self, q: str, **kw):
        if "LIMIT 1" in q and "n.name" in q:  # _resolve_entity
            ident = kw["id"]
            if ident.lower() in self._name.lower():
                return ([{"uuid": "u-1", "name": self._name}], None, None)
            return ([], None, None)
        if "(m:Entity)" in q and "edge_type" in q:  # _relationships
            return (
                [
                    {
                        "edge_type": "placed_at",
                        "fact": "X placed at Acrisure",
                        "other": "Marcus Wells",
                        "other_uuid": "u-2",
                        "valid_at": T_OLD,
                        "invalid_at": None,
                    },
                    {
                        "edge_type": "raised_concern_about",
                        "fact": "ended concern",
                        "other": "Vendor consolidation",
                        "other_uuid": "u-9",
                        "valid_at": T_OLD,
                        "invalid_at": T_INVALIDATED,  # no longer in effect at NOW
                    },
                ],
                None,
                None,
            )
        if "MENTIONS" in q:  # _recent_episodes
            return (
                [
                    {
                        "uuid": "ep-1",
                        "name": "Acrisure EBR",
                        "content": "QBR text",
                        "valid_at": T_OLD,
                    }
                ],
                None,
                None,
            )
        if "has_skill" in q:  # _skills
            return (
                [{"skill": "medical-coder-ii", "valid_at": T_OLD, "invalid_at": None}],
                None,
                None,
            )
        return ([], None, None)


class FakeGraphiti:
    def __init__(self, name: str = "Acrisure"):
        self.driver = _Driver(name)
        self.searched_center: str | None = None

    async def search(self, query, center_node_uuid=None, group_ids=None, num_results=10):
        self.searched_center = center_node_uuid
        return [
            SimpleNamespace(
                name="placed_at", fact="X placed at Acrisure", valid_at=T_OLD, invalid_at=None
            ),
            SimpleNamespace(
                name="raised_concern_about",
                fact="ended concern",
                valid_at=T_OLD,
                invalid_at=T_INVALIDATED,
            ),
        ]


async def test_customer_context_assembles_bundle_and_centres_search():
    g = FakeGraphiti()
    bundle = await retrievers.get_customer_context("Acrisure", as_of=NOW, graphiti=g)

    assert bundle["entity"] == {"uuid": "u-1", "name": "Acrisure"}
    assert g.searched_center == "u-1"  # hybrid search centred on the resolved node
    # as_of=NOW filters out the edge invalidated 5 days ago, keeps the live one.
    assert [f["edge_type"] for f in bundle["temporal_facts"]] == ["placed_at"]
    assert [r["edge_type"] for r in bundle["relationships"]] == ["placed_at"]
    assert len(bundle["recent_episodes"]) == 1
    assert bundle["skills"] == []  # customers have no skill bindings


async def test_as_of_changes_results_on_bitemporal_edge():
    g = FakeGraphiti()
    # Before the edge was invalidated, BOTH facts are in effect.
    past = T_INVALIDATED - timedelta(days=1)
    bundle_past = await retrievers.get_customer_context("Acrisure", as_of=past, graphiti=g)
    bundle_now = await retrievers.get_customer_context("Acrisure", as_of=NOW, graphiti=g)

    assert len(bundle_past["temporal_facts"]) == 2
    assert len(bundle_now["temporal_facts"]) == 1
    assert len(bundle_past["relationships"]) == 2
    assert len(bundle_now["relationships"]) == 1


async def test_talent_context_includes_skills():
    g = FakeGraphiti(name="Marcus Wells")
    bundle = await retrievers.get_talent_context("Marcus", as_of=NOW, graphiti=g)
    assert [s["skill"] for s in bundle["skills"]] == ["medical-coder-ii"]


async def test_rm_context_has_no_skills():
    g = FakeGraphiti(name="Jordan M.")
    bundle = await retrievers.get_rm_context("Jordan", as_of=NOW, graphiti=g)
    assert bundle["skills"] == []
    assert bundle["entity"] == {"uuid": "u-1", "name": "Jordan M."}


async def test_unresolved_entity_returns_empty_bundle():
    g = FakeGraphiti(name="Acrisure")
    bundle = await retrievers.get_customer_context("Nonexistent Corp", as_of=NOW, graphiti=g)
    assert bundle["entity"] is None
    assert bundle["temporal_facts"] == []
    assert bundle["relationships"] == []
    assert bundle["recent_episodes"] == []


@pytest.mark.parametrize(
    "valid_at,invalid_at,as_of,expected",
    [
        (T_OLD, None, NOW, True),  # open-ended, in effect
        (NOW + timedelta(days=1), None, NOW, False),  # not yet valid
        (T_OLD, T_INVALIDATED, NOW, False),  # already invalidated
        (T_OLD, NOW + timedelta(days=1), NOW, True),  # invalidated in the future
    ],
)
def test_valid_as_of_predicate(valid_at, invalid_at, as_of, expected):
    assert retrievers._valid_as_of(valid_at, invalid_at, as_of) is expected

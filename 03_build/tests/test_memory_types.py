"""
SPEC-005 unit tests — Three-Graph typed schema (Design 01).

These are pure-Pydantic / registry-shape tests; they make no LLM calls and run
in the always-on `lint-and-test` CI job. End-to-end extraction (real Anthropic +
OpenAI) lives in tests/test_three_graph_integration.py and scripts/harness_three_graph.py.
"""

import pytest
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode
from pydantic import BaseModel

from core.memory import types as t

# Design 01 §"Entity types" / §"Edge types" lock the counts.
EXPECTED_ENTITY_NAMES = {
    "Customer",
    "Talent",
    "RM",
    "Contact",
    "Case",
    "Opportunity",
    "Skill",
    "AccountPlan",
}
EXPECTED_EDGE_NAMES = {
    "placed_at",
    "manages",
    "raised_concern_about",
    "replaced_by",
    "speaks_in_call",
    "has_skill",
    "reports_to",
    "mentions",
    "escalated_via",
    "has_plan",
}

# Attribute names owned by Graphiti — a custom type must never redeclare these.
_RESERVED = set(EntityNode.model_fields) | set(EntityEdge.model_fields)


def test_eight_entity_types_locked():
    assert set(t.ENTITY_TYPES) == EXPECTED_ENTITY_NAMES
    assert len(t.ENTITY_TYPES) == 8


def test_ten_edge_types_locked():
    assert set(t.EDGE_TYPES) == EXPECTED_EDGE_NAMES
    assert len(t.EDGE_TYPES) == 10


def test_registry_keys_match_model_names():
    # The dict key Graphiti uses must equal the model's class name so
    # EDGE_TYPE_MAP references stay consistent.
    for name, model in {**t.ENTITY_TYPES, **t.EDGE_TYPES}.items():
        assert model.__name__ == name


@pytest.mark.parametrize("model", list(t.ENTITY_TYPES.values()) + list(t.EDGE_TYPES.values()))
def test_models_are_basemodels_and_default_constructible(model: type[BaseModel]):
    # Every attribute is optional in Phase 1 — a bare instance must validate so
    # the LLM may omit attributes it cannot find in the source text.
    inst = model()
    assert isinstance(inst, BaseModel)


@pytest.mark.parametrize("model", list(t.ENTITY_TYPES.values()) + list(t.EDGE_TYPES.values()))
def test_no_reserved_attribute_names(model: type[BaseModel]):
    clashes = set(model.model_fields) & _RESERVED
    assert not clashes, f"{model.__name__} redeclares Graphiti-reserved field(s): {clashes}"


def test_customer_tier_accepts_documented_values_and_tolerates_unknown():
    # Q151: enum-shaped attributes are typed str|None (not strict Literal) so the
    # LLM's '<UNKNOWN>' sentinel does not trigger a costly extraction retry.
    assert t.Customer(tier="Enterprise").tier == "Enterprise"
    assert t.Customer(tier="<UNKNOWN>").tier == "<UNKNOWN>"  # tolerated, not rejected
    assert t.Customer().tier is None


def test_talent_stage_accepts_documented_values():
    talent = t.Talent(stage="Replaced", role="Dental Coder II")
    assert talent.stage == "Replaced"
    assert talent.role == "Dental Coder II"
    assert t.Talent().stage is None


def test_manages_side_distinguishes_book_halves():
    # Q27: the two-flavor manages distinction is carried as `side`.
    assert t.manages(side="customer").side == "customer"
    assert t.manages(side="talent").side == "talent"


def test_edge_type_map_references_only_known_types():
    entity_names = set(t.ENTITY_TYPES) | {"Entity"}  # "Entity" = Graphiti default node
    edge_names = set(t.EDGE_TYPES)
    for (src, dst), edges in t.EDGE_TYPE_MAP.items():
        assert src in entity_names, f"unknown source entity {src!r} in EDGE_TYPE_MAP"
        assert dst in entity_names, f"unknown target entity {dst!r} in EDGE_TYPE_MAP"
        for e in edges:
            assert e in edge_names, f"unknown edge {e!r} for ({src},{dst})"


def test_edge_type_map_has_no_duplicate_keys_and_covers_core_edges():
    # A duplicate literal key would silently drop a mapping; assert the core
    # demo-spine edges are reachable from their Design 01 endpoints.
    assert "placed_at" in t.EDGE_TYPE_MAP[("Talent", "Customer")]
    assert "raised_concern_about" in t.EDGE_TYPE_MAP[("Talent", "Customer")]
    assert t.EDGE_TYPE_MAP[("RM", "Customer")] == ["manages"]
    assert t.EDGE_TYPE_MAP[("RM", "Talent")] == ["manages"]
    assert "replaced_by" in t.EDGE_TYPE_MAP[("Talent", "Talent")]
    assert set(t.EDGE_TYPE_MAP[("Entity", "Entity")]) == EXPECTED_EDGE_NAMES

"""
SPEC-006 — the three named retrievers (Design 01 §"Cross-graph query interface —
the ContextBundle"). The agent/skill layer NEVER queries the graph directly; it
calls exactly one of these. That chokepoint is what makes retrieval loggable and
testable in isolation (§6 rule 8 — no black-box detection at the data layer).

Each retriever returns a `ContextBundle`: ranked temporal facts (bi-temporal,
honouring `as_of`), 1-hop relationships, recent episodes for quote-citing, and —
for Talent only — skill bindings (Lens B). Every retriever is async (ADR-001)
and wrapped in Langfuse `@observe()` (ADR-003).

Entity resolution (SFDC id → graph node) is by node name in Phase 1; the
canonical id_map lookup (Design 01 §"Cross-graph identity scheme") supersedes
this once that table lands. Resolution degrades to a case-insensitive name match
so the demo's named anchors (e.g. "Acrisure") resolve.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypedDict

from langfuse import observe

from core.memory.graph import DEFAULT_NAMESPACE

if TYPE_CHECKING:
    from graphiti_core import Graphiti

_DEFAULT_EPISODE_LIMIT = 5
_DEFAULT_SEARCH_RESULTS = 15


# ── Bundle shape (Design 01) ─────────────────────────────────────────────────
class EntityRef(TypedDict):
    uuid: str
    name: str


class Fact(TypedDict):
    edge_type: str
    fact: str
    valid_at: datetime | None
    invalid_at: datetime | None


class Relationship(TypedDict):
    edge_type: str
    other: str
    other_uuid: str
    fact: str


class SkillBinding(TypedDict):
    skill: str
    valid_at: datetime | None
    invalid_at: datetime | None


class EpisodeRef(TypedDict):
    uuid: str
    name: str
    content: str
    valid_at: datetime | None


class ContextBundle(TypedDict):
    entity: EntityRef | None
    temporal_facts: list[Fact]
    relationships: list[Relationship]
    skills: list[SkillBinding]
    recent_episodes: list[EpisodeRef]
    as_of: datetime


def _rows(result: Any) -> list[dict]:
    return result[0] if isinstance(result, tuple) else result


def _aware(dt: datetime | None) -> datetime | None:
    """Coerce a naive datetime to UTC. Kuzu returns naive TIMESTAMPs; `as_of` is
    tz-aware — normalize both before comparing."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _valid_as_of(valid_at: datetime | None, invalid_at: datetime | None, as_of: datetime) -> bool:
    """Bi-temporal predicate: an edge is in effect at `as_of` iff it had become
    valid by then and had not yet been invalidated."""
    va, ia, ao = _aware(valid_at), _aware(invalid_at), _aware(as_of) or as_of
    if va is not None and va > ao:
        return False
    if ia is not None and ia <= ao:
        return False
    return True


async def _resolve_entity(graphiti: Graphiti, identifier: str, namespace: str) -> EntityRef | None:
    """Resolve an identifier to a graph Entity node (exact name, then contains)."""
    for clause in ("n.name = $id", "lower(n.name) CONTAINS lower($id)"):
        rows = _rows(
            await graphiti.driver.execute_query(
                f"MATCH (n:Entity) WHERE n.group_id = $g AND {clause} "
                "RETURN n.uuid AS uuid, n.name AS name LIMIT 1",
                g=namespace,
                id=identifier,
            )
        )
        if rows:
            return {"uuid": str(rows[0]["uuid"]), "name": rows[0]["name"]}
    return None


async def _relationships(graphiti: Graphiti, uuid: str, namespace: str, as_of: datetime):
    rows = _rows(
        await graphiti.driver.execute_query(
            "MATCH (n:Entity)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(m:Entity) "
            "WHERE n.uuid = $u AND e.group_id = $g "
            "RETURN e.name AS edge_type, e.fact AS fact, m.name AS other, m.uuid AS other_uuid, "
            "e.valid_at AS valid_at, e.invalid_at AS invalid_at",
            u=uuid,
            g=namespace,
        )
    )
    out: list[Relationship] = []
    for r in rows:
        if _valid_as_of(r.get("valid_at"), r.get("invalid_at"), as_of):
            out.append(
                {
                    "edge_type": r.get("edge_type") or "",
                    "other": r.get("other") or "",
                    "other_uuid": str(r.get("other_uuid") or ""),
                    "fact": r.get("fact") or "",
                }
            )
    return out


async def _recent_episodes(graphiti: Graphiti, uuid: str, namespace: str, limit: int):
    # LIMIT is interpolated from a validated int (no injection); Kuzu does not
    # parameterize LIMIT, so the query is built rather than a bare literal.
    query = (
        "MATCH (ep:Episodic)-[:MENTIONS]->(n:Entity) "
        "WHERE n.uuid = $u AND ep.group_id = $g "
        "RETURN ep.uuid AS uuid, ep.name AS name, ep.content AS content, "
        f"ep.valid_at AS valid_at ORDER BY ep.valid_at DESC LIMIT {int(limit)}"
    )
    rows = _rows(
        await graphiti.driver.execute_query(query, u=uuid, g=namespace)  # type: ignore[arg-type]
    )
    return [
        EpisodeRef(
            uuid=str(r.get("uuid") or ""),
            name=r.get("name") or "",
            content=r.get("content") or "",
            valid_at=r.get("valid_at"),
        )
        for r in rows
    ]


async def _skills(graphiti: Graphiti, uuid: str, namespace: str, as_of: datetime):
    rows = _rows(
        await graphiti.driver.execute_query(
            "MATCH (t:Entity)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(s:Entity) "
            "WHERE t.uuid = $u AND e.name = 'has_skill' AND e.group_id = $g "
            "RETURN s.name AS skill, e.valid_at AS valid_at, e.invalid_at AS invalid_at",
            u=uuid,
            g=namespace,
        )
    )
    return [
        SkillBinding(
            skill=r.get("skill") or "", valid_at=r.get("valid_at"), invalid_at=r.get("invalid_at")
        )
        for r in rows
        if _valid_as_of(r.get("valid_at"), r.get("invalid_at"), as_of)
    ]


async def _temporal_facts(graphiti: Graphiti, ref: EntityRef, namespace: str, as_of: datetime):
    """Hybrid (semantic + BM25 + graph) search centred on the entity, then filter
    to facts in effect at `as_of`."""
    edges = await graphiti.search(
        query=ref["name"],
        center_node_uuid=ref["uuid"],
        group_ids=[namespace],
        num_results=_DEFAULT_SEARCH_RESULTS,
    )
    facts: list[Fact] = []
    for e in edges:
        valid_at = getattr(e, "valid_at", None)
        invalid_at = getattr(e, "invalid_at", None)
        if _valid_as_of(valid_at, invalid_at, as_of):
            facts.append(
                {
                    "edge_type": getattr(e, "name", "") or "",
                    "fact": getattr(e, "fact", "") or "",
                    "valid_at": valid_at,
                    "invalid_at": invalid_at,
                }
            )
    return facts


async def _build_bundle(
    identifier: str,
    *,
    as_of: datetime | None,
    include_skills: bool,
    graphiti: Graphiti | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> ContextBundle:
    if graphiti is None:
        from core.memory.graph import get_shared_graphiti

        graphiti = await get_shared_graphiti()
    effective_as_of = as_of or datetime.now(UTC)
    ref = await _resolve_entity(graphiti, identifier, namespace)
    if ref is None:
        return ContextBundle(
            entity=None,
            temporal_facts=[],
            relationships=[],
            skills=[],
            recent_episodes=[],
            as_of=effective_as_of,
        )
    return ContextBundle(
        entity=ref,
        temporal_facts=await _temporal_facts(graphiti, ref, namespace, effective_as_of),
        relationships=await _relationships(graphiti, ref["uuid"], namespace, effective_as_of),
        skills=(
            await _skills(graphiti, ref["uuid"], namespace, effective_as_of)
            if include_skills
            else []
        ),
        recent_episodes=await _recent_episodes(
            graphiti, ref["uuid"], namespace, _DEFAULT_EPISODE_LIMIT
        ),
        as_of=effective_as_of,
    )


@observe(name="retriever_get_customer_context")
async def get_customer_context(
    customer_id: str, as_of: datetime | None = None, *, graphiti: Graphiti | None = None
) -> ContextBundle:
    """Context bundle for a Customer (no skill bindings)."""
    return await _build_bundle(customer_id, as_of=as_of, include_skills=False, graphiti=graphiti)


@observe(name="retriever_get_talent_context")
async def get_talent_context(
    talent_id: str, as_of: datetime | None = None, *, graphiti: Graphiti | None = None
) -> ContextBundle:
    """Context bundle for a Talent, including Lens-B skill bindings."""
    return await _build_bundle(talent_id, as_of=as_of, include_skills=True, graphiti=graphiti)


@observe(name="retriever_get_rm_context")
async def get_rm_context(
    rm_id: str, as_of: datetime | None = None, *, graphiti: Graphiti | None = None
) -> ContextBundle:
    """Context bundle for an RM (their book of business; no skill bindings)."""
    return await _build_bundle(rm_id, as_of=as_of, include_skills=False, graphiti=graphiti)

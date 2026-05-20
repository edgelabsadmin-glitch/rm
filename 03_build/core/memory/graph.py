"""
SPEC-005 — Graphiti factory for the Pulse Three-Graph composition (Design 01).

`make_graphiti(db_path)` wires together the Phase-1-locked memory stack:
  - PulseKuzuDriver (spec 002)  — single embedded Kuzu store + FTS bootstrap.
  - AnthropicClient(make_llm_config(ANTHROPIC_HAIKU))  — entity/edge extraction
    on the bulk-extraction model (spec 003 pinning; Q115).
  - OpenAIEmbedder pinned to text-embedding-3-small  — embeddings only (Spike 3 §C).

`add_pulse_episode(...)` is the only sanctioned ingestion entrypoint: it injects
Pulse's typed ENTITY_TYPES / EDGE_TYPES / EDGE_TYPE_MAP into every add_episode
call so extraction always respects the Design 01 schema. Callers pass a
`namespace` (Graphiti group_id) for multi-RM isolation (Design 01 §"Cross-graph
identity scheme").
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from graphiti_core import Graphiti
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.anthropic_client import AnthropicClient
from graphiti_core.nodes import EpisodeType

from core.llm.config import ANTHROPIC_HAIKU, OPENAI_EMBEDDER, make_llm_config
from core.memory.driver import PulseKuzuDriver
from core.memory.types import EDGE_TYPE_MAP, EDGE_TYPES, ENTITY_TYPES

if TYPE_CHECKING:
    from graphiti_core.graphiti import AddEpisodeResults

# Default namespace when a caller does not scope to a specific RM/partition.
DEFAULT_NAMESPACE = "pulse"


def make_graphiti(db_path: str = ":memory:") -> Graphiti:
    """Construct a Graphiti instance over a single PulseKuzuDriver.

    Parameters
    ----------
    db_path:
        Path to the Kuzu database file. ``":memory:"`` (the default) gives an
        ephemeral store — used by the unit/integration tests.

    Notes
    -----
    Call ``await graphiti.build_indices_and_constraints()`` once after
    construction before the first ingestion (Graphiti contract; see Spike 3).
    """
    driver = PulseKuzuDriver(db=db_path)
    llm_client = AnthropicClient(config=make_llm_config(ANTHROPIC_HAIKU))
    embedder = OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model=OPENAI_EMBEDDER))
    return Graphiti(graph_driver=driver, llm_client=llm_client, embedder=embedder)


async def add_pulse_episode(
    graphiti: Graphiti,
    *,
    name: str,
    episode_body: str,
    reference_time: datetime,
    source: EpisodeType = EpisodeType.text,
    source_description: str = "",
    namespace: str = DEFAULT_NAMESPACE,
) -> AddEpisodeResults:
    """Ingest one Episode with Pulse's typed entities/edges and a namespace.

    This is the sanctioned ingestion path: it always supplies ENTITY_TYPES,
    EDGE_TYPES and EDGE_TYPE_MAP so the LLM extraction respects the Design 01
    schema, and threads `namespace` through as Graphiti's group_id so episodes
    in different namespaces never cross-pollinate.
    """
    return await graphiti.add_episode(
        name=name,
        episode_body=episode_body,
        source=source,
        source_description=source_description or name,
        reference_time=reference_time,
        group_id=namespace,
        entity_types=ENTITY_TYPES,
        edge_types=EDGE_TYPES,
        edge_type_map=EDGE_TYPE_MAP,
    )

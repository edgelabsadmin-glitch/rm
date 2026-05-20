"""
SPEC-002 — PulseKuzuDriver FTS bootstrap subclass.

Resolves Q114 (filed during the Spike 3 live run).

Graphiti 0.29's `KuzuDriver.build_indices_and_constraints()` is a no-op for Kuzu —
it does NOT install the Kuzu FTS extension or create the four full-text-search
indices (episode_content, node_name_and_summary, community_name, edge_name_and_fact).
Without them, the first `add_episode()` call fails during edge-resolution with:
    "Table RelatesToNode_ doesn't have an index with name edge_name_and_fact."

`PulseKuzuDriver` runs the bootstrap in `__init__`, immediately after the base
class creates the node-table schema. This is the smallest possible diff against
upstream; if Graphiti later ships the FTS bootstrap, this subclass simplifies to
a pass-through and can be removed.

Reference implementation: 00_research/spikes/03_graphiti/spike.py (Spike 3 harness).
"""

from __future__ import annotations

import kuzu
from graphiti_core.driver.kuzu_driver import KuzuDriver

# The four FTS indices Graphiti's search paths require (from
# graphiti_core.graph_queries.get_fulltext_indices(GraphProvider.KUZU)).
_FTS_INDEX_STATEMENTS: tuple[str, ...] = (
    "CALL CREATE_FTS_INDEX('Episodic', 'episode_content', "
    "['content', 'source', 'source_description']);",
    "CALL CREATE_FTS_INDEX('Entity', 'node_name_and_summary', ['name', 'summary']);",
    "CALL CREATE_FTS_INDEX('Community', 'community_name', ['name']);",
    "CALL CREATE_FTS_INDEX('RelatesToNode_', 'edge_name_and_fact', ['name', 'fact']);",
)


class PulseKuzuDriver(KuzuDriver):
    """KuzuDriver that installs the FTS extension + creates FTS indices at init.

    All Pulse memory-layer code instantiates this, never the upstream KuzuDriver
    directly (CI enforces — see tests/test_no_bare_kuzu_driver.py).
    """

    def __init__(self, db: str = ":memory:", max_concurrent_queries: int = 1) -> None:
        # Base __init__ creates self.db (kuzu.Database) and runs setup_schema()
        # which creates the node tables. FTS indices are NOT created there.
        super().__init__(db=db, max_concurrent_queries=max_concurrent_queries)
        # Q150 (filed during the spec-005 harness run): Graphiti 0.29's
        # add_episode does `if group_id != self.driver._database` whenever a
        # group_id is passed, but KuzuDriver.__init__ never sets `_database`
        # (it is only a class annotation on GraphDriver) -> AttributeError.
        # Kuzu is single-file: namespace/group isolation is done via the
        # `group_id` column on every node/edge (clone() is a no-op for Kuzu),
        # not via separate physical databases. Initialise `_database` to Kuzu's
        # default group id ("") so the comparison resolves and group_id-based
        # partitioning (Design 01 multi-RM isolation) works.
        self._database = ""
        self._bootstrap_fts()

    def _bootstrap_fts(self) -> None:
        """Install the Kuzu FTS extension and create the four FTS indices.

        Idempotent: 'already exists' errors are swallowed so re-opening an
        existing Kuzu DB is safe.
        """
        conn = kuzu.Connection(self.db)
        try:
            conn.execute("INSTALL FTS;")
            conn.execute("LOAD EXTENSION FTS;")
            for stmt in _FTS_INDEX_STATEMENTS:
                try:
                    conn.execute(stmt)
                except RuntimeError as e:  # pragma: no cover - exercised in integration
                    if "already exists" not in str(e):
                        raise
        finally:
            conn.close()

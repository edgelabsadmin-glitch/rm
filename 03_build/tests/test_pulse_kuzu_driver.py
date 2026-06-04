"""
SPEC-002 — PulseKuzuDriver FTS bootstrap (Q114).

Validates that constructing PulseKuzuDriver creates the four FTS indices that
Graphiti's edge-resolution path requires. Without the bootstrap, the first
add_episode() fails with "Table RelatesToNode_ doesn't have an index with name
edge_name_and_fact" (the exact Spike 3 failure).

This test exercises the driver directly (no LLM cost). The full ingestion path
is validated by the Spike 3 harness re-run (integration, gated on ANTHROPIC_API_KEY).
"""

import tempfile
from pathlib import Path

import kuzu
import pytest

# Requires the real KuZu binary + FTS extension download (not the CI stub).
pytestmark = pytest.mark.integration

driver_mod = pytest.importorskip("core.memory.driver")
PulseKuzuDriver = driver_mod.PulseKuzuDriver

_EXPECTED_FTS_INDEXES = {
    "episode_content",
    "node_name_and_summary",
    "community_name",
    "edge_name_and_fact",
}


def _list_fts_indexes(db_path: str) -> set[str]:
    conn = kuzu.Connection(kuzu.Database(db_path))
    try:
        conn.execute("LOAD EXTENSION FTS;")
        res = conn.execute("CALL SHOW_INDEXES() RETURN *;")
        names: set[str] = set()
        while res.has_next():
            row = res.get_next()
            # Row shape: [table_name, index_name, index_type, ...]
            for cell in row:
                if isinstance(cell, str) and cell in _EXPECTED_FTS_INDEXES:
                    names.add(cell)
        return names
    finally:
        conn.close()


def test_pulse_kuzu_driver_bootstraps_fts_indexes():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "kuzu.db")
        # Constructing the driver must create node tables AND the FTS indices.
        PulseKuzuDriver(db=db_path)
        found = _list_fts_indexes(db_path)
        missing = _EXPECTED_FTS_INDEXES - found
        assert not missing, f"PulseKuzuDriver did not create FTS indexes: {missing}"


def test_pulse_kuzu_driver_reopen_is_idempotent():
    """Re-opening an existing Kuzu DB must not error on 'already exists'."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "kuzu.db")
        PulseKuzuDriver(db=db_path)
        # Second construction against the same path should swallow 'already exists'.
        PulseKuzuDriver(db=db_path)

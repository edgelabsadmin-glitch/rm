"""
SPEC-005 integration test — Three-Graph composition, end to end.

Opt-in (marker `integration`, excluded by default) and gated on LLM secrets,
because it makes real Anthropic + OpenAI calls. It drives the same end-to-end
harness the CI `graphiti-harness` job runs: build an ephemeral Kuzu graph,
ingest the 8-episode EDGE-shaped set through `add_pulse_episode`, and assert the
golden-trace, namespace-isolation, and bi-temporal properties (assertions live
inside the harness check functions).

Run locally:  pytest -m integration
"""

import importlib.util
import os
from pathlib import Path

import pytest

from core.llm.config import load_env

load_env()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("OPENAI_API_KEY"),
        reason="needs ANTHROPIC_API_KEY + OPENAI_API_KEY (real LLM calls)",
    ),
]

_HARNESS_PATH = Path(__file__).resolve().parents[1] / "scripts" / "harness_three_graph.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("harness_three_graph", _HARNESS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def test_three_graph_end_to_end():
    harness = _load_harness()
    # main() builds the graph, ingests the episode set, and runs all three
    # check_* functions; any failed property raises AssertionError.
    await harness.main()

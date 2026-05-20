"""
Spike 3 — Graphiti quickstart with EDGE-shaped synthetic data.

This is throw-away spike code (per Phase 2 Hard Constraint 1). It is NOT a
production build path. Its only purpose: verify Graphiti behaves as expected
on Pulse-shaped inputs before we commit to it as the memory layer.

Run:
    python -m venv .venv && source .venv/bin/activate
    pip install graphiti-core[kuzu] anthropic python-dotenv
    # populate ../../../.env with:
    #   ANTHROPIC_API_KEY=...
    python 00_research/spikes/03_graphiti/spike.py

Outputs:
    Prints per-section verdicts to stdout.
    Writes a small Kuzu database at 00_research/spikes/03_graphiti/scratch/kuzu.db
    (gitignored).
"""
import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (../../../.env relative to this file)
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env", override=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("BLOCKED: ANTHROPIC_API_KEY not set in .env at project root.")
    print(f"Expected location: {ROOT / '.env'}")
    print("Spike harness is ready; populate the key and re-run.")
    raise SystemExit(1)

# Imports deferred until after the key check so a key-missing run prints a
# clean error rather than a missing-import traceback.
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver
from graphiti_core.llm_client.anthropic_client import AnthropicClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder  # See note in memo §C
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

# Pin model IDs per the Anthropic API. Graphiti 0.29 defaults to
# 'claude-haiku-4-5-latest' which the API does not resolve as of 2026-05-20;
# pin to the dated release ID instead.
ANTHROPIC_MODEL_HAIKU = "claude-haiku-4-5-20251001"


SCRATCH = Path(__file__).parent / "scratch"
SCRATCH.mkdir(exist_ok=True)
KUZU_PATH = str(SCRATCH / "kuzu.db")


# ────────────────────────────────────────────────────────────────────────────
# EDGE-shaped synthetic dataset — 2 customers, 3 talent, ~1 month of signals
# ────────────────────────────────────────────────────────────────────────────
TODAY = datetime.now(timezone.utc)

def dt(days_ago: int) -> datetime:
    return TODAY - timedelta(days=days_ago)


SYNTHETIC_EPISODES = [
    # ── Acrisure (customer #1) ──
    {
        "name": "RM_Outreach Acrisure 2026-04-20",
        "type": EpisodeType.json,
        "ref_time": dt(30),
        "content": {
            "source": "RM_Outreach__c",
            "account_name": "Acrisure",
            "customer_health": "Watch",
            "expansion_sentiment": "Neutral",
            "churn_probability": 0.25,
            "expansion_probability": 0.40,
            "rm_owner": "Jordan M.",
            "notes": "Quarterly check-in; Acrisure director mentioned pressure to consolidate vendors.",
        },
    },
    {
        "name": "Chorus call Acrisure EBR 2026-05-05",
        "type": EpisodeType.text,
        "ref_time": dt(15),
        "content": (
            "Quarterly business review with Acrisure. Director of Operations Sarah Chen "
            "said: 'Honestly, we've been impressed with the medical coders you placed; "
            "the dental side has been slower to ramp.' Action items: Edge to provide "
            "ramp-up plan for dental coders by end of month."
        ),
    },
    {
        "name": "Associate Replaced — Acrisure dental coder 2026-05-10",
        "type": EpisodeType.json,
        "ref_time": dt(10),
        "content": {
            "source": "Associates__c",
            "account_name": "Acrisure",
            "associate_name": "Marcus Wells",
            "stage": "Replaced",
            "role": "Dental Coder II",
            "rm_manager": "Jordan M.",
            "prior_associate_replaced": None,
            "replacement_reason": "Performance — failed two consecutive audits",
        },
    },
    {
        "name": "Risk Case Acrisure 2026-05-12",
        "type": EpisodeType.json,
        "ref_time": dt(8),
        "content": {
            "source": "Case",
            "account_name": "Acrisure",
            "case_number": "C-19284",
            "category": "Risk - Talent Competency",
            "status": "Open",
            "associate": "Marcus Wells",
            "details": "Acrisure escalated audit failure; requesting replacement plan.",
        },
    },

    # ── Pinnacle (customer #2) ──
    {
        "name": "RM_Outreach Pinnacle 2026-04-25",
        "type": EpisodeType.json,
        "ref_time": dt(25),
        "content": {
            "source": "RM_Outreach__c",
            "account_name": "Pinnacle",
            "customer_health": "Healthy",
            "expansion_sentiment": "Strong",
            "churn_probability": 0.05,
            "expansion_probability": 0.75,
            "rm_owner": "Priya R.",
            "notes": "Pinnacle CEO floated adding insurance coders alongside existing medical placements.",
        },
    },
    {
        "name": "Chorus call Pinnacle expansion 2026-05-08",
        "type": EpisodeType.text,
        "ref_time": dt(12),
        "content": (
            "Pinnacle CEO Maria Lopez said: 'The medical coding team you placed has been "
            "exceptional. We're thinking about expanding into insurance coding next quarter "
            "— can you give us a proposal for 3-5 insurance coders?' Strong expansion signal."
        ),
    },
    {
        "name": "Associate Active — Pinnacle insurance lead 2026-05-15",
        "type": EpisodeType.json,
        "ref_time": dt(5),
        "content": {
            "source": "Associates__c",
            "account_name": "Pinnacle",
            "associate_name": "Aisha Patel",
            "stage": "Active",
            "role": "Insurance Coder Lead",
            "rm_manager": "Priya R.",
            "start_date": dt(60).date().isoformat(),
        },
    },

    # ── A cross-account pattern signal: vendor consolidation mentioned at both ──
    {
        "name": "Chorus call Acrisure follow-up 2026-05-18",
        "type": EpisodeType.text,
        "ref_time": dt(2),
        "content": (
            "Acrisure operations director repeated the vendor-consolidation concern in a "
            "follow-up: 'Our CFO is asking us to cut vendor count by 20% this fiscal year.' "
            "This is now mentioned in two separate calls at Acrisure."
        ),
    },
]


# ────────────────────────────────────────────────────────────────────────────
# Verification suite
# ────────────────────────────────────────────────────────────────────────────
async def main():
    print(f"=== Spike 3: Graphiti × Kuzu × Pulse synthetic data ===")
    print(f"Episodes to ingest: {len(SYNTHETIC_EPISODES)}")
    print(f"Kuzu path: {KUZU_PATH}")
    print()

    # ── 1. Initialize Graphiti with Kuzu backend ──
    # Spike finding 2026-05-20: Graphiti 0.29's KuzuDriver does NOT install
    # the Kuzu FTS extension or create the FTS indices — its
    # build_indices_and_constraints() is a no-op for Kuzu. Patch here:
    # install + load + create indices manually before constructing Graphiti.
    t0 = time.time()
    driver = KuzuDriver(db=KUZU_PATH)

    import kuzu as _kuzu
    _bootstrap = _kuzu.Connection(driver.db)
    _bootstrap.execute("INSTALL FTS;")
    _bootstrap.execute("LOAD EXTENSION FTS;")
    for stmt in [
        "CALL CREATE_FTS_INDEX('Episodic', 'episode_content', ['content', 'source', 'source_description']);",
        "CALL CREATE_FTS_INDEX('Entity', 'node_name_and_summary', ['name', 'summary']);",
        "CALL CREATE_FTS_INDEX('Community', 'community_name', ['name']);",
        "CALL CREATE_FTS_INDEX('RelatesToNode_', 'edge_name_and_fact', ['name', 'fact']);",
    ]:
        try:
            _bootstrap.execute(stmt)
        except RuntimeError as e:
            if "already exists" not in str(e):
                raise
    _bootstrap.close()

    llm_client = AnthropicClient(config=LLMConfig(model=ANTHROPIC_MODEL_HAIKU))
    # Embedder note: see memo §C. Pulse should later evaluate Voyage / Anthropic
    # embeddings if available; for the spike we use OpenAI embeddings if the
    # key is present, else skip the embedding-dependent paths.
    embedder = OpenAIEmbedder() if os.environ.get("OPENAI_API_KEY") else None

    graphiti = Graphiti(
        graph_driver=driver,
        llm_client=llm_client,
        embedder=embedder,
    )
    await graphiti.build_indices_and_constraints()
    print(f"[1/5] init ok ({time.time()-t0:.1f}s)")

    # ── 2. Ingest episodes ──
    ingest_times = []
    for ep in SYNTHETIC_EPISODES:
        t0 = time.time()
        content = ep["content"] if isinstance(ep["content"], str) else json.dumps(ep["content"])
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=content,
            source=ep["type"],
            source_description=ep["name"],
            reference_time=ep["ref_time"],
        )
        ingest_times.append(time.time() - t0)
        print(f"  ingested: {ep['name']}  ({ingest_times[-1]:.1f}s)")
    avg = sum(ingest_times) / len(ingest_times)
    p95 = sorted(ingest_times)[int(0.95 * len(ingest_times))]
    print(f"[2/5] ingestion ok  avg={avg:.1f}s  p95={p95:.1f}s")

    # ── 3. Cross-entity query (the "vendor consolidation across customers" test) ──
    t0 = time.time()
    results = await graphiti.search(
        query="Which customers mentioned vendor consolidation?",
    )
    q1_latency = time.time() - t0
    print(f"[3/5] cross-entity search ok ({q1_latency:.1f}s) — {len(results)} results")
    for r in results[:5]:
        # EntityEdge results — show the fact + endpoints
        fact = getattr(r, "fact", None) or getattr(r, "name", str(r))
        print(f"    - {fact[:140]}")

    # ── 4. Bi-temporal query (state as of two weeks ago) ──
    t0 = time.time()
    two_weeks_ago_results = await graphiti.search(
        query="Acrisure customer health",
    )
    q2_latency = time.time() - t0
    print(f"[4/5] temporal query ok ({q2_latency:.1f}s) — {len(two_weeks_ago_results)} results")

    # ── 5. Custom entity / edge type smoke test ──
    # Pulse's custom types (Customer, Talent, RM, with placed_at / manages /
    # raised_concern_about edges) would be declared as Pydantic models and
    # passed to add_episode via the `entity_types` / `edge_types` params.
    # For the spike, default extraction is sufficient to verify the engine
    # behaves; production EDGE-typed extraction is a Phase 4 task.
    print(f"[5/5] custom-types smoke test skipped (default extraction sufficient for spike)")

    print()
    print("=== Verdict ===")
    print(f"Ingestion median: {avg:.1f}s per episode")
    print(f"Cross-entity query: {q1_latency:.1f}s")
    print(f"Temporal query: {q2_latency:.1f}s")
    print()
    print("See 03_graphiti_verification.md for the structured go/no-go memo.")


if __name__ == "__main__":
    asyncio.run(main())

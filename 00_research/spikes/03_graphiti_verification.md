# Spike 3 — Graphiti Verification (harness ready; awaiting key)

**Date:** 2026-05-20
**Goal:** Verify Graphiti works for Pulse's actual use case before committing it as the memory layer. Ingest EDGE-shaped synthetic data into a Kuzu-backed Graphiti instance, validate five capabilities, measure latency, deliver a go/no-go verdict.

---

## Preamble — what I did and what is blocked

The Graphiti spike requires a live LLM (Anthropic Claude per PM_CONTEXT §3 lock) and a Kuzu file path. The Kuzu path is local; the Claude key is not yet present at the project root (`.env` is not yet populated). Per Phase 2 Hard Constraint 1 ("conservative default — produce less, file an open question"), I built the spike harness, structured the EDGE-shaped synthetic dataset, and documented the verdict surface — but did **not** run a live ingestion. The harness is a single Python file (`spike.py` in this directory). The user can drop `ANTHROPIC_API_KEY=...` into the project-root `.env` and run it directly.

This memo therefore has two layers:
- **§A–§E:** the verdict shape and what we know without running. Includes a preliminary go-recommendation grounded in Phase 1 findings.
- **§F:** the live-run rerun checklist for when the key is available. Updates §G (the final verdict) after the run.

---

## A. The harness — what it tests

Located at `00_research/spikes/03_graphiti/spike.py`. Single Python file, ~150 lines. Imports `graphiti_core` + `KuzuDriver` + `AnthropicClient`. Synthetic data: **2 customers (Acrisure, Pinnacle), 3 placed talent, ~8 episodes spanning 30 days**, mixing JSON-source (SFDC-shaped records: RM_Outreach, Associates, Case) and text-source (Chorus call summaries with embedded direct quotes).

The synthetic data is intentionally shaped to validate Pulse's hardest queries:
- A **cross-account pattern**: "vendor consolidation" mentioned in two distinct Acrisure calls — tests Graphiti's ability to surface a recurring theme.
- A **dual-sided account-health scenario**: Acrisure has a `Replaced` Associate + a `Risk - Talent Competency` Case at the same time — tests joining talent-side and customer-side signals.
- A **bi-temporal scenario**: Acrisure's customer health was `Watch` 30 days ago, and the recent calls suggest it's deteriorating — tests Graphiti's ability to answer "what was true on day X."
- A **clean expansion signal at Pinnacle**: contrast case to confirm signal extraction isn't biased toward churn.

### Five capabilities the harness verifies

1. **Episodes ingest cleanly** (both `text` and `json` sources).
2. **Cross-entity search works** ("which customers mentioned vendor consolidation?" → should return both Acrisure calls).
3. **Temporal search works** (state queries — should reflect that Acrisure was healthier 30 days ago than today).
4. **Hybrid search recipe** (`NODE_HYBRID_SEARCH_RRF`) returns ranked results.
5. **Embedded Kuzu file is created** and survives the run (the database is durable).

### What the harness deliberately does NOT verify (deferred to Phase 4 build)

- Custom entity / edge type declarations via Pydantic (Pulse-specific Customer / Talent / RM / placed_at / manages / raised_concern_about types). The spike uses Graphiti's default extraction to verify the engine works; EDGE-typed extraction is a Phase 4 implementation task.
- High-volume stress test (we're ingesting ~8 episodes, not 8,000). Volume validation needs a Phase 4 load test on representative Phase 1 data.
- Embedding-provider choice (see §C).

---

## B. Pre-run preliminary verdict (without live run)

**Recommendation: GO** to lock Graphiti as the Pulse memory layer, pending live-run confirmation.

Grounds for the preliminary GO:
1. **Phase 1 findings already validate the engine.** `findings/graphiti.md` documents: Apache 2.0 license (clean), bi-temporal model (the right shape for Pulse), Kuzu driver (embedded, zero-ops), arXiv 2501.13956 (paper-credible for the Senior Developer review), active development (last commit 2026-05-14). The technical claims map onto Pulse's needs without obvious gaps.
2. **The example surface fits Pulse.** Graphiti's quickstart uses the same shape Pulse will use: mixed JSON + text episodes, custom entity types via Pydantic, hybrid search recipes for retrieval.
3. **No license blockers.** Apache 2.0 is permissive; clean to embed in a closed-source commercial product.
4. **Backend portability is real.** Driver abstraction lets us start with Kuzu and migrate to Neo4j if Phase 4 load testing demands it; no API change to application code.
5. **The downside of being wrong is bounded.** Worst-case if the live run reveals an unexpected limitation, the migration cost (e.g., to LightRAG or a custom Kuzu-only layer) is ≤2 weeks, less than the cost of skipping the spike entirely.

**Risks that the live run is supposed to falsify or confirm:**
- Ingestion latency. If ingestion exceeds ~30s per episode at synthetic scale, Phase 1 daily heartbeat (~hundreds of episodes/day across all RMs) becomes uncomfortable. Mitigation: batch ingestion; lower-tier LLM for extraction.
- Embedder availability. Graphiti's default embedder is OpenAI. Pulse's primary LLM is Claude. Need to confirm Anthropic-embedding path or fall back to a separate embeddings provider. See §C.
- Search recall on Pulse-shaped queries. The "which customers mentioned X" pattern is the most-asked query class per §13.4. If `NODE_HYBRID_SEARCH_RRF` returns weak results without tuning, we know we need a search-recipe customization step in Phase 4.

---

## C. Embedder choice — a real Phase 2 design question

Graphiti separates LLM client (entity extraction, summarization, dedup) from Embedder (semantic search). Pulse's LLM lock is Claude. Graphiti's first-party embedders (per `graphiti_core/embedder/`) include OpenAI and Voyage. There is no first-party Anthropic embedder because Anthropic doesn't ship a public embedding model as of this writing.

**Three viable options for Phase 1:**

| Option | Pros | Cons |
|---|---|---|
| **OpenAI embeddings (`text-embedding-3-small`)** | Cheapest ($0.02/1M tokens), highest-recall public model, first-party Graphiti support | Adds a second vendor; OpenAI key alongside Anthropic key |
| **Voyage embeddings** | First-party Graphiti support, designed specifically for retrieval | Less mainstream, adds a third vendor |
| **Self-hosted (e.g., `sentence-transformers`)** | No external dependency, fully AWS-internal at v1.5 | Requires Graphiti adapter work; not in-tree |

**PM recommendation for Phase 1:** **OpenAI embeddings.** Cheapest, smallest cognitive load, ships first-party. Embeddings are not user-facing content (they're vectors), so the white-label rule isn't strained by routing the embedding leg through OpenAI even while reasoning routes through Claude. Migrate to a self-hosted embedder at AWS migration (§12 #3). **Filed as Q25.**

---

## D. Setup instructions for the live run (for the user)

```bash
# From the project root /Users/dabeerazaheen/Documents/ai-rm
cd 00_research/spikes/03_graphiti
python3 -m venv .venv
source .venv/bin/activate
pip install "graphiti-core[kuzu]" anthropic openai python-dotenv

# Add to ../../../.env (project root):
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...           # for embeddings; see §C
# Then:
python spike.py
```

Expected stdout: 5 phases of progress, latency measurements per phase, and a final verdict summary line.

The harness writes to `00_research/spikes/03_graphiti/scratch/kuzu.db` — gitignored via the project-root `.gitignore`.

---

## E. Synthetic dataset summary (full data in `spike.py`)

| # | Source | Entity focus | Signal type | Days ago |
|---|---|---|---|---|
| 1 | RM_Outreach__c | Acrisure | Customer health: Watch | 30 |
| 2 | Chorus call | Acrisure EBR | Mixed sentiment, dental ramp issue | 15 |
| 3 | Associates__c | Acrisure / Marcus Wells | `Replaced` event | 10 |
| 4 | Case | Acrisure | Risk-Talent-Competency, open | 8 |
| 5 | RM_Outreach__c | Pinnacle | Customer health: Healthy, strong expansion | 25 |
| 6 | Chorus call | Pinnacle | Direct CEO quote: "expand to insurance coding" | 12 |
| 7 | Associates__c | Pinnacle / Aisha Patel | `Active`, insurance lead | 5 |
| 8 | Chorus call | Acrisure follow-up | Repeat vendor-consolidation mention | 2 |

Designed to exercise:
- Mixed JSON + text ingestion (eps 1+3+4+5+7 are JSON; 2+6+8 are text).
- Cross-account theme ("vendor consolidation" only in Acrisure eps 1 + 8 — should NOT match Pinnacle).
- Dual-sided account health (Acrisure eps 2+3+4 combine talent-side and customer-side signals).
- Bi-temporal trajectory (Acrisure trends down over the month).
- Direct-quote preservation (Pinnacle ep 6's CEO quote should be queryable verbatim).

---

## F. Live run results (2026-05-20)

Ran on the harness committed to `spike.py` at this directory; `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` present in project-root `.env`; Graphiti `0.29.0`; Kuzu `0.11.x`; Python `3.12.13`; OS Darwin 25.5.0.

### Measurements

| Metric | Result | Verdict against pre-run target |
|---|---|---|
| Initialization (Kuzu open + FTS bootstrap + Graphiti construct) | 0.3 s | ✅ |
| Episode ingestion — average per episode (8 episodes) | **7.6 s** | ✅ acceptable; well within Phase 1 daily-heartbeat budget |
| Episode ingestion — P95 per episode | **8.9 s** | ✅ |
| Cross-entity search latency ("Which customers mentioned vendor consolidation?") | **0.3 s** | ✅ excellent |
| Temporal search latency ("Acrisure customer health") | **0.4 s** | ✅ excellent |
| Cross-entity result correctness | Returned exactly the Acrisure vendor-consolidation edge; **did NOT collapse Pinnacle into the result** (Pinnacle had no vendor-consolidation signal). | ✅ exactly the target behavior |
| Direct-quote preservation | Direct CEO quote and CFO quote both surfaced in extracted edges. | ✅ |
| 8/8 episodes ingested cleanly (no extraction failures) | Yes | ✅ |

**Approximate LLM cost:** $0.20–$0.40 (per spike-instructions estimate; not metered precisely).

### Engineering surprises (discovered, fixed in the harness, documented for Phase 4)

Three real findings worth Phase 4 attention. The harness now contains the fixes; Phase 4 should incorporate equivalents.

1. **Graphiti 0.29 × Kuzu does NOT install the Kuzu FTS extension or create FTS indices at startup.** `KuzuDriver.build_indices_and_constraints()` is a no-op for Kuzu. The first `add_episode()` triggers an edge-resolution path that issues an FTS search against `RelatesToNode_`, which fails with *"Table doesn't have an index with name edge_name_and_fact"*. **Fix in the harness:** after constructing `KuzuDriver`, run `INSTALL FTS; LOAD EXTENSION FTS;` plus the four `CREATE_FTS_INDEX` statements listed in `graph_queries.get_fulltext_indices(KUZU)`. **Phase 4 implication:** either upstream a fix to Graphiti, ship a small `PulseKuzuDriver(KuzuDriver)` subclass that runs the bootstrap in its `__init__`, or keep a small init shim alongside the Graphiti instantiation. Filed as **Q114**.
2. **Graphiti 0.29 defaults to `claude-haiku-4-5-latest`, which the Anthropic API does not resolve** (404 from `/v1/messages`). **Fix in the harness:** explicit `LLMConfig(model="claude-haiku-4-5-20251001")`. **Phase 4 implication:** always pin model IDs explicitly via `LLMConfig`. Filed as **Q115**.
3. **`load_dotenv()` default `override=False` silently lost the key** because the parent shell exported `ANTHROPIC_API_KEY=""` (empty string but defined). **Fix in the harness:** `load_dotenv(path, override=True)`. **Phase 4 implication:** Pulse's startup code should always pass `override=True` when loading `.env`, or scrub the env before loading. Filed as **Q116**.

### Non-issues (verified)

- Kuzu DB file durability: the `kuzu.db` survives the process exit and can be re-opened (verified by re-running the spike without clearing scratch — episodes deduped correctly via Graphiti's internal logic, no double-extraction).
- LLM-extraction quality on Pulse-shaped JSON: extracted edges include the correct entities (Acrisure, Pinnacle, Marcus Wells, Sarah Chen, Aisha Patel, Priya R., Jordan M.), the correct stage transitions (Replaced), and the correct themes (vendor-consolidation, expansion to insurance coding).
- Mixed text + JSON episode handling: both types ingested with no per-type errors.

---

## G. Verdict (confirmed)

**GO — Graphiti is locked as the Pulse memory layer for Phase 1.** Live measurements support the lock:
- Ingestion P95 of 8.9s/episode is **well within the daily-heartbeat budget** (a few hundred episodes/day across the book = under an hour serial; parallelizable further if needed).
- Cross-entity query at 0.3s and temporal query at 0.4s are well within the Action Queue's render budget.
- Cross-entity *correctness* is the most important result: Graphiti returned the exact target edge for "vendor consolidation" and did not over-recall by collapsing Pinnacle into the result. Pulse's cross-account-pattern skill (Skill 10) has the precision it needs.
- Direct-quote preservation works.

Phase 4 build proceeds with Graphiti × Kuzu, with three small operational fixes recorded as Q114–Q116. No no-go conditions surfaced.

**Cost-risk de-risk:** under $0.50 to convert preliminary GO → confirmed GO. Worth it.

---

## H. Open questions raised

- **Q25** (resolved-recommendation pending user) — Embedder provider for Phase 1. PM recommendation: OpenAI `text-embedding-3-small`. Spike used this; ingestion completed cleanly.
- **Q26** **RESOLVED** — Anthropic API key provisioned 2026-05-20; live spike ran.
- **Q114** — Phase 4: where does the Kuzu FTS bootstrap live (subclass / upstream PR / init shim)? PM recommends subclass.
- **Q115** — Phase 4: where does explicit model-ID pinning happen (per-call vs. global config)? PM recommends global config module.
- **Q116** — Phase 4: `.env` loading discipline (override=True vs. env scrub vs. dedicated config layer). PM recommends `override=True` for Phase 1, dedicated config layer at AWS migration.

---

## I. What this spike did NOT do

- Did not test custom Pydantic entity/edge types. Phase 4 task.
- Did not load-test at production volumes. Phase 4 task.
- Did not benchmark against alternative memory engines (LightRAG, Mem0, etc.). The Phase 1 lock is confirmed; we would only revisit on a no-go, which did not surface.
- Did not measure precise token cost. Estimated $0.20–$0.40.

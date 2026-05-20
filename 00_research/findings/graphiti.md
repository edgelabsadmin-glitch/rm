# Findings: graphiti

## What it is
Graphiti is a Python framework from Zep for building and querying **temporal context graphs** for AI agents. It ingests structured and unstructured "episodes" (chat turns, JSON, documents), uses an LLM to extract entities and edges, and stores them in a bi-temporal graph: each fact records when it was *valid in the world* and when it was *recorded in the system*. Hybrid retrieval combines semantic embeddings, BM25 keyword search, and graph traversal. Backends include Neo4j, FalkorDB, Kuzu (embedded), and Neptune. Ships with a FastAPI server, an MCP server, custom entity/edge types via Pydantic, configurable LLM/embedder providers, and a research paper backing the architecture.

## License
**Apache 2.0.** Yes — EDGE Pulse can use Graphiti in a closed-source commercial product. Apache 2.0 is permissive, includes a patent grant, and imposes no copyleft obligations beyond attribution and NOTICE preservation. The Graphiti library itself is the safe-to-embed core; the parent company Zep sells a hosted/governed variant but that is a separate commercial offering, not a license entanglement.

## Maturity signal
- Last commit date: 2026-05-14 (very recent, active development)
- Stars (if external repo): Not pulled in this session; the repo carries Trendshift and Discord badges suggesting strong traction. File this as an open question if a precise number matters for the senior-dev review.
- Open issues count (if available): Not pulled in this session.
- Published papers / notable adopters: **Yes** — arXiv 2501.13956 *"Zep: A Temporal Knowledge Graph Architecture for Agent Memory"* (Jan 2025). Zep markets it as state-of-the-art agent memory. MCP server published for Claude/Cursor.
- Subjective maturity: **Production-ready** for the memory-layer use case. Multiple drivers, structured-output requirements documented, OTel tracing, Make-based dev workflow, integration tests, ruff/pyright enforced.

## Data model / schema
Core entities are deliberately minimal so users layer their own ontology on top:
- **Episode** — a raw input event (a chat turn, a document, a JSON blob). Provenance for every derived fact.
- **EntityNode** — a person, company, concept, etc. with a *summary* that evolves as new episodes arrive.
- **EntityEdge** — a typed relationship between two entity nodes, carrying:
  - `fact` (natural-language statement, e.g. *"Kendra prefers Adidas"*)
  - `valid_at` / `invalid_at` (bi-temporal — when the fact is true in the world)
  - `created_at` / `expired_at` (system-recorded — when we learned it / when it was superseded)
  - `episodes` (provenance back to source data)
- **Community** — clusters of related nodes for higher-level retrieval.
- **Custom types** — both entities and edges can be subclassed via Pydantic models, giving prescribed ontology *or* learned ontology *or* a hybrid.

## Architectural patterns worth stealing
- **Bi-temporal model with explicit expire/supersede semantics.** Edges have both world-time and system-time, and superseded edges are not deleted — they are *expired*, so historical queries (`"what did we believe about X on date D?"`) are first-class. See `graphiti_core/edges.py` and `graphiti_core/utils/maintenance/`.
- **Episode-as-provenance discipline.** Every derived fact traces back to one or more episodes. This is exactly the "audit trail per agent assertion" property the standing rules in PM_CONTEXT §6 demand.
- **Driver abstraction over multiple graph stores.** A single `Driver` interface (Neo4j / FalkorDB / Kuzu / Neptune) means we can start with Kuzu (embedded, zero-ops, Apache 2.0) for Phase 1 and migrate to Neo4j or Neptune later without touching application code. See `graphiti_core/driver/driver.py`.
- **Hybrid search recipes.** `search_config_recipes.py` provides named retrieval strategies (semantic-only, BM25, graph-traversal, cross-encoder rerank, combinations). Pulse's "give the agent context about Account X" call can choose a recipe rather than re-implement.
- **Prompt library separated from logic.** `graphiti_core/prompts/` keeps entity extraction, deduplication, summarization, edge invalidation prompts as named, versioned modules — easy to swap models and to golden-trace test.
- **Cross-encoder rerank step** as a discrete component (`graphiti_core/cross_encoder/`). Useful pattern for any retrieval surface in Pulse.
- **Namespaces** (`graphiti_core/namespaces/`) — multi-tenant isolation at the graph layer. Maps cleanly onto Pulse's per-RM / per-account isolation needs.

## Specific code modules to reference later
- `graphiti_core/graphiti.py` — main orchestrator class; how `add_episode` flows into extraction + dedup + edge invalidation.
- `graphiti_core/edges.py`, `graphiti_core/nodes.py` — bi-temporal edge model.
- `graphiti_core/utils/maintenance/` — edge invalidation, deduplication, community-building logic.
- `graphiti_core/search/search.py` and `search_config_recipes.py` — hybrid retrieval and named recipes.
- `graphiti_core/driver/kuzu_driver.py` — embedded backend; relevant for Phase 1 fast-stack-first.
- `graphiti_core/prompts/` — prompt structure for extraction/dedup/summarization.
- `mcp_server/graphiti_mcp_server.py` — MCP-exposed memory surface; if Pulse ever needs to expose memory to other AI tools internally, this is the pattern.
- `server/graph_service/main.py` — FastAPI wrapping pattern.

## What we explicitly are NOT taking from this
- **Zep's hosted/governed surface.** That's a paid commercial product, not the OSS library. Pulse owns its own governance layer.
- **Direct MCP exposure to end users.** Per the white-label rule, no MCP surface is shown to RMs. MCP may be useful internally for Claude Code or for cross-agent orchestration, but never as a user-facing feature.
- **Neo4j Enterprise features** (parallel runtime, advanced security). Stick to the Community edition or to Kuzu for Phase 1 to avoid license surprises. Re-evaluate at AWS migration.
- **Examples and demos that hardcode OpenAI.** We need provider-agnostic config so we can route between Claude (primary) and others; Graphiti supports this but examples lean OpenAI.

## Relevance to EDGE Pulse
**Extremely high — Graphiti is the load-bearing element of Pulse's memory layer.** It maps directly onto the Temporal Context Graph internal name (PM_CONTEXT §11 glossary). The Episode model fits Pulse's signal-ingestion contract one-to-one: every Zoom call, Chorus transcript, Salesforce update, and Slack thread becomes an episode, and Graphiti handles entity extraction, edge invalidation as facts change, and provenance back to the raw signal. The bi-temporal model is the technically-credible answer to the Senior Developer's "how do you know what was true last quarter?" question. The custom-types facility lets us layer EDGE-specific entities (Customer, Talent, RM, Case, Placement) and edges (placed_at, manages, raised_about, churned_to) without forking the library. Pulse's value comes from what we *put into* the graph and what we *do with* the graph; Graphiti is the engine, not the product.

## Open questions raised by this repo
- **Backend choice for Phase 1.** PM_CONTEXT says Kuzu; this should be validated end-to-end with realistic episode volumes (≈ 530 customers × 12 months × multiple signals/customer/week = thousands of episodes/year per RM). Kuzu is embedded and Apache 2.0 but less battle-tested than Neo4j.
- **Custom ontology shape.** Need a Design-phase artifact mapping EDGE entities/edges to Graphiti's custom-types contract. Filed for Phase 2.
- **PHI in episodes.** Healthcare Zoom transcripts may carry PHI. Graphiti stores episode text raw; we need a redaction-or-encryption strategy before any episode containing call audio/transcript text is ingested. Filed in `99_open_questions.md`.
- **Cost of LLM-driven entity extraction at scale.** Every episode triggers extraction + dedup LLM calls. Need a per-RM monthly TCO estimate against the $75–150 budget posture.

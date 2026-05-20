# Findings: SDRbot-main

## What it is
An open-source CLI agent for Revenue Operations (RevOps) and SDRs, maintained by NForce.ai (sdr.bot). Built on **LangChain + DeepAgents** with **LangGraph** for multi-step planning. Distinguishing feature: **Schema Sync** — at install/sync time it introspects the user's CRM and generates strongly-typed Python tool definitions that match the exact field names and types, including custom objects. Supports Salesforce, HubSpot, Zoho, Pipedrive, Attio, Twenty, plus prospecting integrations (Apollo, Lusha, Hunter, Tavily), email channels (Gmail/Outlook/IMAP/SMTP), and direct database access (Postgres/MySQL/MongoDB). Features Safe Mode (write operations require permission), Plan Review (TODO list before complex tasks), Shell Allow-List (read-only shell commands auto-approved), Headless Mode (cron/CI usage), Session Persistence (SQLite-backed conversation resume), MCP support, and observability hooks (LangSmith, Langfuse, Opik).

## License
**MIT.** Yes — EDGE Pulse can use, fork, embed, and redistribute under closed-source commercial terms with MIT attribution preserved. No copyleft. Vendor copyright is "sdrbot contributors" — clean enough.

## Maturity signal
- Last commit date: N/A in local copy (no `.git` present); upstream maintained by NForce.ai (sdr.bot).
- Stars (if external repo): Not pulled in this session.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: Marketed by NForce.ai; targets RevOps teams.
- Subjective maturity: **Active product, mid-maturity.** Version `0.3.3` per `pyproject.toml` — pre-1.0. Polished CLI with TUI (Textual), session persistence, observability hooks. Production-shipped but pre-1.0 means expect breaking changes. The breadth (6 CRMs + 3 enrichment vendors + 3 databases + 3 email channels + MCP + 3 observability backends) suggests configurability has been prioritized over depth.

## Data model / schema
SDRbot's data model is largely an **abstraction over the user's existing CRM schema** rather than a fixed model of its own:
- **Schema Sync** generates typed Python tool definitions from the live CRM (Salesforce SOQL describes, HubSpot v3 schema API, etc.) and stores them locally.
- **Session** — a persisted conversation thread in SQLite (`langgraph-checkpoint-sqlite`).
- **Memory** — `memory_tools.py` + `agent_memory.py` — file-based memory store with explicit memory-update commands.
- **Skills** — `sdrbot_cli/skills/builtin/` (only `crm-migration.md` ships) plus user-installable skills loaded via `skills/load.py` and `skills/middleware.py`.
- **Subagents** — `subagents/loader.py` + `migration_executor.py` — explicit subagent shape (a more constrained agent that handles a discrete task).
- **Sandbox integrations** (`integrations/`: `daytona.py`, `modal.py`, `runloop.py`, `sandbox_factory.py`) — execute generated code in remote sandboxes.

## Architectural patterns worth stealing
- **Schema Sync — generate typed CRM tools from the live schema.** This is the most important pattern in SDRbot for Pulse. Salesforce schemas are bespoke per org (custom objects, custom fields); Pulse's agent must reason about EDGE's specific `RM_Outreach__c`, `Associates__c`, `Customer_Health__c` etc. as first-class. Generating typed tool definitions at install/sync time gives the agent an unambiguous, well-typed surface and prevents prompt-engineered guesses at field names. Worth lifting the *pattern* (introspect → codegen typed tools) even if we don't lift LangChain.
- **Safe Mode + Plan Review (HITL).** Safe Mode requires permission before create/update/delete; Plan Review writes a TODO list and asks for approval before complex tasks. This is the explicit shape of **human-in-the-loop as the product**, the standing rule in PM_CONTEXT §6 product rule 3. The action queue *is* Plan Review made permanent.
- **Shell Allow-List for read-only commands.** Auto-approve safe ops, prompt for risky ones. Maps onto tier-aware approval (auto-approve low-risk actions for SMB customers, require approval for Enterprise).
- **Session persistence in SQLite.** Conversation resume across restarts via `aiosqlite` + `langgraph-checkpoint-sqlite`. Pulse's agent state needs the same survivability.
- **Headless / non-interactive mode.** Run via cron, CI, or stdin pipe (`echo "..." | sdrbot -n`). Output text or JSON. Pulse needs this shape for the daily heartbeat — the agent runs unattended each morning and posts to the action queue.
- **Subagent loader pattern.** Explicit codification of "spawn a more constrained agent for a discrete task" is cleaner than open-ended multi-agent chatter. Useful for Pulse if/when we have specialized sub-tasks (e.g., draft-email subagent, EBR-prep subagent).
- **Observability via langsmith / langfuse / opik.** Real production agent telemetry is non-negotiable for HITL audit ("no silent failure" rule). Pick one and standardize.
- **Sandbox factory for code execution.** Daytona/Modal/Runloop adapters behind a `sandbox_factory.py` interface. Overkill for Phase 1 but interesting if Pulse ever generates code (e.g., a one-off SOQL query authored on the fly).
- **System prompt and default agent prompt as separate markdown files** (`system_prompt.md`, `default_agent_prompt.md`). Prompts versioned and grep-able, not buried in Python strings.

## Specific code modules to reference later
- The Salesforce schema-sync logic (likely in `sdrbot_cli/setup/` or `sdrbot_cli/services/`) — read for the introspect→codegen pattern.
- `sdrbot_cli/skills/load.py`, `sdrbot_cli/skills/middleware.py` — runtime skill-loading.
- `sdrbot_cli/subagents/loader.py` — subagent pattern.
- `sdrbot_cli/sessions.py` + `sdrbot_cli/agent.py` — session persistence shape.
- `sdrbot_cli/non_interactive.py` — headless mode.
- `sdrbot_cli/system_prompt.md`, `sdrbot_cli/default_agent_prompt.md` — prompt structure (Memory-First Protocol, HITL approval framing, skills-directory referencing).
- `sdrbot_cli/tracing.py` — observability wiring; reference for picking one of LangSmith / Langfuse / Opik.
- `sdrbot_cli/mcp/` — MCP server hookup for Pulse if we expose MCP internally.

## What we explicitly are NOT taking from this
- **LangChain + DeepAgents + LangGraph as the Phase 1 agent runtime.** PM_CONTEXT §3 locks n8n for Phase 1 orchestration; LangGraph is a v1.5+ candidate (PM_CONTEXT §12 item 4). The patterns transfer; the framework doesn't (yet).
- **CLI/TUI as Pulse's surface.** Pulse's hero surface is the dashboard action queue.
- **The "supports 6 CRMs" breadth.** Pulse targets Salesforce only.
- **Apollo/Lusha/Hunter/Tavily as built-in enrichment vendors.** Pulse may add specific external sources; do not adopt this entire stack.
- **Sandbox factory for code execution.** Phase 1 doesn't need it.
- **Multiple observability backends.** Pick one (likely Langfuse or Claude's own tracing). Three is too many.

## Relevance to EDGE Pulse
**Medium-high — strongest contribution is the Schema Sync pattern and the explicit HITL discipline.** SDRbot is the only reference in this audit that addresses *generating typed CRM tools from a live schema* — and that is the cleanest answer to "how does the Pulse agent reliably operate against EDGE's specific Salesforce custom objects?" Lift the *pattern*: at deploy time (or scheduled), introspect Salesforce via `sf` CLI, emit typed Python (or TypeScript) tool definitions for each entity + each operation, and pass those into the agent's tool surface. Beyond Schema Sync, SDRbot's Safe Mode + Plan Review + Shell Allow-List trio is a clean encoding of human-in-the-loop discipline — the same shape Pulse needs for tiered approval. The session persistence, headless mode, and observability hooks are all directly applicable. The actual code is MIT, so we *could* lift portions, but the LangChain dependency tree pulls in much more than we want for Phase 1; lifting patterns is the smarter path.

## Open questions raised by this repo
- **Schema Sync cadence.** Salesforce schemas change occasionally; how often should Pulse re-sync and re-codegen the typed tools? On every deploy? Nightly? On webhook? Filed for Phase 2.
- **Observability backend choice.** LangSmith, Langfuse, Opik, or a Claude-native option? Decision needs to be made before Phase 4 because instrumentation must be there from commit one. Filed for Phase 2.
- **MCP exposure inside Pulse.** Pulse's agent could call EDGE-Salesforce tools via MCP rather than direct Python. Decouples agent framework from data layer (same idea raised in `relaticle.md`). Filed for Phase 2.
- **DeepAgents / LangGraph migration timing.** When does Pulse outgrow n8n? Filed for v1.5+.
- **Subagents pattern adoption.** Worth Phase 2 design discussion: do we have *specialized* sub-tasks that warrant a subagent abstraction, or is one supervisor agent + skill files enough? Filed for Phase 2.

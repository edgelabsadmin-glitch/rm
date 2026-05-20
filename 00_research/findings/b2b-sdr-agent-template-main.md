# Findings: b2b-sdr-agent-template-main

## What it is
A prior-work template (forked locally into ai-rm) for an open-source AI SDR built on the "OpenClaw" / "Hermes" agent runtimes. Its hallmark is a **7-layer Markdown context system** — `IDENTITY.md`, `SOUL.md`, `AGENTS.md`, `USER.md`, `HEARTBEAT.md`, `MEMORY.md`, `TOOLS.md` — each a discrete file that the AI reads on every conversation to assemble persona, sales pipeline, owner ICP, daily inspection rules, multi-layer memory protocol, and tool catalog. Ships with a `skills/` directory (`chroma-memory`, `delivery-queue`, `graphify`, `lead-discovery`, `quotation-generator`, `sdr-humanizer`, `supermemory`, `telegram-toolkit`), a `product-kb/` catalog, an `install.sh` deployer, and Markdown READMEs in 8 languages. The README brands the project as "PulseAgent B2B SDR Agent Skill" — note the naming overlap with EDGE Pulse, addressed below.

## License
**MIT.** Yes — EDGE Pulse can reuse, modify, and embed this template's content under closed-source commercial terms with standard MIT attribution preserved in source files. No copyleft.

## Maturity signal
- Last commit date: Locally extracted April 25 2026; upstream actively maintained (README references DeepSeek V4 catalog from 2026-04-24).
- Stars (if external repo): Not pulled; promoted on Product Hunt.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: Live on Product Hunt; multilingual community.
- Subjective maturity: **Active template, not a system.** This is a *starter kit* for building SDR agents on the OpenClaw runtime, not a self-contained product. The content (the 7 Markdown files + memory protocol) is the deliverable; the surrounding code is glue.

## Data model / schema
The template encodes context as Markdown files rather than as a typed schema:
- **IDENTITY.md** — who the agent is, company info, role.
- **SOUL.md** — personality, values, conversation rules.
- **AGENTS.md** — the full sales workflow (10 stages).
- **USER.md** — the human owner's profile, ICP, scoring rules.
- **HEARTBEAT.md** — daily inspection routines (13 items: new leads, stalled leads, quote tracking, meetings, nurture, data quality, email sequence, lead discovery, etc.).
- **MEMORY.md** — the 4-layer memory operating protocol:
  - **L0**: optional Active Memory sub-agent (recent/full/message modes)
  - **L1**: MemOS structured memory (auto-injection at conversation start)
  - **L2**: dual-threshold proactive summary (50% background save, 65% full compression)
  - **L3**: ChromaDB per-turn store with customer-id isolation and recency-weighted ranking
  - **L4**: daily CRM snapshot fallback
  - Plus an explicit fallback chain when each layer is unavailable
- **TOOLS.md** — CRM, channels, integration catalog.

PM_CONTEXT memory `feedback_only_adopt_context_split` already locks the decision: **take the per-profile Markdown context-split pattern; drop the rest.**

## Architectural patterns worth stealing
- **Per-profile Markdown context layers.** This is the one pattern PM_CONTEXT has already explicitly endorsed for adoption (the `feedback_only_adopt_context_split` memory). Pulse's "context priming layer" (per-Account / per-Associate / per-RM profiles) maps onto exactly this idea: a Markdown layer per entity that lives alongside the structured graph and gets read into the agent's context window when reasoning about that entity. This pattern is the most direct architectural lift in the audit.
- **Memory layer fallback chain.** The L0–L4 cascade with explicit per-layer fallback behavior is good operational design. Pulse's analogue: Graphiti as primary, with a defined fallback if Graphiti is unavailable (e.g., "read directly from Salesforce + degrade gracefully on a banner"). Adopt the *discipline of naming the fallback*, not the specific L0–L4 layers.
- **HEARTBEAT-style daily inspection.** A small set of named, scheduled checks the agent runs without prompting. Maps onto Pulse's proactive proposed-action generation (every morning the agent scans the book of business and posts proposed actions to the queue).
- **Skills as named subdirectories under `skills/`.** Matches customer-success-skills's pattern but at the implementation level (each skill is a folder with its own logic), not just Markdown. Worth considering when Pulse's skill library matures into Phase 2.
- **`product-kb/catalog.json` as the agent's product knowledge base.** Maps onto Pulse's need for an EDGE-role-catalog that the agent reasons against (the same catalog that `opportunity-tracker/config/role-catalog.json` defines).

## Specific code modules to reference later
- `workspace/IDENTITY.md`, `SOUL.md`, `AGENTS.md`, `USER.md`, `HEARTBEAT.md`, `MEMORY.md`, `TOOLS.md` — read all seven once. They are the lifted assets.
- `workspace/MEMORY.md` specifically — the fallback-chain documentation pattern is worth replicating in Pulse's design doc.
- `workspace/HEARTBEAT.md` — the daily-inspection rhythm.
- `skills/lead-discovery/`, `skills/delivery-queue/` — read for shape of an OpenClaw skill.
- `ANTI-AMNESIA.md` — the project's own meta-discipline about not losing context; reference for our PM_CONTEXT-style discipline.

## What we explicitly are NOT taking from this
- **The OpenClaw / Hermes runtimes.** Pulse is not running on OpenClaw. The Markdown context layers are runtime-agnostic; the runtime itself is not adopted.
- **WhatsApp / Telegram / Email channel surface.** Pulse's channel is the dashboard and the action queue, not consumer messaging.
- **The Product Hunt branding "PulseAgent."** Naming overlap with EDGE Pulse is coincidental and irrelevant; we own "EDGE Pulse" internally and do not need to disambiguate.
- **DeepSeek V4 / other LLM provider lock-in.** Pulse uses Claude as primary per PM_CONTEXT.
- **ChromaDB / MemOS / Supermemory as the memory engines.** Pulse's memory engine is Graphiti (locked). The *layered cascade idea* transfers; the specific engines do not.
- **The "10-stage sales workflow" content.** Pulse is an RM intelligence layer, not an SDR. Different lifecycle, different workflow.

## Relevance to EDGE Pulse
**Medium-high — concentrated in one pattern.** PM_CONTEXT already named the lift target: per-profile Markdown context layers (the `feedback_only_adopt_context_split` memory). This finding confirms the pattern is real, well-developed in the template, and easy to port. The fallback-chain discipline in MEMORY.md is a good second pattern to adopt at the architecture level. The HEARTBEAT cadence pattern is a useful third — Pulse's "every morning the agent reviews the book of business" loop can be sketched as a HEARTBEAT-style file. Everything else (runtime, channels, memory engines, SDR workflow) is project-specific and not adopted.

## Open questions raised by this repo
- **Where do the Markdown context layers live in Pulse's architecture?** Same git repo as the agent code (versioned)? Separate content repo? Backing a CMS surface for RM-facing edits? Filed for Phase 2.
- **Per-entity granularity.** PM_CONTEXT says per-Account / per-Associate / per-RM profiles. Should there also be per-Customer-pair Markdown (e.g., one file for an Account+Talent placement)? Probably no for Phase 1. Filed for Phase 2.
- **Update cadence for context Markdown files.** If profiles are static text and the underlying data changes hourly, the Markdown layers stale. Need a sync strategy (regenerate on signal, generate on read, edit-then-pin?). Filed for Phase 2.
- **Authoring tool for the Markdown layers.** Hand-authored, agent-authored on first ingestion, or hybrid? Filed for Phase 2.

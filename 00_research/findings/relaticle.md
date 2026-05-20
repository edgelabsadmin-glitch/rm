# Findings: relaticle

## What it is
Relaticle is a self-hosted, "open-source CRM built for AI agents" — a Laravel 12 + Filament 5 + Livewire 4 + PHP 8.4 application whose differentiating feature is a **production-grade MCP (Model Context Protocol) server with 30 tools** that any AI agent (Claude, GPT, open-source) can call to perform CRM operations. Other notable features: 22 custom field types including entity relationships and per-field encryption, a REST API with full CRUD and schema discovery, 5-layer authorization with team-scoped data and workspaces, PostgreSQL-exclusive, 1,100+ automated tests, and Filament admin panels for CRUD UIs.

## License
**GNU AGPL v3.** **No — not usable for code embedding in EDGE Pulse as a closed-source commercial product.** Same constraint as Twenty: AGPL's network-use clause forces source disclosure on any networked derivative work. Self-hosting Relaticle internally would be permitted, but Pulse cannot lift its code, schemas, or migrations.

## Maturity signal
- Last commit date: 2026-05-15 (extremely active, just days before this audit).
- Stars (if external repo): Not pulled in this session.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: Marketed as "production code for a commercial SaaS product with paying customers" in CLAUDE.md.
- Subjective maturity: **Production-ready.** The CLAUDE.md describes a serious quality bar (PHPStan analysis, 99.9% type coverage, Rector for refactoring, Pint for style, Pest for tests, mutation testing tool). The "Actions" pattern (all writes go through action classes) is mature DDD discipline.

## Data model / schema
- **Companies, Contacts, Opportunities** as core entities (standard CRM trio).
- **Custom fields** layered via a trait (`UsesCustomFields`) — 22 field types, including entity-relationship fields and conditional-visibility fields. Custom-field values are tenant-scoped.
- **Multi-tenant** via team-scoped data and workspaces; tenant context set by middleware (`SetApiTeamContext`).
- **Authorization** is described as "5-layer" — likely Laravel Gates + Policies + tenant scope + custom-field visibility + workspace scope. Worth a deeper read in Phase 2 if needed.

## Architectural patterns worth stealing
- **MCP server as a CRM access layer.** Relaticle exposes 30 MCP tools that match its CRM operations — `search_companies`, `create_contact`, `update_opportunity`, etc. **This is directly relevant** to Pulse: if Pulse's agents are to operate against Salesforce, an MCP-style typed-tool layer is the cleanest abstraction. Pulse can build the same shape against Salesforce instead of against its own DB.
- **Actions as single source of truth for write operations.** "All write operations (create, update, delete) must go through action classes in `app/Actions/` — never inline business logic in controllers, MCP tools, Livewire components, or Filament resources." This is the exact pattern the action queue needs: every action the agent proposes maps onto a named Action class with auditable inputs/outputs and side effects.
- **Tenant-context middleware.** Tenant ID is set once in middleware and ambient to all downstream calls. Maps onto Pulse's RM-scoped data model (each RM sees their book of business, plus the Overall view per PM_CONTEXT memory).
- **`UsesCustomFields` trait.** A field-layer extension mechanism that auto-merges custom fields into the model and persists them via `saved` events. Strong pattern for Pulse if we ever need to mirror Salesforce custom fields without per-field migrations.
- **Mutation testing as code-review tool, not CI gate** — pragmatic stance worth adopting.
- **Pint + Rector + PHPStan + type-coverage gates** — the equivalent stack in TypeScript would be ESLint + ts-prune + tsc strict + type-coverage. Worth replicating the *discipline*.

## Specific code modules to reference later
- `app/Mcp/` or wherever the 30 MCP tools live — read the *shape* of an MCP-tool definition that maps onto a CRM action. Pulse can mirror this against Salesforce.
- `app/Actions/` — the action-class pattern; map onto Pulse's proposed-action contract.
- `app/Models/` with the `UsesCustomFields` trait — the custom-fields persistence pattern.
- `app/Http/Middleware/SetApiTeamContext.php` — ambient tenant context middleware.
- `CLAUDE.md` itself — surprisingly useful prose on the project's quality discipline.

## What we explicitly are NOT taking from this
- **Any source code.** AGPL.
- **Laravel/PHP as Pulse's stack.** EDGE's engineering culture (and the rest of our references) points toward Python + TypeScript. Adopt patterns, not the language.
- **Filament admin panels.** Beautiful but PHP-tied. We will use a TypeScript/React surface aligned to Linear + Granola.
- **Per-field encryption** as a baseline — overkill for Phase 1. Field-level encryption is a Phase 2+ HIPAA hardening item.
- **Their MCP tool surface verbatim** — Pulse's MCP tools (if exposed) would target Salesforce operations, not Relaticle CRM operations.

## Relevance to EDGE Pulse
**Medium-high as a pattern donor, low as a code donor.** The single most relevant idea is **the MCP-tools-as-CRM-access pattern**: a typed, named, auditable surface that the agent calls to perform operations. Pulse's action queue is the *human-facing* analogue, and an MCP-tool layer is the *agent-facing* analogue. The Actions pattern (all writes through named Action classes) is a clean way to enforce auditability — every proposed action is an Action instance with a known shape, every approved action runs the same Action with logging and reversibility. The custom-fields trait is interesting if Pulse ever needs to mirror Salesforce schema dynamically. Beyond those, the language mismatch (PHP) and AGPL license cap Relaticle's direct contribution to Pulse.

## Open questions raised by this repo
- **MCP as an internal interface for Pulse's own agents.** Should Pulse expose its Salesforce-operation tools via MCP so that the agent layer (whether Claude API direct, Claude Agent SDK, LangGraph, etc.) calls a uniform interface? This would decouple agent framework from data layer. Filed for Phase 2.
- **Should Pulse have "Actions" as a named code primitive?** PM_CONTEXT §11 glossary already names "Action Queue" as the hero UI surface — extending that to an Action class on the backend that owns approve/reject/execute lifecycle seems natural. Filed for Phase 2.
- **Per-field encryption for PHI fields.** Not Phase 1, but worth knowing it's a pattern others have implemented when we revisit HIPAA hardening. Filed for v1.5+.

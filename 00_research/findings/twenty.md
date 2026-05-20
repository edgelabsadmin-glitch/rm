# Findings: twenty

## What it is
Twenty is the leading open-source CRM, positioned as a "build, ship, version" CRM for technical teams who want to define objects, fields, views, workflows, and agents *as code*. The stack is a polished monorepo: React 18 + Jotai + Linaria frontend, NestJS + TypeORM + PostgreSQL + Redis + GraphQL (code-first) backend, BullMQ for jobs, Nx for workspace management, Yarn 4, Playwright E2E. It supports both cloud (twenty.com) and self-hosting (Docker Compose) and has a TypeScript SDK (`twenty-sdk/define`) for declaring objects/views/agents in code. There is an `agents` first-class concept inside the product itself.

## License
**GNU AGPL v3, with some files under a separate Commercial License (marked `/* @license Enterprise */`).** **No — not usable for code embedding in EDGE Pulse as a closed-source commercial product.** AGPL is the strongest copyleft: any networked use that exposes derived work over a network triggers the obligation to make source available under AGPL. Embedding any Twenty source — even server-side, even unmodified — would force Pulse to be AGPL-licensed (or pursue a separate commercial license from Twenty). **Conditional alternative:** Pulse may install a self-hosted Twenty instance as a *standalone* internal tool for the RM team to use *separately*, since use without distribution is permitted; but we may not lift code, schemas, or templates into Pulse.

## Maturity signal
- Last commit date: 2026-05-19 (literally hours before this audit — extremely active).
- Stars (if external repo): Not pulled in this session, but Twenty is widely known to be in the tens of thousands of stars range based on README badges.
- Open issues count (if available): Not pulled; project tracks roadmap publicly on GitHub Projects.
- Published papers / notable adopters: Commercial backing via twenty.com hosted offering; venture-funded (publicly known).
- Subjective maturity: **Production-ready and actively shipped.** The CLAUDE.md alone reveals a serious engineering culture (Jotai, Linaria zero-runtime CSS-in-JS, strict TypeScript, Nx incremental tooling, code-first GraphQL with codegen, instance/workspace migration distinction). Among the references in this audit it is the most production-grade CRM.

## Data model / schema
- **Workspaces, Users, Members, Objects, Fields, Views** as core metadata.
- **Custom objects and fields at runtime** — users define their own schema via UI or the `twenty-sdk/define` API; metadata tables drive GraphQL schema generation.
- **Three Postgres schemas:** `core` (cross-workspace shared), `metadata` (object/field definitions), and per-workspace schemas (the workspace's own data).
- **Background jobs via BullMQ.**
- **Agents** as first-class objects inside the platform.

## Architectural patterns worth stealing
- **Metadata-driven dynamic schemas.** Users define objects/fields in the app; the GraphQL schema is generated from the metadata layer. This is the cleanest pattern in the references for a CRM that must *adapt* to a customer's specific schema (relevant to EDGE because Salesforce schemas are bespoke per org, and Pulse needs to reflect that without code changes).
- **Instance commands vs. workspace commands** for migrations. Instance commands run once at the database level; workspace commands iterate across each tenant's schema. This is the right pattern for any multi-tenant CRM-shaped product and worth stealing if Pulse ever multi-tenants.
- **Code-first GraphQL.** Schema is generated from TypeScript decorators on entities; the frontend codegens types from the GraphQL schema. Loops the type system end-to-end, which matters for a Senior-Dev review.
- **Linaria for zero-runtime CSS-in-JS.** Strong design-system pattern compatible with the Linear/Granola aesthetic locked in PM_CONTEXT §6 design rule 13.
- **`isDefined()` / `isNonEmptyString()` / `isNonEmptyArray()` utilities** in `twenty-shared` — small but high-signal example of a serious codebase's quality discipline.
- **Diff-with-main linting** (`lint:diff-with-main`) for fast PR-scoped checks. Worth adopting in Pulse's build pipeline.

## Specific code modules to reference later
- `packages/twenty-server/src/engine/metadata/` — metadata-driven schema modules (path approximate; verify in Phase 2).
- `packages/twenty-front/src/modules/` — feature-module organization in the React app; reference for our own modular feature layout.
- `packages/twenty-shared/src/` — shared utilities and types; reference for `isDefined` and friends.
- The agent feature inside Twenty (location to be confirmed) — read for *shape*, not for adoption.
- `nx.json` and the Nx task graph — reference if Pulse goes Nx (likely if we standardize on TypeScript monorepo).

## What we explicitly are NOT taking from this
- **Any source code in Pulse's binary.** AGPL forecloses it.
- **The "users define their own objects" UI surface.** Pulse's RM users are not configuring a CRM; Salesforce *is* the CRM. We define Pulse's domain model ourselves.
- **NestJS as a hard requirement.** It's a reasonable choice, but n8n + a lighter API layer is likely sufficient for Phase 1.
- **GraphQL as a hard requirement.** Pulse's API surface is small in Phase 1; REST/tRPC is fine. Revisit if we ever expose a public extensibility API.
- **Twenty's design language verbatim.** Twenty is good-looking but Pulse's design lock is Linear + Granola (PM_CONTEXT §6 design rule 13). Adopt Twenty's *engineering quality bar*, not its visual identity.

## Relevance to EDGE Pulse
**Medium — high as an architectural quality bar, zero as a code source.** Twenty is the highest-quality CRM in the reference set and the best example of *how a modern CRM should be engineered* (metadata-driven, code-first GraphQL, strict TypeScript, monorepo with Nx, BullMQ for jobs). It also explicitly has an "agents" concept inside the product, which is worth studying as a UX precedent for surfacing agents to operators. **But the AGPL license bars us from copying code**, and Pulse's product surface is fundamentally different: Pulse is an *intelligence and action layer on top of* Salesforce, not a CRM that replaces Salesforce. The right use of Twenty here is: read the engineering, read the agents UX, adopt the discipline; do not import or fork.

## Open questions raised by this repo
- **Should Pulse expose any "build your own object" customization to admins?** Probably no for Phase 1 (PM_CONTEXT is clear that scope must be ruthless). But the question is worth raising at the v2 horizon — power users at EDGE may want to extend Pulse's domain model. Filed for v1.5+ candidates.
- **GraphQL vs. REST for Pulse's internal API surface.** Twenty's code-first GraphQL is appealing but heavy. Pulse Phase 1 likely doesn't need GraphQL. Filed for Phase 2 design.
- **Monorepo vs. single-package layout for Pulse.** Nx is a long-term commitment. Phase 1 likely starts single-package. Filed for Phase 2.

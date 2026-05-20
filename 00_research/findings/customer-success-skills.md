# Findings: customer-success-skills

## What it is
An "open-core skill library for agentic customer success operations" — a curated repository of ~45+ Markdown-encoded "skills" (executable playbooks readable by both humans and autonomous AI agents) organized by CS lifecycle stage. Categories include: 01-technical, 02-onboarding, 03-alignment, 04-adoption, 05-expansion, 06-churn, 07-operations. Each skill is a stand-alone Markdown file describing trigger conditions, inputs, execution logic, guardrails, and expected outcomes. The repo also ships a small React/Vite web portal for browsing the skills, a `SKILLS_REGISTRY.json` index, and example metadata.

## License
**REPlexus Community License v1.0 (custom).** **Conditional.** Permits (a) personal/educational use and (b) "internal business operations — implement and execute these skills within your own organization to manage your own customers and revenue." **Prohibits** (a) "commercial consulting services" / MSP offerings, (b) packaging the skills into a "competing software product, paid training course, or membership site." Requires (c) share-alike on modifications and (d) attribution to Josh Rosenthal / REPlexus. Also explicitly permits AI ingestion provided author/organization metadata is preserved and cited in generated outputs.

**Assessment for Pulse:**
- *Internal use of the framework's ideas to inform our own skill library* — clearly permitted.
- *Bundling these Markdown files verbatim into Pulse's binary or repo* — borderline; "internal business operations" arguably covers it if Pulse is EDGE-internal, but the "competing software product" prohibition is the live risk if Pulse is ever offered as SaaS to other staffing firms or if it embeds the skills as user-visible content.
- *Reading the skills, learning the structure, and writing our own under EDGE's own attribution* — clearly permitted and recommended.

**Path: treat as inspiration, write our own.** Do not commit these files into Pulse's repo as production assets.

## Maturity signal
- Last commit date: 2026-05-13 (recent).
- Stars (if external repo): Not pulled in this session.
- Open issues count (if available): Not pulled.
- Published papers / notable adopters: Authored by Josh Rosenthal on behalf of REPlexus. No major adopter signals.
- Subjective maturity: **Experimental / curated content library.** The value is the *content* and the *format*, not the code. The React portal is a thin wrapper. Active but small.

## Data model / schema
- **Skill** — a single Markdown file. Naming convention: `NNN-kebab-name.md` (e.g., `038-gbm-prediction.md`, `041-crisis-de-escalation.md`).
- Folder structure encodes lifecycle stage: `01-technical`, `02-onboarding`, `03-alignment`, `04-adoption`, `05-expansion`, `06-churn`, `07-operations`.
- `SKILLS_REGISTRY.json` indexes the skills with metadata (likely title, category, author, version — to confirm by reading).
- `metadata.json` and `config/` provide template / category configuration.
- Each skill file (per the Pillars described in the README) covers: outcome intent, data sources (CRM, support, email, call transcripts, usage), prediction logic, value receipts (ROI evidence).

## Architectural patterns worth stealing
- **Skills as Markdown files indexed by a registry.** This is *exactly* the pattern Anthropic uses for Claude Code Skills and is consistent with the b2b-sdr-agent-template's `skills/` folder pattern. Pulse's internal agent can carry its own per-lifecycle skill library: *churn de-escalation*, *expansion ask*, *EBR prep*, *placement check-in*, etc. Each is a Markdown file with named sections (trigger, inputs, logic, guardrails, output) — readable by humans, ingestible by agents.
- **Lifecycle-staged organization.** Onboarding → Alignment → Adoption → Expansion → Churn maps cleanly onto Pulse's customer lifecycle. Lets us scope Phase 1 to a small subset (probably adoption + churn + expansion) and add stages later.
- **"Outcome Intent" as a first-class skill section.** Each skill explicitly captures what the customer wants to achieve. Pulse's per-account record should carry an "outcome intent" field — what does *this customer* want from EDGE in the next 6 months — as input to all proposed actions.
- **"Value Receipts" pattern.** Automate the evidence of ROI per action. Maps onto Pulse's after-action follow-up loop: after an action is approved and executed, the system captures the outcome and credits the agent.
- **Filename-numbered skills** (`042-human-save-play.md`) — gives a deterministic ordering and natural skill IDs for reference. Cheap and useful.

## Specific code modules to reference later
- `skills-library/06-churn/038-gbm-prediction.md`, `039-auto-remediation.md`, `041-crisis-de-escalation.md`, `042-human-save-play.md` — read these for *content shape* before designing Pulse's own churn-skill set.
- `skills-library/05-expansion/` — read for expansion-signal playbook design.
- `skills-library/04-adoption/` — `030-early-disengagement.md` is exactly the silent-churn-signal use case in Pulse's PM_CONTEXT.
- `skills-library/02-onboarding/` — relevant once Pulse handles new placement intake (Phase 2+).
- `SKILLS_REGISTRY.json` — registry shape; mimic with our own EDGE-attributed registry.
- `src/types.ts`, `src/template.md` — skill type definitions and authoring template.

## What we explicitly are NOT taking from this
- **The Markdown files themselves, committed verbatim into Pulse's repo.** License + white-label considerations. Write our own under EDGE attribution.
- **The React/Vite portal.** Pulse's UI is the action queue and dashboard, not a skill browser. Skill files are internal artifacts.
- **The REPlexus brand and attribution.** Our skills are EDGE-attributed and white-labeled.
- **Generic CS playbooks that don't fit a staffing-firm context.** Many skills (e.g., "Maturity Rolodex", "Stack Consolidation") are designed for SaaS CS, not for talent placement.
- **AI Companion / generic LLM advice that lacks operational specifics.** Use only the structural pattern, not the prose.

## Relevance to EDGE Pulse
**Medium — important for skill-library *structure*, less so for *content*.** The biggest contribution is validating that "skills as Markdown files in a numbered, lifecycle-staged library" is a workable shape for codifying RM playbooks. Pulse's agent in Phase 1 will need ~10–20 such skills (e.g., *detect-quiet-customer*, *propose-EBR-prep*, *draft-expansion-ask*, *crisis-de-escalation-on-replacement*) and this repo confirms the format. The *content* of these skills must be EDGE-specific because we're staffing, not SaaS — but the *lifecycle stages* (onboarding/adoption/expansion/churn) and the *section schema* (trigger/inputs/logic/guardrails/output) port cleanly. The license is the binding constraint: read, learn, then write our own.

## Open questions raised by this repo
- **Who authors Pulse's skill library?** PM, Senior Dev, VP Client Success, RMs, or a hybrid? Phase 2 design needs to set this. The b2b-sdr template suggests the *system designer* authors them; the CS-skills repo suggests a CS practitioner authors them. EDGE Pulse will likely need RM input on triggers and guardrails. Filed for Phase 2.
- **Are skills versioned per customer tier?** A Hottest-customer churn-de-escalation skill should differ from a low-touch SMB version. Tier-aware skill variants are worth a design decision. Filed for Phase 2.
- **Skill-attribution surface.** Even internally, we'll want to know which skill drove which proposed action — for explainability and for iterating on skills. Maps onto the "reasoning capture" thread elsewhere in this synthesis. Filed for Phase 2.

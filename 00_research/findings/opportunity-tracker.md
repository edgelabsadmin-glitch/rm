# Findings: opportunity-tracker

## What it is
EDGE's existing internal "Opportunity Tracker" Python application. It scans **585 active Salesforce accounts daily** across LinkedIn / Indeed / Glassdoor / Google Jobs and each client's own career page (supports Greenhouse, Lever, generic HTML scrapers), fuzzy-matches every job posting against EDGE's 53-role catalog (across Insurance, Medical, Dental verticals), tags each match (Hottest / Warm / General), tracks new vs. seen state in SQLite to suppress duplicate alerts, sends branded email notifications, optionally writes Salesforce tasks, and exposes a Streamlit + Plotly dashboard with filtering, search, analytics, and per-account drill-down. There is also an `ai_matcher.py` that augments the deterministic matcher with LLM judgment for ambiguous cases.

## License
**No LICENSE file in the folder — internal EDGE code.** Yes — EDGE owns it and can reuse/refactor freely. Per PM_CONTEXT (`project_opportunity_tracker` memory) Opportunity Tracker is already committed as Pulse's job-posting-signal source for v1.

## Maturity signal
- Last commit date: N/A (no `.git`). Filesystem timestamps indicate active maintenance through April 2026.
- Stars / issues: N/A.
- Published papers / notable adopters: N/A; in active production use by the EDGE sales team.
- Subjective maturity: **Production-grade for its scope.** Built by EdgeLabs, working against real Salesforce data, real email notifications, real scrapers. Bigger surface than rm-intelligence-agent. Has a deployable Streamlit dashboard with authentication. Solid as a feeder system; not architected to be a *library* for other EDGE projects.

## Data model / schema
- **Account** — from `data/accounts.json`, mirrored from Salesforce (Id, Name, industry, Owner, etc.). 585 records.
- **Role catalog** — `config/role-catalog.json` — 53 roles across 3 industries (Insurance, Medical, Dental). Each role has aliases, keywords, and tier metadata.
- **Job posting** — scraped or API-fetched per board. Fields: title, company, location, url, source, date_posted, raw description.
- **Match** — `(posting, role, tier, confidence, matched_keywords)` tuple. Tiers: `Hottest`, `Warm`, `General`.
- **State** — SQLite table tracking which (account, posting_url) pairs have been seen, when, what tier, whether notified.
- **Notification log** — per-email send record.
- **SF tasks** — optional Salesforce task creation tied to matches.

## Architectural patterns worth stealing
- **Externalized role catalog as JSON.** `config/role-catalog.json` is editable by non-engineers, drives matching, and decouples the catalog from code. Pulse's "what roles does EDGE staff" knowledge should live here and be referenced by Pulse's agent.
- **Tiered match output (Hottest / Warm / General).** A 3-tier confidence taxonomy is the right shape for any signal-quality output Pulse produces. Maps naturally onto Pulse's churn/expansion/replacement signals.
- **Hybrid deterministic + LLM matcher.** `matcher.py` (fuzzy) + `ai_matcher.py` (LLM judgment for ambiguous cases) is the right cost-quality split. Cheap matchers first, LLM only when needed. Same pattern from rm-intelligence-agent.
- **SQLite state for new-vs-seen suppression.** Lightweight idempotency layer that prevents alert fatigue. Pulse's action queue needs the same: don't propose the same action twice within a window. Reuse the pattern.
- **ATS-specific scrapers behind a common interface** (`scanners/ats_scrapers/`: Greenhouse, Lever, generic HTML). The clean adapter shape is reusable for any "many integrations behind one interface" need in Pulse.
- **Streamlit + Plotly for the analytics dashboard.** Faster to build than React for internal analytics. Pulse's hero surface is React/TS (action queue, design lock), but a Streamlit-style admin/analytics surface might still serve the VP of Client Success well during demos.
- **Per-account drill-down view.** Already the right shape — clicking a customer drops into a detailed posting history. Pulse needs the same drill-down from action queue → customer detail.
- **Authentication on the Streamlit dashboard.** A reminder that even internal tools need auth. Pulse will need OAuth/SSO.

## Specific code modules to reference later
- `src/salesforce_client.py` — Salesforce client; reusable foundation for Pulse's Salesforce read layer. Note PM_CONTEXT prefers `sf` CLI over `simple-salesforce` for Pulse, so this is a *reference*, not a direct lift.
- `src/matcher.py` and `src/ai_matcher.py` — hybrid matcher pattern.
- `src/state.py` — SQLite new-vs-seen state tracking; portable to any signal-suppression need.
- `src/scanners/ats_scrapers/` — adapter-per-vendor pattern.
- `src/orchestrator.py` — pipeline orchestration; useful for understanding the run shape before re-architecting with n8n.
- `src/notifications.py` and `src/sf_tasks.py` — outbound action surfaces (email + Salesforce tasks). These are exactly the kinds of "actions" Pulse's action queue will dispatch.
- `config/role-catalog.json` — the canonical EDGE role catalog. Pulse should consume this same file (or a shared upgrade of it).
- `dashboard/app.py` — Streamlit dashboard structure.

## What we explicitly are NOT taking from this
- **Streamlit as Pulse's primary UI.** Pulse's hero surface is the action queue in React; Streamlit is reference-only.
- **`simple-salesforce` username/password auth.** PM_CONTEXT's `reference_sfdc_access` memory locks `sf` CLI with `--target-org production`. Migrate any code we lift to the CLI approach.
- **Email as the primary notification channel.** PM_CONTEXT (`feedback_dont_flood_slack`) and the action-queue-as-hero standing rule mean notifications are dashboard/action-queue first, with email as a deliberate secondary surface.
- **SQLite as Pulse's primary state store.** Fine for new-vs-seen suppression at small scale; Pulse will likely want Postgres for the action log, plus Graphiti for the memory layer.
- **Job-board scraping logic for any signal beyond job postings.** Scope-locked: opportunity-tracker is the job-posting signal feeder; Pulse adds other signal types via other sources (Chorus, Zoom, SFDC, news).
- **The 53-role catalog as immutable.** It is the starting point; Phase 2 will likely refine it.

## Relevance to EDGE Pulse
**High — opportunity-tracker is Pulse's first committed external-signal feeder per PM_CONTEXT.** Pulse does not need to re-implement job-posting scanning; it consumes opportunity-tracker's output. The right shape: opportunity-tracker continues to produce its match records, and Pulse subscribes (via shared filesystem, a small queue, or a database table) to "new Hottest match" events and ingests them as Episodes into Graphiti, attached to the relevant Customer entity. The hybrid matcher pattern, the SQLite-state idempotency layer, and the tiered match taxonomy are all reusable beyond just job postings.

## Open questions raised by this repo
- **Integration contract between opportunity-tracker and Pulse.** Filesystem JSONL? Postgres table? HTTP webhook? n8n trigger? Filed for Phase 2.
- **Should opportunity-tracker be re-homed inside Pulse's repo or kept separate?** Probably kept separate (it runs on its own cadence, has its own scrapers, and the Streamlit dashboard is independently useful). Filed for Phase 2.
- **Role catalog ownership.** Pulse and opportunity-tracker both need the same role catalog. Either shared file with one canonical owner, or a small service. Filed for Phase 2.
- **Migration to `sf` CLI from simple-salesforce.** Worth doing in opportunity-tracker as a cleanup, but only if there's a real reason. Filed as a v1.5+ candidate.

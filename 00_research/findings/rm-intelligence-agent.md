# Findings: rm-intelligence-agent

## What it is
EDGE's own prior-work prototype — a Python pipeline (≈2,650 lines across 9 modules) that pulls Chorus call recordings + Salesforce data for ~50 top accounts and produces a CEO-facing static HTML demo. The pipeline runs in stages: (1) `chorus_pull` collects engagements/conversations via the Chorus v3 API; (2) `rank_accounts` joins Chorus meetings to SFDC accounts via name fuzz-match and ranks by meeting depth; (3) `sfdc_pull` pulls three SFDC layers — `RM_Outreach__c`, `Associates__c`, risk-tagged `Case` records — via the `sf` CLI (`--target-org production`); (4) `extract_signals` sends each meeting through `gpt-5-mini` to extract churn/expansion signals + verbatim client quotes; (5) `generate_narratives` produces per-account first-person AI-RM narrative paragraphs via `gpt-4o`; (6) `generate_ceo_overview` rolls up a CEO summary; (7) `render_demo` writes a single self-contained HTML file at `data/demo.html`. **This is the direct EDGE Pulse predecessor.**

## License
**No LICENSE file present in the folder; this is internal EDGE code.** Yes — EDGE owns it and can use, modify, or relicense as needed. Treat as wholly EDGE-internal IP and reuse freely.

## Maturity signal
- Last commit date: N/A (not a git repo at the folder level). Files last modified mid-May 2026 per filesystem timestamps.
- Stars / issues: N/A.
- Published papers / notable adopters: N/A.
- Subjective maturity: **Demo-ready prototype.** Working end-to-end pipeline that has produced output (`data/account_narratives.json`, `data/demo.html` are present). Code is pragmatic Python with no test suite, no abstraction over the pipeline stages, hardcoded model names and prompts, cross-project filesystem references (e.g., reads `../opportunity-tracker/data/accounts.json` and `../opportunity-tracker/.env`). Excellent material to *learn from and lift patterns from*; not a reusable library as-is.

## Data model / schema
The pipeline's intermediate JSON files implicitly define the working schema for Pulse:
- **Meeting (Chorus)** — engagement record with `account_id`, `account_name`, `host`, participants, `meeting_summary`, `action_items`, `transcript_link`, `recording_link`, date.
- **Account ranking row** — `account_name`, `industry`, `owner_name`, `meetings` count, derived rank.
- **Account signal aggregation** — per-account: `churn_signal_count`, `expansion_signal_count`, `churn_severity_mix`, `recent_sentiments`, top churn/expansion `quotes[]` with `signal`, `quote`, `severity`, `date`.
- **SFDC bundle** — per-account: `RM_Outreach__c` records (Customer_Health__c, Churn_Probability__c, Expansion_Probability__c, EBR_Description__c, Referral_Sentiment__c, etc.), `Associates__c` records (Active/Replaced/Terminated/Downsell statuses with RM_Manager and Associate_Manager owners), risk-tagged `Case` records with `Categories__c` starting with `Risk` and full `Description` + `Details__c`.
- **Per-account narrative** — `headline_html` (first-person AI-RM voice with inline `<num>`, `<good>`, `<bad>`, `<quote>`, `<em>` tags), `health_tier` (healthy/watch/at-risk/escalated), `one_line_recommendation`, `top_signals[]` (3–5 evidence cards), `talking_points[]`.

This schema is the **best concrete reference for Pulse's per-account data shape** in the entire research set. It is grounded in actual EDGE SFDC fields and actual Chorus payloads.

## Architectural patterns worth stealing
- **Four-layer signal triangulation (Chorus → RM_Outreach → Associates → Cases).** This is the operational order PM_CONTEXT already captures as the signal-triangulation pipeline. The code implements it.
- **Per-account JSONL caching of intermediate artifacts.** Every pipeline stage writes to a JSONL file and skips work that's already been done (`meeting_signals.jsonl`, `narrative_cache.jsonl`). Makes runs idempotent and CEO-demos cheap to iterate.
- **Fuzzy name matching for Chorus↔SFDC join** (`src/rank_accounts.py`). Token-set + substring + direct ratio fallback using stdlib `difflib`. Pulse will need the same join logic; reuse this function rather than re-derive.
- **Cheap-model bulk extraction + expensive-model narrative generation.** `extract_signals` uses `gpt-5-mini`/`gpt-4o-mini`-equivalent for bulk per-meeting extraction; `generate_narratives` uses `gpt-4o` for the synthesized voice. This two-tier model strategy maps directly onto Pulse's budget posture (PM_CONTEXT §5).
- **`sf` CLI subprocess for SOQL** (`src/sfdc_pull.py`). The user's memory already locks this approach (`reference_sfdc_access`); the code is the working example.
- **Inline-tag rendering of AI-RM voice** (`src/render_demo.py`'s `<num>`, `<bad>`, `<good>`, `<quote>`, `<em>` → CSS classes). Cleanest pattern in the audit for turning LLM prose into design-language-compliant HTML without an HTML-injection footgun. Whitelist the tags, escape the rest.
- **Single-file static HTML demo output.** `data/demo.html` is self-contained — perfect for CEO demos because there is no infrastructure to fail. Pulse should preserve this "ship a single HTML file" capability for demo scenarios even after we have a live UI.
- **Cross-project data sharing via filesystem** (reads `../opportunity-tracker/data/accounts.json`). Pragmatic glue today; needs to be cleaned up into a shared data layer in Pulse.

## Specific code modules to reference later
- `src/sfdc_pull.py` — the SOQL queries against `RM_Outreach__c`, `Associates__c`, `Case`. Authoritative reference for current SFDC schema usage.
- `src/chorus_pull.py` — Chorus v3 API patterns (auth header shape, pagination, conversation-detail join).
- `src/extract_signals.py` — prompt for client-voice churn/expansion extraction; preserves verbatim quotes; output JSON schema.
- `src/generate_narratives.py` — narrative generation prompt; inline-tag voice system; per-account context-building.
- `src/rank_accounts.py` — Chorus↔SFDC fuzzy join.
- `src/render_demo.py` — single-file HTML render with inline-tag styling. Design language already calibrated to Sales Pulse aesthetic (Edge purple `#4a0f70`, Instrument Serif italic, JetBrains Mono numbers).
- `data/demo.html`, `data/account_narratives.json`, `data/sfdc_bundle.json` — actual produced artifacts; read these to understand the existing demo's voice and tone.

## What we explicitly are NOT taking from this
- **The pipeline-as-Python-scripts orchestration.** Phase 1 should move to n8n (per PM_CONTEXT §3) so non-engineers can iterate on the pipeline.
- **Hardcoded model names.** Models will rotate; Pulse needs a single config point.
- **Cross-project filesystem reads.** `../opportunity-tracker/data/accounts.json` is glue; Pulse needs a proper shared data layer.
- **OpenAI dependency for all extraction.** PM_CONTEXT locks Claude as primary LLM. Migrate the extraction prompts to Claude API and golden-trace test.
- **Lack of tests.** Pulse's engineering rules (PM_CONTEXT §6 rule 6) require tests on every commit. This codebase has none — pattern, not test approach.
- **Static HTML as the production UI.** Demo asset, yes; production action queue is React/TS, no.
- **The signal taxonomy as final.** The current churn/expansion taxonomy is a starting point but should be refined in Phase 2 against actual Pulse skills.

## Relevance to EDGE Pulse
**Highest of any reference in this audit.** This is *Pulse v0*. It already encodes the EDGE-specific SFDC schema (RM_Outreach__c, Associates__c with placement statuses, Case w/ Risk categories), the Chorus integration mechanics, the four-layer signal triangulation order, the AI-RM first-person voice, the inline-tag rendering system, the single-file HTML demo deliverable, and a working CEO-overview generator. It also already adopts the cheap-model-for-extraction + expensive-model-for-synthesis pattern that fits the budget posture. Phase 1 should largely be a *re-architecture* of this codebase: same data flow, same outputs, but routed through Graphiti as the memory layer, governed via the action-queue contract, surfaced via React rather than static HTML, and hardened with tests and reasoning capture. The fuzzy-join function, the prompts, the rendering tags, and the JSONL caching pattern can be lifted nearly verbatim.

## Open questions raised by this repo
- **Should the existing demo HTML be preserved as the CEO-demo fallback?** Even after Pulse has a live UI, the "single self-contained HTML file" output is a powerful demo artifact that requires no infrastructure. Filed for Phase 2.
- **Migrate prompts from GPT to Claude.** Current pipeline uses `gpt-5-mini` and `gpt-4o`; PM_CONTEXT locks Claude as primary. Need a port + a golden-trace test for output stability. Filed for Phase 2.
- **The fuzzy Chorus↔SFDC join's failure modes.** Token-set ratio with a default cutoff is robust most of the time but occasionally collapses two distinct customers or misses a real match. Pulse should keep a manual override layer. Filed for Phase 2.
- **The signal taxonomy.** `churn_signals` and `expansion_signals` are the only first-class signal types today. Pulse will likely need more (e.g., placement-replacement-risk, RM-relationship-quality, referral-readiness). Filed for Phase 2.
- **Where does cached state go in the new architecture?** Today: JSONL files. Future: Graphiti + a Pulse-native event log? Filed for Phase 2.

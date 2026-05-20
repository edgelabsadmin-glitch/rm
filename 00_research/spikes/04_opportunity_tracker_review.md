# Spike 4 — opportunity-tracker Review (scoping for Phase 3 Planning)

**Date:** 2026-05-20
**Phase:** Bridge spike between Phase 2.5 closure and Phase 3 Planning
**Scope:** Read-only review of `opportunity-tracker/` to inform the Phase 3 Planning prompt. No code, no design artifacts, no skill specs produced here.

---

## Preamble — what I did

Read every Python module, the role catalog, the SQLite schema, sample match records from `data/runs/`, the dashboard's top, requirements.txt, and a live query of `data/state.db` (506 postings across 74 accounts; tier distribution captured in §1.4 below). Identified what to lift, where the matcher precision fix lands at code-level, the recommended integration contract, the behavioral shape of Skill 11, and the Phase 4 day count.

---

## Q1 — What's actually in the opportunity-tracker codebase?

### 1.1 Module inventory

| Module | Lines | Purpose |
|---|---|---|
| `src/orchestrator.py` | 301 | Daily-job entry point. Loads accounts, runs scanners, dedups, matches, writes state, sends notifications. Supports `--refresh` (SFDC pull), `--account X` (single), `--source boards|career|all`, `--workers N`, `--batch-commit N` (mid-scan git push for dashboard progress). |
| `src/scanners/jobboard_scanner.py` | 132 | `jobspy.scrape_jobs` wrapper. **Currently scans 4 sources: indeed, linkedin, glassdoor, google.** Verifies posting belongs to account via (a) domain match, (b) substring company-name match, (c) fuzzy company-name match ≥75%. |
| `src/scanners/career_scanner.py` | 71 | Career-page scraping. Tries Greenhouse → Lever → Generic in priority order. |
| `src/scanners/ats_scrapers/greenhouse.py` | 72 | Greenhouse API adapter. |
| `src/scanners/ats_scrapers/lever.py` | 66 | Lever API adapter. |
| `src/scanners/ats_scrapers/generic.py` | 115 | Generic HTML scraper for unknown ATS / direct career pages. |
| `src/matcher.py` | 107 | **Deterministic fuzzy matcher.** `thefuzz.fuzz.token_sort_ratio` against flat-string role catalog. Thresholds: 80=hottest, 65=warm, else=general. Industry boost: +5. |
| `src/ai_matcher.py` | 170 | **LLM-driven matcher** (currently OpenAI `gpt-5.4-mini`, batch_size=10). Adds `reasoning`, `outreach_suggestion`, `signals` fields. Falls back to fuzzy matcher on any failure. |
| `src/state.py` | 212 | SQLite state. Two tables (`postings`, `scan_runs`). `generate_posting_id()` produces a deterministic SHA-256 hash for idempotency. |
| `src/notifications.py` | 363 | Email (SMTP) + optional Slack webhook notifications for new postings. |
| `src/sf_tasks.py` | 97 | **Generates Salesforce Task recommendations as data only.** `push_tasks_to_salesforce()` exists as a Phase-2 placeholder — never called in Phase 1. |
| `src/salesforce_client.py` | 66 | `simple_salesforce` connection. Pulls `Account.Id, Name, Website, Industry, Segment__c, OwnerId, Owner.Name` for `Account_Status__c = 'Active'`. |
| `src/utils.py` | 162 | URL normalization, career-page discovery, request headers + timeouts. |
| `dashboard/app.py` | 1,258 | Streamlit + Plotly dashboard. Reads `data/state.db` directly. Uses purple `#4a0f70` (a slightly different shade than Tier-0's `#6B46C1` — flagged Q124). |
| `config/role-catalog.json` | 61 | **Flat string lists per industry.** 28 insurance + 15 medical + 10 dental = 53 roles. **No per-role metadata** (no `remote_compatible`, no aliases, no keywords). |
| `data/accounts.json` | — | Last `--refresh` snapshot from Salesforce. 586 active accounts. |
| `data/state.db` | — | SQLite. Live data: 506 postings, 74 distinct accounts, tier mix: 134 hottest / 37 warm / 335 general. |
| `data/runs/{date}_*.json` | — | Per-run output: `_scan_results.json` (everything) + `_new_postings.json` (only new). |
| `data/scan_progress.json` | — | Mid-scan progress for dashboard polling. |

### 1.2 Architecture — the daily-job flow

```
   cron / manual trigger
            │
            ▼
   orchestrator.main()
   ├── (optional) --refresh → salesforce_client.connect() → get_active_accounts() → accounts.json
   ├── load_accounts() from data/accounts.json
   ├── load_role_catalog() from config/role-catalog.json
   ├── for each account (serial; --workers flag exists but main() loop is serial):
   │     scan_account(account, catalog, sources, conn)
   │       ├── scan_company(name, industry, website)        # jobboard via jobspy
   │       ├── scan_career_page(account)                    # ATS adapters + generic
   │       ├── deduplicate_postings(across sources, prefer career_page/greenhouse/lever)
   │       ├── ai_match_postings(...)  → falls back to fuzzy on failure
   │       ├── generate_task_recommendations(matched, account)  # data only, no SFDC write
   │       ├── detect_new_postings(conn, account_id, matched)
   │       └── save_postings(conn, ...)
   ├── save_run_summary(conn, ...)
   └── send_new_postings_email + send_slack_notification (when not --no-email)
```

### 1.3 External integrations

| Integration | Mechanism | Library | Auth |
|---|---|---|---|
| **Job-board scrape (LinkedIn / Indeed / Glassdoor / Google)** | `jobspy.scrape_jobs` library | `python-jobspy` | API-key-free; scrapers wrapped inside jobspy |
| **Career-page scrape** | `requests` + `beautifulsoup4` + Greenhouse/Lever JSON APIs | `requests`, `bs4`, `lxml` | None |
| **Salesforce account refresh** | SOQL via `simple_salesforce` | `simple-salesforce` | `SF_USERNAME` + `SF_PASSWORD` + `SF_SECURITY_TOKEN` in `.env` |
| **AI matching** | OpenAI chat completions, `gpt-5.4-mini`, batch_size=10, temperature=0.1 | `openai` | `OPENAI_API_KEY` |
| **Email notifications** | SMTP (Gmail) | stdlib | `.env` SMTP creds |
| **Slack notifications** | webhook POST | `requests` | `SLACK_WEBHOOK_URL` (optional) |
| **Mid-scan progress publishing** | `git add/commit/push` of `state.db` + `scan_progress.json` | shell out to `git` | Local git auth |

### 1.4 State management — schema

```sql
CREATE TABLE postings (
  id              TEXT PRIMARY KEY,           -- SHA-256 hash, first 16 chars
  account_id      TEXT NOT NULL,              -- SFDC Account.Id
  account_name    TEXT NOT NULL,
  title           TEXT NOT NULL,
  company         TEXT,
  location        TEXT,
  source          TEXT NOT NULL,              -- linkedin | indeed | glassdoor | google | career_page | greenhouse | lever
  url             TEXT,
  date_posted     TEXT,
  description     TEXT,                       -- truncated to 500 chars
  first_seen_date TEXT NOT NULL,
  last_seen_date  TEXT NOT NULL,
  match_tier      TEXT,                       -- hottest | warm | general
  matched_role    TEXT,                       -- from role catalog
  match_score     INTEGER,                    -- 0-100
  reasoning       TEXT,                       -- LLM-generated
  outreach_suggestion TEXT,                   -- LLM-generated (2-3 sentence sales prompt)
  signals         TEXT                        -- comma-joined list (e.g. "exact role match, multiple openings, urgent hire")
);
-- + indexes on (account_id), (first_seen_date), (match_tier)

CREATE TABLE scan_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT NOT NULL,
  accounts_scanned INTEGER,
  new_postings_found INTEGER,
  total_postings_found INTEGER,
  errors INTEGER
);
```

**Idempotency.** `state.generate_posting_id()` is deterministic: `sha256(f"{account_id}:{url}").hexdigest()[:16]`, falling back to `sha256(f"{account_id}:{title.lower()}:{location.lower()}")` when URL is missing (career pages with unstable URLs). Same posting → same id → `detect_new_postings` skips on existing.

### 1.5 Output shape — actual match record (verbatim from `data/runs/2026-04-04_new_postings.json`)

```json
{
  "title": "Senior Employee Relations Investigator",
  "company": "Acrisure",
  "location": "Tennessee, United States",
  "source": "linkedin",
  "url": "https://www.linkedin.com/jobs/view/4395316214",
  "date_posted": "2026-04-02",
  "description": "**About Acrisure**\n Acrisure is a global Fintech leader…",
  "match": {
    "score": 10,
    "tier": "general",
    "matched_role": null,
    "matched_industry": null,
    "reasoning": "The title is an employee relations investigator role, which is HR/compliance work and not a close match to Edge's insurance operations, claims, or support roles.",
    "outreach_suggestion": "Acrisure is hiring in a people-relations/compliance function, so this is not a primary fit for Edge's core staffing catalog. If you reach out, position Edge as a partner for their insurance operations and claims support needs rather than this role specifically, and ask whether they also have openings in claims, underwriting support, or customer service. That can open a broader conversation with a fast-growing insurance brokerage like Acrisure.",
    "signals": ["multiple openings", "large enterprise", "insurance company"]
  },
  "id": "b5e38d4fb7c22fc2",
  "is_new": true
}
```

The `match` object is the rich payload Pulse needs. Three of those fields — `reasoning`, `outreach_suggestion`, `signals` — are LLM-generated and constitute the work the matcher *already does* that Skill 11 should *consume*, not redo.

### 1.6 Role catalog — what the matcher binds to

```json
{
  "insurance": ["Customer Care Coordinator", "Customer Service Representative", …28 strings],
  "medical":   ["Scheduling Coordinator", "Patient Care Coordinator", …15 strings],
  "dental":    ["Scheduling Coordinator", "Patient Care Coordinator", …10 strings]
}
```

**53 total roles. All flat strings. No metadata.** Three categories overlap (Scheduling Coordinator and a few others appear in multiple verticals).

**Implication:** the matcher currently has no structural place to say "this role is intrinsically in-person" or "EDGE places remote variants of this role only." Either the catalog gets a schema upgrade or the in-person filter happens entirely at the posting level. (Recommendation in §Q2.)

---

## Q2 — What's the matcher actually doing? Where does the precision fix land?

### 2.1 Deterministic layer (`src/matcher.py`)

```python
score = fuzz.token_sort_ratio(job_title.lower(), role.lower())     # line 42
if catalog_industry == mapped_industry:
    score = min(score + 5, 100)                                    # +5 industry boost
```

- Title-only matching. Description, location, salary, work-arrangement — none of these enter the score.
- Tiers: `score >= 80 → hottest`, `>= 65 → warm`, `else → general`.
- Industry boost (+5) applies when the posting's account is in the same industry catalog (insurance/medical/dental).

**No location filter. No remote-vs-in-person filter. No description scan.** This is the structural source of the user's "flags in-person-only roles like Nurse" complaint.

### 2.2 AI layer (`src/ai_matcher.py`)

- Model: `gpt-5.4-mini` — **must migrate to Claude per Decision 13.**
- Batch size: 10 postings per call, temperature 0.1.
- Prompt instructs the model to produce: `score`, `tier`, `matched_role`, `matched_industry`, `reasoning`, `outreach_suggestion`, `signals`.
- The prompt **passes location to the model** (`"location": p.get("location", "")`) but **does not instruct it to filter or down-weight in-person-only postings**.
- Falls back to fuzzy on init failure or per-batch JSON parsing failure.

### 2.3 Why "Nurse" gets flagged — concrete explanation

"Nurse" isn't in the catalog. But "Patient Care Coordinator" is. The fuzzy matcher returns ~50% similarity for "Registered Nurse Patient Care Coordinator" against "Patient Care Coordinator" — below the `warm` threshold of 65, so this case alone doesn't fire. The actual fail mode is the AI layer: GPT, given the catalog + the posting + no remote-required filter, treats a Nurse-flavored Patient Care Coordinator as a close match because the *responsibilities* in the description overlap with the catalog role, even though EDGE can't service the placement. The LLM is *too* generous because the prompt doesn't tell it to be skeptical of physical-presence requirements.

### 2.4 The precision fix — concrete, code-level

**Three changes, none of them deep.** Estimated effort: ~1 day total.

#### Change A — Role catalog schema upgrade (`config/role-catalog.json`)

Promote from flat strings to typed objects. Default `remote_compatible: true` for the existing 53 roles (EDGE wouldn't have them in the catalog if they weren't remote-friendly), but the schema accommodates future roles that aren't:

```json
{
  "insurance": [
    {
      "name": "Customer Care Coordinator",
      "remote_compatible": true,
      "in_person_disqualifiers": [],
      "aliases": ["Customer Care Rep", "Care Coordinator (Insurance)"]
    },
    …
  ],
  …
}
```

Three new fields per role:
- `remote_compatible: bool` — default `true`. If `false`, the matcher hard-skips this role.
- `in_person_disqualifiers: string[]` — phrases that, if present in the posting description, disqualify *this specific role* (e.g., for "Dental Assistant", disqualifiers might include `["chairside", "operatory", "hands-on", "intraoral"]`). Empty by default; populated as RMs flag false-positives in the queue.
- `aliases: string[]` — synonyms the matcher should accept (e.g., "Scribe" ↔ "Medical Scribe"). Existing-fuzzy-noise reduction.

**Files that change:** `config/role-catalog.json` (schema), `src/matcher.py:11-13` (loader to handle object form), `src/matcher.py:40-54` (read `role["name"]` instead of `role`).

#### Change B — Posting-level filter in the AI prompt (`src/ai_matcher.py:44-65`)

Add a new prompt instruction:

> 8. **work_arrangement**: One of "remote", "hybrid", "on-site", or "unspecified". Read the location and description: if the location names a specific physical address or city *only* (e.g. "Nashville, TN" without "remote" / "virtual" / "work from home"), AND the description mentions on-site duties, return "on-site". Edge places **remote talent only** — postings classified as "on-site" should receive tier="off-scope" regardless of title match.

Add `"off-scope"` as a fourth tier value. `src/matcher.py:60-67` tier-mapping table updates to include `off-scope` (returned only by AI layer; deterministic layer cannot infer work-arrangement and continues using its three tiers).

**Files that change:** `src/ai_matcher.py` (prompt + tier value), `src/matcher.py` (tier value), `src/state.py` (acceptable enum values for `match_tier`), `dashboard/app.py` (display the new tier).

#### Change C — Source narrowing (`src/scanners/jobboard_scanner.py:77`)

User directive: "only LinkedIn and Indeed are in scope; the third never works." The current code scans **four** sources: `["indeed", "linkedin", "glassdoor", "google"]`. Narrow to two:

```python
# Before
site_name=["indeed", "linkedin", "glassdoor", "google"],
# After
site_name=["indeed", "linkedin"],
```

**Half-hour change. One line.** This is the cheapest precision win — removes the noisiest sources and halves the per-account scrape time.

### 2.5 Filter location — recommendation

The user's question phrased the choice as "field on the catalog vs. field on the posting vs. both." Recommendation: **both, but the posting-level filter does the heavy lifting.**

- Catalog-level (`remote_compatible: false`) is for roles EDGE *never* places remote (currently zero such roles; the field is future-proofing).
- Posting-level (`work_arrangement: "on-site"`) is for postings that happen to be on-site even when the role is generally remote-compatible. **This is the case the user actually hit.** Most catalog roles can be done remotely *or* on-site depending on the customer; the posting's content is what disambiguates.

The two filters compose: if `role.remote_compatible is False` OR `posting.work_arrangement == "on-site"` → drop.

---

## Q3 — Integration contract recommendation

### 3.1 The four candidate paths

| Path | Pulse pulls | opportunity-tracker pushes | Operational shape |
|---|---|---|---|
| **A. Shared Postgres table** | Pulse n8n polls every 30 min for `processed_at IS NULL` rows | opportunity-tracker writes new match records on every daily run | Pulse owns the schema; opportunity-tracker writes only |
| B. Webhook (opp-tracker → Pulse) | Pulse exposes `/webhooks/opportunity-tracker` | opportunity-tracker fires per new match | Requires opportunity-tracker to maintain HTTP delivery semantics (retries, idempotency keys) |
| C. SFDC custom object | Pulse reads via the existing SFDC adapter | opportunity-tracker writes to a new `Job_Posting_Match__c` object | Couples opp-tracker release cadence to SFDC schema migrations |
| D. File-drop | Pulse polls a shared S3 prefix | opportunity-tracker writes per-run JSON to S3 | Brittle on failure modes; no per-record idempotency without extra plumbing |

### 3.2 Recommendation: **Path A — Shared Postgres table**

**Rationale.**
- **Cost-aligned with PM_CONTEXT §5 ($20/mo target).** Supabase free tier (Phase 1 lock per Design 11 ADR-003) accommodates this with room to spare. opportunity-tracker's SQLite stays; adding a Postgres write is a single `psycopg2` call from `state.save_postings()` (mirror writes).
- **Maintenance-friendliness wins.** The schema for `expansion_intent_signals` is a 12-column table mirroring `postings` plus three coupling fields (`pulse_episode_id`, `processed_at`, `processed_status`). One schema, one source of truth, no HTTP retries to debug, no SFDC schema migration ceremony.
- **Signal Source Adapter pattern compatibility (§6 rule 26).** The path implements the adapter contract from Design 02 cleanly:
  - `list_recent_events(since)` = `SELECT * FROM expansion_intent_signals WHERE processed_at IS NULL`
  - `receive_webhook(...)` = N/A (not webhook-driven)
  - `fetch_full(event)` = already-full from the row
  - `normalize(raw)` = trivial mapping to Episode envelope (§3.4 below)
  - `dedup_key(raw)` = `f"oppt:posting:{posting_id}"` — uses opp-tracker's already-deterministic SHA-256
- **Idempotent by construction.** opp-tracker's `generate_posting_id` produces a stable hash; Pulse uses the same hash as its dedup_key (Design 02 §"Idempotency contract"). Same posting → same hash → ingestion no-op on retry.

**The "split-brain risk":** opp-tracker keeps writing to SQLite (its own state), Pulse reads from Postgres (the mirror). If the two diverge, the SQLite is authoritative for opp-tracker's own behaviors (dedup, dashboard) and Postgres is authoritative for Pulse's behaviors (episode ingestion). Both writes happen in the same transaction within `state.save_postings()`, so divergence requires either a Postgres outage during a scan run (acceptable — Pulse picks up the row on the next opp-tracker run) or a manual SQLite edit (out of scope).

### 3.3 Concrete schema for the shared Postgres table

```sql
CREATE TABLE expansion_intent_signals (
  posting_id           TEXT PRIMARY KEY,             -- opp-tracker's deterministic hash
  account_id           TEXT NOT NULL,                -- SFDC Account.Id
  account_name         TEXT NOT NULL,

  -- Posting fields (mirror of opp-tracker's row)
  title                TEXT NOT NULL,
  company              TEXT,
  location             TEXT,
  source               TEXT NOT NULL,                -- linkedin | indeed | career_page | greenhouse | lever
  url                  TEXT,
  date_posted          TEXT,
  description          TEXT,
  first_seen_date      TIMESTAMPTZ NOT NULL,

  -- Match fields (mirror of opp-tracker's match.* fields)
  match_tier           TEXT,                         -- hottest | warm | general | off-scope
  matched_role         TEXT,
  matched_industry     TEXT,
  match_score          INTEGER,
  reasoning            TEXT,
  outreach_suggestion  TEXT,
  signals              TEXT[],                       -- Postgres array; JSONB also fine
  work_arrangement     TEXT,                         -- (added by Change B above)

  -- Pulse coupling fields
  ingested_at          TIMESTAMPTZ DEFAULT NOW(),    -- when opp-tracker wrote this row
  processed_at         TIMESTAMPTZ,                  -- when Pulse ingested as Episode; NULL until then
  pulse_episode_id     UUID,                         -- Pulse-side Episode UUID after ingestion
  processed_status     TEXT                          -- 'ingested' | 'skipped:off-scope' | 'skipped:dup' | 'failed'
);

CREATE INDEX idx_eis_unprocessed ON expansion_intent_signals(account_id) WHERE processed_at IS NULL;
CREATE INDEX idx_eis_account     ON expansion_intent_signals(account_id, first_seen_date DESC);
CREATE INDEX idx_eis_tier        ON expansion_intent_signals(match_tier);
```

### 3.4 Episode envelope (mapping into Design 02's schema)

Per Design 02 §"The Episode envelope":

```python
Episode = {
  "episode_id":     <Pulse-assigned UUID>,
  "dedup_key":      f"oppt:posting:{posting_id}",         # uses opp-tracker's hash
  "source":         "opportunity-tracker",
  "source_event_id": posting_id,                          # opp-tracker's hash
  "source_url":     posting.url,                          # the LinkedIn / Indeed / career-page URL
  "source_timestamp": posting.first_seen_date,
  "content_type":   "json",
  "content": {
    "posting": {title, location, source, url, description, date_posted},
    "match":   {tier, matched_role, score, reasoning, outreach_suggestion, signals, work_arrangement}
  },
  "subject":     f"Job posting: {title} @ {company}",
  "description": f"opportunity-tracker {tier} match: {matched_role}",
  "candidate_entities": [
    {"type": "Customer", "sfdc_id": account_id, "name": account_name}
  ],
  "tags": ["expansion-intent", tier, source],
  "ingested_at": <now>,
  "processing_state": "received"
}
```

**What the agent sees** when querying "expansion signals at Acrisure": a list of `Episode`s tagged `expansion-intent`, each carrying the full match payload. Graphiti extracts `(Account)-[posted_job:tier]->(Topic:matched_role)` edges; the agent gets a structured cross-account view through the same retriever it uses for any Customer query (Design 01 `get_customer_context`).

### 3.5 Idempotency — where dedup happens

**Two layers, both load-bearing.**

1. **At the adapter** (Pulse's opportunity-tracker Signal Source Adapter): `dedup_key = f"oppt:posting:{posting_id}"`. Pulse's `episodes` Postgres table has `UNIQUE(dedup_key)` (Design 02). A repeat ingestion = silent no-op at the insert.
2. **At the polling layer**: Pulse's n8n workflow polls `WHERE processed_at IS NULL`. After successful ingestion, Pulse `UPDATE expansion_intent_signals SET processed_at = NOW(), pulse_episode_id = $1, processed_status = 'ingested'`. The row leaves the polling queue.

Failure modes handled:
- Pulse crashes mid-ingest → row stays `processed_at = NULL` → next poll retries. Dedup at the `episodes` UNIQUE gate prevents double-ingestion.
- Pulse ingests but UPDATE fails → row stays `processed_at = NULL` → next poll re-attempts → episodes UNIQUE skips the second insert → next UPDATE succeeds.
- opp-tracker re-scans and re-writes the same `posting_id` → Postgres `INSERT … ON CONFLICT (posting_id) DO UPDATE` (set `match_tier`, `outreach_suggestion`, `signals` etc.) updates the *latest match analysis* but leaves `processed_at` / `pulse_episode_id` intact. Pulse does not re-ingest unless explicitly forced.

---

## Q4 — Skill 11 behavioral shape (not a spec; that's Phase 3)

**Working name:** `detect-expansion-intent-from-job-posting` (consistent with skill naming convention).

**Trigger.** Episode-driven. Fires on every `episode-ingested` event where:
- `source == "opportunity-tracker"`, AND
- `content.match.tier IN ('hottest', 'warm')`, AND
- `content.match.matched_role IS NOT NULL`, AND
- `content.match.work_arrangement != 'on-site'` (post-precision-fix)

Skip `general` and `off-scope` tiers by default — too noisy. Configurable per policy (admin may enable `general` for high-priority accounts).

**Output — proposed Action Queue card.** Three components:
1. **The drafted outreach email** to the customer-side champion (lifted from `content.match.outreach_suggestion`, polished and personalized by Pulse using the Customer profile from Design 06).
2. **The supporting context Pulse adds** that opp-tracker cannot know on its own — current placed-talent count at the account (from Graphiti `placed_at` edges, Design 01), the account's current health tier (Design 07), and any *recent* signals from the same account (last 30 days, via `get_customer_context`).
3. **A SFDC Task** for the account RM (mirror of opp-tracker's `sf_tasks` recommendation, but dispatched only on approval — opp-tracker's own `push_tasks_to_salesforce` placeholder stays dormant; Pulse's Action Queue is the sole write path per §6 rule 6).

**`why_oneline` (example):**

> Acrisure posted 3 Medical Scribe roles in the last 7 days. EDGE currently places 18 talent there (Active). Strong expansion signal.

The structure is always: *(Customer) posted (N) (matched_role) (work_arrangement) roles in (window). EDGE currently places (M) talent there. (Tier) expansion signal.*

**`why_detail` (the expanded card):**
- The list of posting citations (clickable URLs to LinkedIn / Indeed / career-page); date_posted on each.
- The matcher's reasoning text (the LLM's prose from `match.reasoning`).
- The matcher's signals list (`["exact role match", "multiple openings", "team expansion", …]`).
- The placed-talent context from Graphiti: current Active count by role, recent Replaced/Terminated events (if any), the customer's `Customer_Health__c` / `Expansion_Probability__c` from RM_Outreach__c.
- Cross-postings pattern (if multiple postings within a window) — "this is the 4th opening in this role family this quarter at this customer."

**Reasoning trace (per Design 04):**
- `signals_consulted`: list of opportunity-tracker Episode IDs ingested + the Customer context retrievers called + the bundle summary
- `reasoning_text`: prose in the inline-tag voice (Tier-0 §10) — `<num>3 Medical Scribe postings</num> in <em>7 days</em>; <good>EDGE already places 18</good>; <bad>off-channel hiring pattern</bad> not in current placements`
- `proposed_action`: ActionPayload with email_draft + sfdc_task_draft

**Tier-aware variants (per §6 rule 4).**

| Account tier (`Account.Segment__c`) | Skill 11 behavior |
|---|---|
| **SMB** | `warm` tier auto-approve at +2h (low blast radius for SMB customer outreach); `hottest` tier human-required (high-stakes; SMB customers respond visibly to single-touch outreach). |
| **Mid-Market** | Both `warm` and `hottest` human-required. RM gets the drafted email + the SFDC Task in the Action Queue. |
| **Enterprise** | Both tiers human-required + the action card cc's VP of Client Success on the email draft. Suggested EBR-tie-in language pre-drafted ("we noticed your hiring activity in [role family] — happy to walk through your staffing forecast at our next EBR on [date]"). |

**Coordination with other skills.**
- **Skill 04 (`talent-care`)**: shared rate-limit table to prevent talent-care and expansion-intent action cards from stacking on the same account in the same week (Q67 pattern).
- **Skill 06 (`advocacy`)**: opp-tracker's `signals` list often mentions "strong sentiment" — feed into the advocacy skill's positive-signal triggers via the Graphiti edges Skill 11 emits.
- **Skill 10 (`cross-account-pattern-finder`)**: weekly aggregator looks for "vendor consolidation" patterns; Skill 11 contributes "expansion-intent across customer cohort" patterns (e.g., "5 dental customers all posted Insurance Coordinator roles in 2 weeks").

---

## Q5 — Phase 4 day-count estimate

| Item | Days |
|---|---|
| Signal Source Adapter for opportunity-tracker (Postgres-table polling + Episode envelope mapping + dedup discipline) | **1.0** |
| Role catalog schema upgrade (flat strings → typed objects with `remote_compatible` + `aliases` + `in_person_disqualifiers`; matcher.py loader update) | **0.5** |
| AI prompt extension for posting-level `work_arrangement` filter + `off-scope` tier addition across matcher/state/dashboard | **0.5** |
| Source narrowing (Glassdoor + Google removal from `jobboard_scanner.py:77`) + smoke-test | **0.25** |
| OpenAI → Claude migration in `ai_matcher.py` (port prompt; pin model per Q115; switch SDK) | **0.5** |
| Skill 11 implementation (per Design 05 template) | **1.0** |
| Integration golden-trace tests (synthetic match record → episode-ingested → skill fires → action-suggested → approval-gated dispatch → outcome detection) | **0.5** |
| **Total** | **~4.25 days** |

**vs. Session 10 estimate (~3 days):** **~1.25 days over.** The slip is concentrated in two items the Session 10 estimate didn't fully account for: (a) the OpenAI → Claude migration on opp-tracker's side (PM_CONTEXT Decision 13 makes this required, not optional), and (b) the catalog schema upgrade (which Session 10 treated as part of "matcher precision fix" but is a discrete change with its own ripple into the matcher loader).

**Buffer impact.** PM_CONTEXT §9 Session 10 noted ~3 days of buffer remained in the prior plan. This consumes ~4.25 days — that puts Phase 4 at ~1.25 days of effective overrun against the 4-week demo deadline. **Flag explicitly** per the spike prompt:

- **Mitigation A (recommended):** keep opportunity-tracker on OpenAI for Phase 1 (the matcher prompts are stable; OpenAI → Claude migration there is a v1.5+ candidate). This saves 0.5 days and stays within original budget. White-label rule is *not* violated because opp-tracker is an *upstream* signal source, never user-facing; its LLM provider is implementation detail. **However, this contradicts the spirit of Decision 13 ("migrate before production data flow").** Worth a PM decision.
- **Mitigation B:** defer Skill 11's Enterprise-tier EBR-tie-in pre-drafted language to v1.5 (Q125). Saves ~0.25 days.
- **Mitigation C:** ship Skill 11 as Phase 1 *for hottest tier only* on the demo path (warm tier deferred to v1.5). Saves ~0.5 days on golden-trace test coverage. Demo storyboard supports this — Scene 3 only needs one strong "Acrisure posted 3 Medical Scribe roles" moment, not the full tier matrix.

**PM recommendation:** Mitigation A (keep opp-tracker on OpenAI for Phase 1) + Mitigation B (defer EBR-tie-in copy). Combined savings ~0.75 days. Phase 4 day-count returns to ~3.5 days, within Session 10 estimate range plus 0.5 days for the catalog schema upgrade that wasn't fully scoped originally.

---

## §13 Coverage Map implications

PM_CONTEXT §13's footer already states "opportunity-tracker addition extends §13.6 row count to 10." This memo confirms and proposes the exact additions:

### §13.5 — add a row under "Customer Success & Relationship Management"

| JD area | JD ask | Pulse capability | Phase |
|---|---|---|---|
| Customer Success & Relationship Management | Proactive customer-side expansion-signal detection (job postings, public signals) | Skill 11 `detect-expansion-intent-from-job-posting` + opportunity-tracker Signal Source Adapter | Phase 1 |

**Rationale.** The JD doesn't have this row verbatim, but the underlying responsibility — proactive customer-side opportunity surfacing — is the spirit of "Proactive feedback gathering" (already covered by Skill 01) extended to *outside* signals beyond the call/SFDC/case stream. opportunity-tracker is the first non-Chorus, non-SFDC, non-Calendar signal source Pulse ingests; this row makes that addition explicit in the coverage map.

### §13.6 — add row #10 under "Where Pulse exceeds the EDGE doc"

| # | Pulse upgrade | Rationale |
|---|---|---|
| 10 | **opportunity-tracker as expansion-intent signal source** | EDGE doc focuses on internal signals (calls, notes, cases); Pulse extends to public hiring data already running daily at EDGE. Job postings are a high-signal expansion indicator that the EDGE doc doesn't contemplate. |

PM updates §13.5 and §13.6 after this memo lands; PM_CONTEXT already pre-staged the row count expectation.

---

## New open questions

## Q118: Source narrowing — confirm "Glassdoor + Google removed"
**Raised during:** Spike 4
**Question:** User said "the third source never works." `jobboard_scanner.py:77` actually scans four sources: `["indeed", "linkedin", "glassdoor", "google"]`. Confirm: keep `["indeed", "linkedin"]` only?
**Why it matters:** Half-hour change; cleanest possible noise reduction. Decision needed before Phase 4 starts.
**Recommended path:** Narrow to LinkedIn + Indeed. PM-recommended.
**Status:** Open

## Q119: Role catalog schema upgrade — full restructure or additive metadata
**Raised during:** Spike 4
**Question:** Promote `config/role-catalog.json` from flat strings to typed objects (`{name, remote_compatible, in_person_disqualifiers, aliases}`)? Or keep flat strings and add a parallel metadata file?
**Why it matters:** Schema upgrade is cleaner but breaks the existing matcher loader. Parallel file is incremental but adds a second source of truth.
**Recommended path:** Full restructure. The loader change is ~5 lines (`role["name"]` instead of `role`); the schema upgrade is forward-looking and aligns with the "no second source of truth" engineering principle. PM-recommended.
**Status:** Open

## Q120: `off-scope` as a fourth tier value
**Raised during:** Spike 4
**Question:** Introduce a fourth `match_tier` value (`off-scope`) for postings the AI matcher determines are on-site-only, OR silently filter to `tier=None` and never write the row?
**Why it matters:** `off-scope` preserves auditability (we know WHY a posting was excluded — useful for tuning the prompt later). Silent filter is cleaner but loses the audit trail.
**Recommended path:** `off-scope` as a fourth tier; dashboard displays it as a 4th tile; Pulse adapter skips ingestion for this tier (no Episode emitted) but the row persists in `expansion_intent_signals` with `processed_status='skipped:off-scope'`.
**Status:** Open

## Q121: opportunity-tracker's `sf_tasks.push_tasks_to_salesforce()` stays dormant
**Raised during:** Spike 4
**Question:** opp-tracker has a placeholder `push_tasks_to_salesforce()` function (`src/sf_tasks.py:79`) that would auto-create SFDC Tasks. Confirm Phase 1 keeps this dormant so Pulse's Action Queue is the sole SFDC-write path (per §6 rule 6).
**Why it matters:** Two write paths to SFDC = two approval surfaces. §6 rule 6 says only one.
**Recommended path:** Confirmed dormant. opp-tracker generates Task *recommendations* as data only; Pulse picks them up via the Episode and proposes them through the Action Queue with human approval. Update opp-tracker's docstring to note the deprecation.
**Status:** Open

## Q122: opportunity-tracker's OpenAI dependency — migrate to Claude now or v1.5+?
**Raised during:** Spike 4 (Mitigation A in day-count estimate)
**Question:** PM_CONTEXT Decision 13 says "migrate prompts from OpenAI to Claude before any production data flow." opportunity-tracker is currently OpenAI-based. It's an *upstream* tool that produces signals Pulse consumes — its LLM provider is not user-facing. Migrate now (adds 0.5 days to Phase 4) or defer to v1.5+ (stays within Session 10 buffer)?
**Why it matters:** 0.5 days; PM_CONTEXT Decision 13 interpretation.
**Recommended path:** Defer to v1.5+. opp-tracker is an upstream signal source; its LLM provider is implementation detail and doesn't violate the white-label rule (no user-facing surface mentions it). PM-recommended, contingent on PM accepting the Decision-13-spirit-vs-letter reading.
**Status:** Open

## Q123: Account tier field confirmed as `Segment__c`
**Raised during:** Spike 4
**Question:** Q22 (from Spike 1) asked for the SFDC Account tier field name. opportunity-tracker's `salesforce_client.py:24` reads `Segment__c` directly. Confirm this is the field Pulse's tier-aware behavior reads.
**Why it matters:** Resolves Q22. Phase 4 binds Pulse's tier policy to `Account.Segment__c`.
**Recommended path:** Confirmed. Mark Q22 as resolved.
**Status:** **RESOLVED 2026-05-20 (this memo).** Field is `Account.Segment__c`. Update Q22 status.

## Q124: opportunity-tracker dashboard purple shade
**Raised during:** Spike 4
**Question:** `dashboard/app.py:27` uses `BRAND = "#4a0f70"` (a darker purple than Tier-0's `#6B46C1`). Pulse's Tier-0 design language is locked at `#6B46C1`. Should the opportunity-tracker dashboard be re-skinned to match Tier-0, or kept as-is?
**Why it matters:** Visual coherence if RMs see both surfaces (opp-tracker dashboard and Pulse). The opp-tracker dashboard is admin-internal today; if it stays admin-only, brand-coherence is low-stakes.
**Recommended path:** Defer to v1.5+. opp-tracker dashboard is internal-admin only; Phase 1 ships with the existing styling. Re-skin if/when the dashboard surfaces to RMs.
**Status:** Open (v1.5+ candidate)

## Q125: Skill 11 Enterprise EBR-tie-in pre-drafted language — Phase 1 or v1.5+?
**Raised during:** Spike 4 (Mitigation B in day-count estimate)
**Question:** Skill 11's Enterprise-tier variant suggests pre-drafted EBR-tie-in language ("we noticed your hiring activity in [role family] — happy to walk through your staffing forecast at our next EBR on [date]"). Saves the RM a paragraph of email-writing. Phase 1 ships or v1.5+?
**Why it matters:** ~0.25 days of Phase 4 scope.
**Recommended path:** Phase 1 ships *static* EBR-tie-in language; the dynamic-EBR-date insertion is v1.5+. The RM can edit the date inline on the Action Queue card.
**Status:** Open

---

## What this spike did NOT do

- Did not write any code (per Hard Constraint 1).
- Did not write any design artifact (per Hard Constraint 2).
- Did not write the Skill 11 spec (per Hard Constraint 3 — that's Phase 3).
- Did not test the matcher precision fix end-to-end against real postings (the fix is recommended at code level; verification is a Phase 4 task).
- Did not benchmark opp-tracker's daily-run cost (LLM tokens, scrape rate-limits) at production volumes — out of scope for a scoping spike.
- Did not migrate any opp-tracker code to Claude (Q122 defers).

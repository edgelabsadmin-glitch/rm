# expansion_signal_job_posting_match_v1

**Version:** v1
**Category:** expansion
**Severity model:** tiered (low / medium / high) — mapped from opportunity-tracker's tier output
**Owning skill(s):** Skill 11 (detect-expansion-intent-from-job-posting) — primary
**Status:** active

## Plain-English definition

opportunity-tracker (the existing EDGE daily-scan tool) matched a new job posting at a customer against EDGE's 53-role catalog. The posting indicates the customer is hiring for a role EDGE can staff — an expansion opportunity. Severity mirrors opportunity-tracker's `match.tier` value (`hottest` / `warm` / `general`), with the `off-scope` tier suppressing the signal entirely (per Q120 + Spike 4 §Q2).

## Detection mechanism

**Type:** hybrid — opportunity-tracker does the matching (rules + LLM); Pulse consumes the result.

opportunity-tracker's daily scan produces match records (per Spike 4 §1.5). When records land in the shared Postgres `expansion_intent_signals` table with `processed_at IS NULL`, Activepieces polls every 30 minutes (per ADR-002 §"Trigger types Phase 1 uses") and posts each new record to Pulse's `/webhooks/expansion-intent` endpoint. Pulse's opportunity-tracker Signal Source Adapter normalizes the row into an Episode (per Spike 4 §3.4), and this signal fires on `episode-ingested` events tagged `expansion-intent`:

```
For each Episode with source='opportunity-tracker':
  match = episode.content.match
  if match.tier == 'off-scope':
    return None  # suppressed per Q120 fix
  if match.matched_role is None:
    return None  # safety; shouldn't happen post-precision-fix

  severity = {
    'hottest':  'high',
    'warm':     'medium',
    'general':  'low',
  }[match.tier]

  fire(severity, evidence=episode)
```

No additional LLM call — the match record already contains opportunity-tracker's LLM reasoning, outreach suggestion, and signals list.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| `expansion_intent_signals` Postgres table | posting metadata + match metadata | per-row (daily scan cadence) |
| Pulse Episode (post-ingestion) | `content.match.{tier,matched_role,reasoning,outreach_suggestion,signals,work_arrangement}` | last 30 days |
| Graphiti `posted_job` edges | (Account)-[posted_job:tier]->(Topic:role) | last 30 days |
| Per-Profile Markdown (Customer) | placed-talent context (current Active count, recent Replaced events) | current |

## Triggering threshold

- `off-scope` tier → suppressed (no fire, no Episode, no action card).
- `general` tier → suppressed by default (too noisy; Phase 1 config). Admin can enable via policy module.
- `warm` tier → `medium` severity.
- `hottest` tier → `high` severity.

## Tier-aware variants (Account tier — distinct from match tier!)

Match tier = the opportunity-tracker classification. Account tier = the Customer's SFDC `Segment__c`.

| Account tier | Variant |
|---|---|
| **SMB** | `warm`-match → auto-approve at +2h. `hottest`-match → human-required. |
| **Mid-Market** | Baseline. All severities human-required. |
| **Enterprise** | `warm` and `hottest` both human-required + cc VP-CS on the action card. Static EBR-tie-in copy attached (per Mitigation B in Spike 4). |

## False-positive failure modes

- **In-person-only role disguised as remote-compatible.** Pre-precision-fix issue. Mitigation: Spike 4's three changes (catalog schema upgrade, posting-level `work_arrangement` filter, source narrowing) — implemented in Phase 4 spec 016.
- **Customer is hiring but EDGE was already informed.** Customer already mentioned hiring (`expansion_signal_verbal_capacity_mention_v1` fired). Mitigation: Skill 11's composition logic dedups (Q134) — one action card, not two.
- **Different parent-org account.** opportunity-tracker matches via SFDC Account.Id; cross-org confusion is unlikely.
- **Repeat scrape of same posting.** opportunity-tracker's deterministic `posting_id` SHA-256 prevents double-write at source; Pulse's episode `dedup_key` prevents double-ingestion.

## False-negative failure modes

- **Postings on non-LinkedIn/non-Indeed boards.** Per Q118 + Mitigation in Spike 4, only LinkedIn + Indeed are scanned. Postings on Glassdoor / Google / company-direct (without an ATS we scrape) are missed.
- **Postings the AI matcher classifies `general`.** Suppressed by default; admin can enable `general` for specific accounts.
- **Postings that go up and come down between daily scans.** Edge case; opportunity-tracker scans daily, so postings live <24h are at risk.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| `match_tier_to_severity` map | dict | per above | Admin | Re-map opportunity-tracker tiers to Pulse severities |
| `include_general_tier` | bool | False | Admin | True = `general` fires at `low` |
| `account_id_allowlist_for_general` | list | empty | Admin | Per-account exception list to fire `general` |
| Source narrowing | list | `[linkedin, indeed]` | opportunity-tracker config | (Q118-disposition) |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_ (Spike 4 noted ~134 hottest + 37 warm in current state.db on 74 accounts; daily volume estimate ~5-10 hottest fires per RM)
- Action-approval rate: _TBD_
- Outcome (Opportunity created / RFP received) within 30d: _TBD_  ← critical Layer 8 outcome
- Apparent false-positive rate (e.g. customer says "we filled internally"): _TBD_
- Last tuned: never

## Examples

### Example 1 — Acrisure
- **Evidence:** opportunity-tracker matched 3 LinkedIn postings for "Medical Scribe" at Acrisure in last 7 days; all tier=`hottest`; matched_role=Medical Scribe; work_arrangement=`remote`.
- **Signal fires at:** `high` (Mid-Market; hottest tier).
- **Action proposed:** Skill 11 — drafted email to Sarah Chen citing the 3 postings + 18 currently-placed talent at Acrisure + outreach_suggestion from opportunity-tracker as the body.

### Example 2 — Helix Labs (Enterprise)
- **Evidence:** opportunity-tracker matched 1 posting tier=`warm`; matched_role=Patient Care Coordinator; work_arrangement=`remote`.
- **Signal fires at:** `medium` (Enterprise; warm tier). cc VP-CS triggered.
- **Action proposed:** Skill 11 — email draft + Salesforce Task + EBR-tie-in copy attached.

### Example 3 — Vertex Group — does NOT fire
- **Evidence:** opportunity-tracker matched 1 posting tier=`off-scope` (on-site only).
- **Signal does NOT fire.** Row written to `expansion_intent_signals` with `processed_status='skipped:off-scope'`; no Episode emitted.

## Open questions

- **Q135:** `general`-tier-by-account allowlist. The user mentioned some accounts where even low-signal postings are worth seeing. Phase 1 ships with allowlist empty; admin can add accounts post-launch.
- See also Q118, Q119, Q120 (catalog schema, source narrowing, off-scope tier) — all dispositions in `99_open_questions.md`.

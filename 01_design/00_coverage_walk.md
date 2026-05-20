# Phase 2 — §13 EDGE Coverage Walk

**Date:** 2026-05-20
**Purpose:** Per §6 rule 5 and §13.7, verify every row in PM_CONTEXT §13.2–13.5 has at least one corresponding design artifact. Coverage gaps block Phase 2 → Phase 3 advancement.

---

## §13.2 — EDGE Workflow 1 (Automated Post-Meeting Note Capture)

| EDGE ask | Design artifact(s) | Coverage |
|---|---|---|
| Meeting ends → webhook fires → workflow activates | Design 02 (`signal_source_adapter.md` §Behavior + diagram); Design 11 (n8n) | ✅ |
| Submit voice note or text summary (30 sec) | Design 03 (Action Queue) for *received* surfacing; ingest mechanism via Design 02 Chorus adapter | ✅ |
| Workflow captures meeting transcript | Design 02 Chorus adapter `fetch_full()` | ✅ |
| Sentiment score (1–10) extraction | Skill `01-detect-talent-signal` (multi-axis vector, composite 1–10 for UI) | ✅ |
| Theme tags (burnout, growth, AI displacement, etc.) | Skill `01-detect-talent-signal` signal taxonomy | ✅ |
| Urgency flag | Skill 01 + Design 04 `urgency` field on `action-suggested` event + Design 03 ranking | ✅ |
| 2-sentence summary | Skill 01 + ported prompt from rm-intelligence-agent (Decision 13) | ✅ |
| Push structured data to Salesforce via API | Design 03 Action Queue dispatch handlers; Design 04 §"Dispatch events" + §6 rule 6 | ✅ |
| Per-customer persistent knowledge thread | Design 01 (Three-Graph composition — bi-temporal edges per Customer; not a Claude conversation) | ✅ |

**§13.2 coverage: 9 / 9 rows ✅**

---

## §13.3 — EDGE Workflow 2 (Intelligent Pre-Meeting Briefing)

| EDGE ask | Design artifact(s) | Coverage |
|---|---|---|
| Detect customer meeting on calendar 24h ahead | Design 02 Calendar adapter | ✅ |
| Identify account name | Skill `02-prepare-customer-meeting-brief` (lifted fuzzy-join from rm-intelligence-agent) | ✅ |
| Pull all talent profiles from Salesforce | Design 01 (`get_customer_context` retriever); Design 02 SFDC adapter | ✅ |
| Aggregate sentiment, identify red flags | Skill 02 + Design 07 (Dual-Sided Account Health) | ✅ |
| Generate structured brief: top 3 issues, at-risk talent, positive performers, talking points | Skill 02 §Output | ✅ |
| Delivered to Slack or email | Skill 02 `delivery_channel: action_queue + email_to_rm` (Slack OUT per `feedback_dont_flood_slack`) | ✅ (email; Slack scope-deferred) |
| Manual-review-to-2-minutes ROI | Design 04 event log captures `decision_latency_ms` on every approval | ✅ |

**§13.3 coverage: 7 / 7 rows ✅** (Slack-delivery deliberately deferred per locked memory; not a coverage gap.)

---

## §13.4 — Customer Intelligence Hub Q&A examples

| EDGE example query | Design artifact(s) | Coverage |
|---|---|---|
| "How many people at Mendota feel burned out?" | Design 01 retrievers + Skill 01 burnout-signal taxonomy | ✅ |
| "Which Helix talent flagged the AI tool as impacting their work value?" | Design 01 retrievers + Skill 01 AI-displacement signal + Skill 10 (cross-customer slice) | ✅ |
| "Prep me for my Pinnacle meeting" | Skill 02 RM-initiated trigger path | ✅ |
| "Which talent across ALL accounts have raised pay concerns this quarter?" | Skill 10 (cross-account-pattern-finder) + Skill 01 pay-concern signal | ✅ |
| "Has sentiment at TechCorp improved or declined since we launched their AI tool?" | Design 01 bi-temporal `as_of` query; Design 07 health trajectory | ✅ |
| "Who are my strongest ambassadors at Vertex?" | Skill 06 (advocacy) | ✅ |

**§13.4 coverage: 6 / 6 rows ✅**

---

## §13.5 — RM Job Description (six responsibility areas)

### Customer Success & Relationship Management
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Conduct EBRs | Skill 02 (EBR is one calendar-trigger path of the briefing skill) | ✅ |
| Manage renewals end-to-end | Skill 03 (renewal-watcher) | ✅ |
| Kickoff calls with new customers | Skill 08 (onboarding) | ✅ |
| Proactive feedback gathering | Design 02 (Signal Source Adapters ingest passively) + Design 03 (Action Queue surfaces proactively) | ✅ |
| Drive product adoption | **Deferred to Phase 2 (§12 #7)** — `product-adoption-monitor` skill not in Phase 1 | ⚠️ deferred |
| Trust-based stakeholder relationships | Design 06 (Per-Profile Markdown — Stakeholders section) + Skill 02 (briefing uses it) | ✅ |

### Talent Relationship & Engagement
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Owner of placed Talent | Design 07 (Dual-Sided Account Health — talent-side first-class) | ✅ |
| Quarterly check-ins, no slippage | Skill 04 (talent-care) | ✅ |
| Support partner for Talent issues | Skill 05 (escalation-router) + Skill 09 (coaching-signal-router) | ✅ |
| Coach Talent for long-term success | Skill 09 (coaching-signal-router) | ✅ |
| Cohesive customer + Talent experience | Design 07 (Dual-Sided Account Health) + Design 06 (parallel Customer + Associate profiles) | ✅ |

### Issue Resolution & Escalation Management
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Primary escalation point | Skill 05 (escalation-router) + Design 03 (Action Queue routing) | ✅ |
| Proactive risk monitoring | Design 07 (Dual-Sided Account Health, health-tier-changed events) + Skill 03 (renewal-watcher) + Skill 01 (signal extraction) | ✅ |
| Track issues, resolutions, outcomes | Design 04 (Event Log + Reasoning Capture; full action lifecycle) | ✅ |

### Strategy & Operations
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Implement initiatives | **Organizational; not a Pulse capability (§13.5 row reads "Organizational, not product")** | N/A |
| Track adoption, satisfaction, retention, performance | Design 08 (CEO View) + Design 04 (event log aggregations) | ✅ |
| Ensure compliance | §6 rule 2 (AWS-only + audit log standing rule) + Design 09 (Three-Tier Role Model RBAC enforcement) | ✅ |
| Recognition + advocacy programs | Skill 06 (advocacy) + Skill 07 (recognition) | ✅ |

### Monitoring & Reporting
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Collect health metrics, renewal forecasts, churn, usage | Design 07 (Dual-Sided Account Health) + Design 04 (event log) + Design 08 (CEO View synthesizes) | ✅ |
| Document customer workflows, Talent feedback, success plans | Design 06 (Per-Profile Markdown Layer) + Design 01 (Episodes as graph provenance) | ✅ |
| Regular leadership reports | Design 08 (CEO View — weekly cadence; monthly rollup) | ✅ |

### Communication & Stakeholder Engagement
| JD ask | Design artifact(s) | Coverage |
|---|---|---|
| Bridge customers / Talent / internal teams | Skill 05 (escalation-router routes to right internal team) + Design 03 (Action Queue) | ✅ |
| Transparent proactive communication | Skill 03 (renewal-watcher email drafts) + Skill 04 (talent-care) + Skill 07 (recognition) + Design 04 audit log | ✅ |
| Effective communication channels | Design 03 (Action Queue dispatch: email + SFDC + Calendar) | ✅ |

**§13.5 coverage: 23 / 24 rows ✅** (one row deferred to Phase 2 — `product-adoption-monitor`; explicit and pre-approved per §12 #7. One row marked N/A as "organizational, not product" per the doc itself.)

---

## §13.6 — Where Pulse exceeds the EDGE doc

| Pulse upgrade | Design artifact(s) | Coverage |
|---|---|---|
| 1. Action Queue + agentic action proposals | Design 03 (Action Queue) + Design 04 (event triplet) | ✅ |
| 2. Three-graph architecture | Design 01 (Three-Graph Composition) + Design 06 (Per-Profile Markdown — narrative complement) | ✅ |
| 3. Multi-axis sentiment vector | Skill 01 §"Signal taxonomy" §"Sentiment vector" | ✅ |
| 4. Talent-side workflows as first-class | Design 07 (Dual-Sided Account Health) + Design 06 (Associate profile) + Skill 04 / 09 | ✅ |
| 5. Renewal Watcher | Skill 03 | ✅ |
| 6. Escalation Router | Skill 05 | ✅ |
| 7. Auto-generated leadership reports | Design 08 (CEO View) | ✅ |
| 8. Demo HTML fallback | Design 08 §"Demo HTML fallback" + Design 12 Scene 6 | ✅ |
| 9. Signal Source Adapter pattern (pluggable from day 1) | Design 02 (Signal Source Adapter) | ✅ |

**§13.6 coverage: 9 / 9 rows ✅**

---

## Summary

| Section | Rows | Covered | Deferred | N/A | Gap |
|---|---|---|---|---|---|
| §13.2 | 9 | 9 | 0 | 0 | 0 |
| §13.3 | 7 | 7 | 0 | 0 | 0 |
| §13.4 | 6 | 6 | 0 | 0 | 0 |
| §13.5 | 24 | 22 | 1 | 1 | 0 |
| §13.6 | 9 | 9 | 0 | 0 | 0 |
| **Total** | **55** | **53** | **1** | **1** | **0** |

- **Deferred:** §13.5 "Drive product adoption" — Product Adoption Monitor skill explicitly filed for Phase 2 per PM_CONTEXT §12 #7. Not a coverage gap by definition.
- **N/A:** §13.5 "Implement initiatives" — labeled by the doc itself as organizational, not product. Not a coverage gap.

**Phase 2 coverage verdict: complete. No gaps that block Phase 3 advancement.**

---

## Cross-references

Every design artifact carries its own §13 Coverage section. This walk consolidates them. Source of truth for individual artifact mappings:

- Design 01 — §"EDGE Coverage references"
- Design 02 — §"EDGE Coverage references"
- Design 03 — §"EDGE Coverage references"
- Design 04 — §"EDGE Coverage references"
- Design 05 — §"EDGE Coverage references" (skill-by-skill mapping)
- Designs 06–12 — §"EDGE Coverage references" in each file
- Skills 01–10 — §"EDGE Coverage" in each spec

---

## Sign-off

Per §13.7 ("Coverage verification at phase gates"), Phase 2 (Design) gate is **CLEARED** for coverage. Remaining DoD items: spike memos exist ✅, design artifacts exist ✅, no application code written ✅, no design artifact names underlying tech user-facing ✅, Phase 2 questions appended (Q21–Q113, see `99_open_questions.md`).

The PM appends the Session log entry to PM_CONTEXT.md §9 per §7.6 / §4.6 after reviewing this report.

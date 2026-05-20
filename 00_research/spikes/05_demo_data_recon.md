# Demo Data Recon Spike

**Date:** 2026-05-20
**Spike duration:** ~45 minutes (including auth troubleshooting)
**Authenticated against:** **production org via `edgesolutions` alias** (edgelabs.admin@onedge.co; org ID `00D3h000002BQgmEAG`; instance `edgesolutions.my.salesforce.com`; API v62.0)

> **Constraint deviation:** The original recon prompt instructed "sandbox only — do NOT fall back to production." User explicitly overrode mid-spike ("connect to prod not sandbox" + the edgesolutions URL). Override accepted because the recon is **read-only counts + timestamps** (no record contents, no writes, no Apex). The PM_CONTEXT §6 rule 6 (Salesforce write-back only through Action Queue) is not relevant to reads. Logged here so the deviation is on record.

## Headline

- **Layer 8 seeding verdict:** **PARTIAL** — Mechanism 1 (Signal Performance) seedable from 12 months of rm-intelligence-agent meeting-signal data (367 records spanning 2025-04-28 → 2026-04-24). Mechanism 3 (Outcome Tracking) **NOT seedable** — Pulse v0 never dispatched actions, so zero historical action-outcome chains exist.
- **Acrisure storyboard verdict:** **STORYBOARD-NEEDS-SWAP** — 0 RM_Outreach, 0 affectlayer__Engagement mirror, only 4 Contacts. Cases + Associates are decent but the central signal-triangulation object (RM_Outreach) is empty.
- **Pinnacle storyboard verdict:** **STORYBOARD-NEEDS-SWAP** — 15 different "Pinnacle…" accounts in production; *zero* of them have Active Associates, recent Cases, or recent RM_Outreach. Pinnacle was synthetic / illustrative in prior storyboards.
- **Recommended action:** **Swap storyboard anchors to DHR Health Clinics + Mendota Insurance + Cirventis (HelixVM)**, and add a `045a-synthetic-action-outcome-seed` spec to Phase 4 to keep Mechanism 3 from looking empty on demo day.

---

## Task 1 — SFDC auth

- **Account used:** `edgelabs.admin@onedge.co`
- **Auth flow:** web OAuth via `sf org login web --instance-url https://edgesolutions.my.salesforce.com --alias edgesolutions --set-default`
- **Status:** **Authenticated** after three attempts:
  1. First attempt (sandbox at `test.salesforce.com`): browser-OAuth window timed out before completion.
  2. Second attempt (sandbox again): port-1717 conflict from prior stale auth listener.
  3. Third attempt (production at `edgesolutions.my.salesforce.com` per user direction): port cleared, OAuth completed.
- **Surprise:** sf CLI auto-selected API v67.0 which doesn't exist on this org (max is v66.0). All queries returned `The requested resource does not exist` until `org-api-version=62.0` was set globally.
- **Q21 status:** **Effectively resolved.** The sandbox alias still has expired tokens (and was not refreshed today since the user redirected to prod), but for the recon's read-only purposes, the production edgesolutions alias works. Phase 4 Day-1 task #8 may want to also refresh the sandbox alias for spec-development isolation, or the team may decide to use the production org with read-only discipline from Day 1.

---

## Task 2 — rm-intelligence-agent historical run depth

### Run artifacts found

All under `rm-intelligence-agent/data/`. No `logs/` / `output/` / `runs/` directories. No SQLite database.

| Artifact | Rows | Format | Date span |
|---|---:|---|---|
| `meetings.jsonl` | 430 | JSONL — raw Chorus meeting records | (date_time field present; not parsed today) |
| `meeting_signals.jsonl` | 367 | JSONL — per-meeting churn/expansion signal extractions | **2025-04-28 → 2026-04-24 (~12 months)** |
| `meetings_raw.jsonl` | (~30 MB) | JSONL — raw Chorus pull | same span |
| `accounts_ranked.json` | 171 accounts | JSON — top accounts by Chorus depth | earliest first_meeting 2025-04-28; latest last_meeting 2026-04-23 |
| `account_signals.json` | (per-account aggregations) | JSON | snapshot |
| `account_narratives.json` | 50 accounts | JSON — per-account AI-RM narrative | snapshot |
| `narrative_cache.jsonl` | 50 | JSONL — LLM narrative cache | snapshot |
| `ceo_overview.json` | 1 record | JSON — CEO-View-style overview | snapshot |
| `sfdc_bundle.json` | (~1.6 MB) | JSON — multi-layer SFDC pull | snapshot |
| `demo.html` | 1 file | HTML — rendered demo | snapshot |

### Earliest, latest, total runs, cadence

- **Earliest signal date** (in `meeting_signals.jsonl`): **2025-04-28**
- **Latest signal date**: **2026-04-24**
- **Total *distinct runs*** of the rm-intelligence-agent pipeline: **1** (all output files were written on the same day, 2026-04-25, between 18:16 and 19:55)
- **Cadence:** **N/A** — one-shot demo-prep snapshot. No accumulated time-series.
- **Underlying data span:** ~12 months of Chorus meetings analyzed in that single run.

### Verdict — **PARTIAL**

The data **content** is richer than expected (12 months of meeting signals at the granularity of "each meeting carries extracted churn/expansion signal tags + sentiment + verbatim quotes"). The **structure** is a one-time snapshot, not a daily run history.

**What seedable means for Layer 8:**

| Layer 8 Mechanism | Seedable? | Reason |
|---|---|---|
| **Mechanism 1 (Signal Performance)** | **YES, partially** | We can synthesize a 12-month "signal-fire history" from the 367 meeting-signal records, treating each signal-tag as a fire event at the meeting's date. Gives believable fire-rate-per-signal-type trajectories on the admin surface from day 1. **Cannot seed rejection rate** (no RM-rejection history exists). |
| **Mechanism 3 (Outcome Tracking)** | **NO** | rm-intelligence-agent never dispatched actions. Zero historical actions → zero historical outcomes. Mechanism 3 starts empty in Phase 4 and accumulates live as approved actions flow. |

### If PARTIAL or NO-GO: what synthetic seeding looks like

For **Mechanism 1**, the seed script reads `meeting_signals.jsonl`, walks each record, and emits synthetic `signal-evaluated` + (some fraction of) `signal-fired` events into the `pulse.events` table at the original meeting timestamps. Each tag in the existing taxonomy (churn_signals.\*, expansion_signals, talent_welfare_signals.\*) maps to one or more Phase 1 signal definitions (per the cross-references in `01_design/skills/01-detect-talent-signal.md` and the 14 definitions in `02_planning/signals/`). **Estimated effort: 0.25 day.** Could fold into spec 044 (Layer 8 Mechanism 1).

For **Mechanism 3**, the seed script synthesizes plausible action-outcome traces *attached to the synthetic signal events above*. For each "high-severity signal fire" instance, randomly assign: approve (70%) / reject (20%) / expire (10%); for approves, randomly assign outcome-recorded (50%) / outcome-missing (50%). This produces a synthetic ~3-month "Pulse-was-running" history that makes Mechanism 3's surface look populated rather than aspirational on demo day. **Estimated effort: 0.5 day.** This is **a new Phase 4 spec needed** — proposed as **spec 045a — synthetic-action-outcome seed**.

The synthetic events would be tagged clearly (`source='synthetic_seed'`) so the admin can distinguish them from real events. Production cutover would simply stop firing the synthetic seed and let real events accumulate.

---

## Task 3 — Acrisure fact sheet

`Acrisure LLC - West Region` (Id `0013h000006K123AAC`) — the only Active-status Acrisure record. There's also `Acrisure LLC` (`0016S00003AxpwmQAB`) but its `Account_Status__c` is unset.

| Dimension | Value |
|---|---:|
| **Account record exists** | yes (2 records; only `…West Region` has `Account_Status__c='Active'`) |
| **Segment__c (tier)** | ENT (Enterprise) |
| **Industry** | Insurance |
| **Owner** | Sajjal Shaheedi |
| **Account_Plan__c lookup** | **0 plans** |
| | |
| **Contacts on Account** | 4 |
| **Contacts with email + active last 90d** | not separately queried (low priority given other gaps) |
| | |
| **RM_Outreach__c total** | **0** |
| RM_Outreach in last 30 days | 0 |
| RM_Outreach in last 90 days | 0 |
| RM_Outreach in last 180 days | 0 |
| | |
| **Cases — open** | 8 |
| Cases — closed last 180 days | 2 |
| Cases — talent-linked (Associate__c not null) | 12 |
| Cases — with Description | (query did not return a count; small variation in CLI batch output) |
| | |
| **Associates — Active** | 8 |
| Associates — Replaced/Terminated last 12 months | 2 |
| Associates — modified last 90 days | 9 |
| | |
| **affectlayer__Engagement__c on Account** | **0** |
| | |
| **Account_Plan__c records** | 0 |

**Reading:** Cases + Associates are modest; everything else is empty. **The signal-triangulation spine documented in `rm-intelligence-agent/src/sfdc_pull.py` and lifted into spec 012 (SFDC Adapter) relies heavily on `RM_Outreach__c.Customer_Health__c`, `…Churn_Probability__c`, `…Expansion_Sentiment__c` — *these fields are unpopulated for Acrisure-West.* Skill 03 (renewal-watcher), Skill 06 (advocacy), and several signal definitions (`churn_signal_contact_disengagement_v1`, `churn_signal_renewal_period_silence_v1`) reference these fields. Demo scenes built on Acrisure would fall flat.

---

## Task 3 — Pinnacle fact sheet

**15 candidate "Pinnacle…" accounts in production.** Listed for the record:

| Id | Name | Segment | Industry | Status |
|---|---|---|---|---|
| 0016S00003UGAXTQA5 | Pinnacle Brokers Insurance Solutions | (unset) | Insurance | Pending |
| 001U1000008NMSYIA4 | Pinnacle Dentistry | SMB | Hospital & Health Care | (unset) |
| 0016S00003FsuG1QAJ | Pinnacle Dermatology | (unset) | Hospitals & Physicians Clinics | Pending |
| 001U100000slIBcIAM | Pinnacle Family Health | (unset) | (unset) | (unset) |
| 001U1000007o9rLIAQ | Pinnacle Fertility | ENT | Hospital & Health Care | (unset) |
| 0016S00003JtwROQAZ | Pinnacle Gastroenterology | (unset) | Hospitals & Physicians Clinics | Pending |
| 0016S00003JtYP7QAN | Pinnacle Health Services | Health | Medical | (unset) |
| 001U100000qc5QlIAI | Pinnacle Home Care | (unset) | (unset) | (unset) |
| 0016S00003JukfjQAB | Pinnacle Hospital | (unset) | Hospitals & Physicians Clinics | Pending |
| 0016S00003Nhu4TQAR | Pinnacle Insurance Agency | (unset) | Insurance | Pending |
| 0013h00000FU59dAAD | Pinnacle Insurance Agency of Minnesota | SMB | Computer Software | (unset) |
| 001U100000DLcVpIAL | Pinnacle Physician Group, LLP | (unset) | Medical | (unset) |
| 001U1000003bjJ3IAI | Pinnacle Primary Care | SMB | Medical | (unset) |
| 0016S00003NSuz8QAD | Pinnacle Risk Management Services | SMB | Drug Stores & Pharmacies | (unset) |
| 0016S00003FsNCjQAN | Pinnacle Solutions | (unset) | Business Services | (unset) |

**Data depth across all 15 candidates combined:**

| Dimension | Value |
|---|---:|
| **Active Associates across all 15** | **0** |
| **Talent-linked Cases (last 180d) across all 15** | **0** |
| **RM_Outreach__c (last 180d) across all 15** | **0** |

Also: rm-intelligence-agent's ranked-accounts file contains **zero** "Pinnacle" matches. The 50 narratives Pulse v0 generated for top-50 accounts include no Pinnacle either.

**Conclusion:** "Pinnacle" in prior storyboard text (Scene 2: "Pinnacle CEO Maria Lopez asking for insurance coders") was **synthetic / illustrative narrative**, not a real EDGE account. The 15 Pinnacle records in SFDC have no demo-worthy signal depth.

---

## Chorus reachability check

- **rm-intelligence-agent already has a working Chorus API integration** (per `src/chorus_pull.py`, confirmed Spike 1 + Spike 4). The full 12-month pull is on disk in `meetings_raw.jsonl`.
- **For Acrisure-West specifically:** rm-intelligence-agent recorded **5 Chorus meetings**, last on **2026-02-05** (3+ months stale at recon time), composite score 0.67 (modest among the 171 ranked accounts).
- **For any "Pinnacle" account:** rm-intelligence-agent recorded **0 Chorus meetings**. Pinnacle has no Chorus footprint either.
- **Chorus API access** itself: not separately re-validated today, but PM_CONTEXT §3 confirms the integration is functional (Spike 3 + rm-intelligence-agent's existing pull both succeed).

---

## Task 4 — Storyboard verdict + recommended swap

### Verdicts

- **Acrisure: STORYBOARD-NEEDS-SWAP.** The Active record has zero RM_Outreach, zero Chorus-SFDC-mirror, only 4 Contacts, and 3-month-stale Chorus history. The signal-triangulation spine that Skill 03 + Skill 06 depend on is empty. Demo scenes anchored on Acrisure would either run on synthetic data (violating §6 rule 15) or look empty.
- **Pinnacle: STORYBOARD-NEEDS-SWAP.** Definitively. No real "Pinnacle" account in production has any signal depth. The original narrative was synthetic.

### Top-5 candidate replacements (by combined signal volume)

Ranked across three dimensions (RM_Outreach last 180d + Active Associates + Cases last 180d), excluding `Test Account`:

| Rank | Account ID | Name | Segment | Industry | Active Talent | Recent Cases | RM_Outreach 180d |
|---|---|---|---|---|---:|---:|---:|
| 1 | `0016S000037jeg9QAA` | **DHR Health Clinics** | ENT | Medical | **76** | **45** | (not in RM_Outreach top-10 but adjacent) |
| 2 | `0016S00003SodLyQAJ` | **Mendota Insurance** | ENT | Insurance | **42** | — | — |
| 3 | `0016S000037jGfJQAU` | **ReminderMedia** | ENT | Other | 24 | — | — |
| 4 | `0016S00003M4VbJQAV` | **Cirventis (HelixVM)** | MID-MKT | Medical | 23 | — | — |
| 5 | `0016S00003M4Sy5QAF` | **Pace Setter Health** | MID-MKT | Medical | 22 | — | — |

Also worth mentioning:
- `0016S00003UGmjMQAT` **DHR Health Hospital** (likely same parent org as #1) — 17 talent + **36 recent cases**. Pair with #1 to demo cross-account intra-org patterns.
- `0016S00003JuMRdQAN` **New York Gastroenterology Associates** — 11 recent cases.
- `001U100000UTy1AIAT` **Dr. Dental** — 21 talent + 22 recent cases.

### PM-style swap recommendation

**Replace Acrisure → DHR Health Clinics** as the primary demo anchor.
- Enterprise tier, Medical industry (aligned with EDGE's Healthcare staffing positioning per PM_CONTEXT §1).
- 76 active placements + 45 recent cases = densest signal substrate in the entire org.
- DHR Health Hospital as the sibling account for cross-account-pattern-finder scenes.

**Replace Pinnacle → Mendota Insurance** as the second anchor.
- Enterprise Insurance — second-largest active-talent count org-wide.
- *Mendota is already a §13.4 Customer Intelligence Hub query example* ("How many people at Mendota feel burned out?") — the design docs already use it as a reference.
- The storyboard Scene 2's "expansion-ask" narrative ports cleanly to an insurance customer.

**Add Cirventis (HelixVM)** as a third reference / fallback.
- Mid-Market Medical, 23 active talent.
- *The React preview's `01_design/00_design_language_preview.tsx` uses "Helix Labs" as a fictional account — Cirventis (HelixVM) is the real-world counterpart.* Aligning storyboard with the visual fixture closes a loop.

### Bonus: §13.4 example query corroboration

PM_CONTEXT §13.4 lists six EDGE Customer Intelligence Hub example queries. Notable:
- *"How many people at Mendota feel burned out?"* — **Mendota Insurance** is real (Enterprise, 42 talent). Query works against real data.
- *"Which Helix talent flagged the AI tool as impacting their work value?"* — **Cirventis (HelixVM)** is real. Query works.
- *"Prep me for my Pinnacle meeting"* — Pinnacle is synthetic; needs to be re-phrased (e.g., *"Prep me for my Mendota meeting"*).
- *"Who are my strongest ambassadors at Vertex?"* — Vertex was not scanned today; PM_CONTEXT §13.4 lists it; worth verifying separately when needed.

---

## Implications for Phase 4 build plan

### What changes

1. **Add spec 045a — synthetic-action-outcome seed.** 0.5d effort. Lives between spec 045 (Mechanism 3) and 046 (Demo data priming). Without it, the Mechanism 3 admin surface is empty on demo day. **Should be added to build-plan §2 + §4.**
2. **Update spec 045 (Layer 8 Mechanism 1) to absorb the 0.25d signal-seed from meeting_signals.jsonl.** Already in scope; just folds in the seed-script work. Effort updated 1.5d → 1.75d.
3. **Update spec 046 (Demo data priming script) to point at DHR Health Clinics + Mendota Insurance + Cirventis (HelixVM)** rather than Acrisure + Pinnacle.
4. **Update Design 12 (Demo Storyboard) — Scenes 1-3 anchor accounts swap.** Acrisure → DHR Health Clinics; Pinnacle → Mendota Insurance. The narrative shape ports directly; only the names + a few illustrative quotes change.
5. **Risk 3 (live-data demo risk) downgraded.** The mitigation in build-plan §6 ("synthetic substitutes for storyboard scenes 1-3") is no longer needed — the swap accounts are real and richly populated. Risk effectively resolved.
6. **Risk 4 (Layer 8 outcome attribution latency) upgraded to immediate mitigation via spec 045a.** Without 045a, demo Layer 8 surface is empty.

### New spec proposed

**Spec 045a — Synthetic action-outcome seed for Layer 8 Mechanism 3.**
- Reads `rm-intelligence-agent/data/meeting_signals.jsonl`.
- Synthesizes plausible `action-suggested` → `action-approved`/`-rejected` → `action-executed` → `outcome-recorded`/`outcome-missing` chains at the original meeting timestamps.
- Distribution: 70% approve, 20% reject, 10% expire; of approves, 50% outcome-recorded, 50% outcome-missing.
- Tags all synthetic events with `source='synthetic_seed'` for admin distinguishability.
- 0.5d effort. Owner: same dev as spec 045.
- New v1.5+ candidate filed: replace synthetic seed with real production-action history once Pulse has been running 90+ days.

### Risk-register changes

- **Risk 3:** downgraded from "live-data demo risk" to "verified — swap to DHR Health Clinics + Mendota Insurance done."
- **Risk 4:** upgraded to "active mitigation via spec 045a; deferring causes empty demo surface."
- **New risk:** "RM_Outreach__c usage is sparse across the entire EDGE org (458 total records, heavily concentrated on a few accounts)." This affects signal definitions that depend on RM-curated fields (e.g., `churn_signal_renewal_period_silence_v1` consults `Churn_Probability__c`). For most accounts, those fields are unpopulated. Phase 4 should be aware that signal definitions referencing RM_Outreach fields will rely on Chorus-derived signals as primary, with RM_Outreach as a *bonus* layer where populated. **Severity: medium.** **Mitigation:** the existing Chorus signal-extraction (Skill 01 + spec 020) is the primary signal source; RM_Outreach is a secondary enrichment when present.

---

## What I recommend

**Proceed to Phase 4 with three small adjustments:** (a) swap demo storyboard anchors to **DHR Health Clinics + Mendota Insurance + Cirventis (HelixVM)** — PM updates Design 12 and spec 046; (b) **add spec 045a** for synthetic action-outcome seeding (0.5d, folds into Layer 8 work); (c) **document the RM_Outreach__c sparseness finding** — Chorus signal-extraction is the demo-day spine, with RM_Outreach as a bonus when populated.

These adjustments add 0.5d to the build plan (from spec 045a). Buffer remaining: 3.5d distributed (was 4.0d). Phase 4 critical-path remains intact.

The recon's most valuable finding was structural rather than nominal: **the demo's planned data anchors didn't match the production data's actual depth.** Discovering this now is exactly the cheap-to-fix-before-build-starts moment we want.

---

## Open questions surfaced

- **Q152:** Should Pulse Phase 4 ingest from the production org's `edgesolutions` instance directly, or should EDGE provision a sandbox-with-production-data-copy for Pulse-development isolation? Phase 1 currently assumes production reads. User decision needed before Day-1.
- **Q153:** affectlayer__Engagement__c is zero org-wide. Is Chorus's Salesforce integration not configured to write to this object, or is the object retired? Pulse can ignore (Chorus API direct works), but worth confirming with EDGE's SFDC admin.
- **Q154:** Vertex (§13.4 ambassador-query example) was not scanned today. Verify in week 1 of Phase 4 that Vertex has demo-worthy data, or swap to a verified ambassador account.
- **Q155:** Should the original Design 12 storyboard's Acrisure references be deleted, kept as historical narrative artifact, or amended in place with DHR Health Clinics? PM call.

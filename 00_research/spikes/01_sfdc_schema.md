# Spike 1 — SFDC Schema Discovery

**Date:** 2026-05-20
**Goal:** Confirm the full in-scope Salesforce schema for Pulse, beyond what `rm-intelligence-agent` already queries. Capture object API names, key custom fields, lookup relationships, and meaningful picklist values. Output a "Schema Sync codegen feasibility" verdict.

---

## Preamble — what I'm about to do

I will (a) confirm the `sf` CLI is configured and which orgs are reachable; (b) inventory the schema that `rm-intelligence-agent` already validates against production (this is the known floor); (c) document the additional in-scope objects PM_CONTEXT names (`Account_Plan__c`, `affectlayer__Engagement__c`, plus standard `Account` / `Contact` / `Opportunity`); (d) run `sf sobject describe` against the **sandbox** alias for each in-scope object if reachable; (e) file a Schema Sync codegen feasibility verdict; (f) file any gaps as open questions.

---

## A. `sf` CLI state

```
sf version: @salesforce/cli/2.130.9 darwin-arm64 node-v23.11.0
configured orgs:
  prod        → dabeera.zaheen@healthandgroup.com  (Connected; default org)
  production  → dabeera.zaheen@onedge.co           (Connected; this is the alias rm-intelligence-agent uses)
  sandbox     → edgelabs.admin@onedge.co           (UNABLE TO REFRESH — token expired)
```

**Blocker for live sandbox describes.** The spike prompt explicitly forbids running schema describes against `production`. The `sandbox` alias is configured but the refresh token has expired (`sf org display --target-org sandbox` returns "Unable to refresh session due to: Error authenticating with the refresh token due to: expired access/refresh token"). Re-authentication requires user interaction (`sf org login web -a sandbox` or equivalent).

**Filed as Q21 in `99_open_questions.md`.** Resolution unblocks the live describe pass for any custom objects that `rm-intelligence-agent` does *not* already touch.

---

## B. Validated in-scope schema (from `rm-intelligence-agent/src/sfdc_pull.py`)

These objects/fields are demonstrably queryable in production today via the `sf` CLI against the `production` alias. This is the **schema floor** — everything below is known-good.

### B.1 `RM_Outreach__c` (custom — the "RM Object")

| Field | Type (inferred) | Notes |
|---|---|---|
| `Id` | Id | |
| `Name` | string | |
| `CreatedDate`, `LastModifiedDate` | datetime | |
| `Account__c` | lookup → Account | **load-bearing join** |
| `Associate__c` | lookup → Associates__c | optional, ties outreach to specific talent |
| `Case__c` | lookup → Case | optional, ties outreach to an open case |
| `EBR_Date__c` | date | Executive Business Review date |
| `EBR_Description__c` | longText | EBR narrative |
| `Description__c` | longText | RM notes |
| `Active_Associates__c` | int / formula | per-account active-talent count snapshot |
| `Customer_Health__c` | picklist | values TBD via describe; presently aggregated |
| `Expansion_Sentiment__c` | picklist | |
| `Satisfaction_with_Talent__c` | picklist | |
| `Customer_Priority_level__c` | picklist | likely tier proxy |
| `Competitor_Analysis__c` | text | |
| `Referral_Sentiment__c` | picklist | |
| `Churn_Probability__c` | percent / picklist | RM-recorded |
| `Expansion_Probability__c` | percent / picklist | RM-recorded |
| `Referral_Potential__c` | picklist | |
| `Recording_link__c` | url | |
| `Transcript_link__c` | url | |
| `Account_Owner_Name__c` | string (denormalized) | |
| `Annual_Revenue__c` | currency (denormalized from Account) | |

**Role in Pulse:** the RM-curated, human-authored layer of customer health. Pulse reads it as canonical RM judgment; agent proposals supplement it; the agent never overwrites it without explicit per-write approval (§6 rule 6).

### B.2 `Associates__c` (custom — placed talent)

| Field | Type | Notes |
|---|---|---|
| `Id`, `Name`, `CreatedDate`, `LastModifiedDate` | std | |
| `Account__c`, `Account__r.Name` | lookup → Account | which customer |
| `RM_Manager__c`, `RM_Manager__r.Name` | lookup → User | the RM responsible |
| `Associate_Manager__c`, `Associate_Manager__r.Name` | lookup → User | the internal manager of the talent |
| `Candidate__c` | lookup → Contact (likely) | |
| `Prior_Associate_Replaced__c` | lookup → Associates__c | **chain-of-replacement edge** |
| `Stage__c` | picklist | known values: `Active`, `Replaced`, `Terminated`, plus more TBD |
| `Risk_level__c` | picklist | |
| `Risk_Details__c` | text | |
| `Type__c` | picklist | |
| `Next_Action__c` | text | |
| `Start_Date__c`, `End_Date__c` | date | |
| `Salary__c`, `Annual_Recurring_Revenue__c` | currency | |
| `Industry__c`, `Role__c`, `Country__c` | picklist | |
| `Meetings_Count__c` | int | |
| `Description__c` | longText | |

**Role in Pulse:** the talent-side of the Account/Talent Relationship Graph. The `Stage__c` enum drives dual-sided account health (a `Replaced/Terminated` event is a leading churn indicator per `project_signal_triangulation` memory). The `Prior_Associate_Replaced__c` self-lookup captures replacement chains.

### B.3 `Case` (standard) — risk-tagged signal layer

Only **risk-tagged** cases are in scope. Filtered by `Categories__c IN (...risk values)`:

```
'Risk - Talent Competency','Risk - Poor Talent Experience','Risk - Resignation',
'Risk - Talent Professionalism','Risk - Customer Payment Failure','Risk - ADP',
'Risk – Role Change','Risk – Emergency Leaves',
'Poor Experience with Edge','Competitor','Performance','Relationship Management',
'Business Performance','Business Needs'
```

Fields in use:

| Field | Type | Notes |
|---|---|---|
| `Id`, `CaseNumber`, `CreatedDate`, `ClosedDate`, `IsClosed` | std | |
| `Subject`, `Status` | std | |
| `Categories__c` | picklist (the risk taxonomy above) | **load-bearing for signal filtering** |
| `Channel__c` | picklist | how the issue surfaced |
| `Next_Action_Marketplace_Status__c` | picklist | |
| `Issue_Types__c` | picklist (multi?) | |
| `Description`, `Details__c` | longText | narrative the agent cites |
| `Associate__c`, `Associate__r.Name`, `Associate__r.Stage__c` | lookup → Associates__c | **case-on-talent edge** |
| `AccountId`, `Account.Name` | std | |
| `OwnerId`, `Owner.Name` | std | |

**Role in Pulse:** the formal-issue layer; risk-tagged cases are graph episodes with strong signal weight. The `Categories__c` enum is the existing EDGE risk taxonomy and should be preserved in Pulse's signal schema.

### B.4 `affectlayer__Engagement__c` (Chorus-installed package)

Referenced in PM_CONTEXT `reference_sfdc_schema` as the SFDC mirror of Chorus engagements. **Not queried by `rm-intelligence-agent` directly** — that pipeline goes to the Chorus v3 API instead. In scope for Pulse because it offers an SFDC-native join key (`affectlayer__Engagement__c` ↔ Chorus conversation ID) without going outside Salesforce. **Live describe needed when sandbox auth refreshes (Q21).**

### B.5 `Account_Plan__c` (custom)

Referenced in PM_CONTEXT `reference_sfdc_schema`. **Not yet queried by `rm-intelligence-agent`.** Expected to carry strategic account plans (objectives, success criteria, renewal trajectory). High-value for Workflow 2 (briefing) and EBR Prep skill. **Live describe needed (Q21).**

### B.6 Standard objects in scope

| Object | In-scope use |
|---|---|
| `Account` | Customer entity. Already joined in current queries. Fields needed: `Id`, `Name`, `Industry`, `Owner`, plus a tier/segment custom field (likely `Tier__c` or similar — confirm via describe). |
| `Contact` | Customer-side stakeholders (champions, decision-makers, detractors). Needed for the Per-Profile Markdown Layer and Champion Tracker (§13.5 JD ask). Currently not queried by `rm-intelligence-agent`. |
| `Opportunity` | Renewal/expansion pipeline. Needed for Renewal Watcher skill (§13.5 JD ask). Currently not queried by `rm-intelligence-agent`. |
| `Event` / `Task` | Calendar entries — Workflow 2 needs "detect customer meeting on calendar 24h ahead." Calendar Signal Source Adapter likely reads from `Event` (or directly from Google/MS Calendar API). |
| `User` | RM identity, ownership. Standard fields. |

---

## C. Relationship map (current understanding)

```
                          Account (Customer)
                              │
            ┌─────────────────┼──────────────────┬────────────────────┐
            │                 │                  │                    │
            ▼                 ▼                  ▼                    ▼
      Opportunity        Contact          Associates__c          Account_Plan__c
       (renewal,         (stakeholder,    (placed talent)        (strategic plan)
        expansion)        champion)             │
                                                │
                                  ┌─────────────┼─────────────┐
                                  ▼             ▼             ▼
                              Case          RM_Outreach__c   Prior_Associate_Replaced__c
                            (risk-tagged    (RM-curated      (self-edge: replacement chain)
                             signal)         judgment)

      affectlayer__Engagement__c (Chorus mirror) — joins Account/Contact to Chorus conversation
      Event / Task — calendar signals; Workflow 2 trigger
```

The relationship graph is **not flat**: `Case` joins to *both* `Account` (via `AccountId`) and `Associates__c` (via `Associate__c`). The `Prior_Associate_Replaced__c` self-lookup gives Pulse the chain-of-replacement edge for free.

---

## D. Schema Sync codegen feasibility — verdict

**GO with caveats.** The Schema Sync pattern lifted from `SDRbot-main` (introspect SFDC → codegen typed agent tools) is feasible against this schema:

1. **Object surface is small and well-bounded** — ~8 objects (6 custom + 2 standard widely used) plus 2–3 ancillary (`Event`, `User`, `Account_Plan__c`). Bounded enough that codegen output is reviewable rather than enormous.
2. **Custom fields are consistently named** with `__c` suffixes and meaningful semantic prefixes (`Risk_`, `Customer_`, `EBR_`, etc.). The agent can reason about them by name without exotic mapping.
3. **Picklist values are stable** (the risk taxonomy alone has 14+ values already enumerated in production-validated code). Codegen should emit them as TypeScript/Python literal types for compile-time safety.
4. **Lookups are well-typed** — the `__r.Name` traversal pattern works cleanly via SOQL relationship queries, which means generated tools can return typed nested objects.
5. **Caveat 1:** picklist values for `Customer_Health__c`, `Expansion_Sentiment__c`, etc. are referenced in code but not enumerated. Live describe needed (Q21) to lock the full enum surface before codegen.
6. **Caveat 2:** `Account_Plan__c` and `affectlayer__Engagement__c` not yet validated by working code. Live describe needed (Q21).
7. **Caveat 3:** the `production` org alias is `production`, not the typical `prod`. Codegen must emit `--target-org production` (PM_CONTEXT `reference_sfdc_access` memory locks this).

**Recommended codegen output shape (for Phase 4 build):**
- One typed module per object (`sfdc.account`, `sfdc.rm_outreach`, `sfdc.associate`, `sfdc.case`, ...).
- Each module exports: an interface for the record shape, a `select` function (read with SOQL), a `create`/`update` action-class binding (write only via Action Queue per §6 rule 6).
- Picklist enums emitted as exhaustive literal types.
- Generated under `03_build/sfdc_typed_tools/` at build time; regenerated when schema changes.

---

## E. Open questions raised by this spike

- **Q21** — sandbox auth refresh needed to complete describe pass for `Account_Plan__c`, `affectlayer__Engagement__c`, full picklist enumerations, and any in-scope objects not currently queried by `rm-intelligence-agent`. **Blocking for Schema Sync codegen completeness, but not blocking for Phase 2 design lock** since the known schema is sufficient to design against.
- **Q22** — `Account` tier field. Pulse's tier-aware behavior rule (§6 rule 4) needs a tier picklist on `Account`. Need to confirm the field name (`Tier__c`? `Segment__c`?) and value set via describe.
- **Q23** — `Calendar` source: does Workflow 2 read from SFDC `Event` records, from Google/MS Calendar API directly, or from a workflow-engine calendar trigger? Affects which Signal Source Adapter implements the 24h-ahead trigger.

---

## F. What this spike did NOT do

- Did not run `sf sobject describe` against sandbox (sandbox auth expired; awaiting user refresh per Q21).
- Did not run any describe against `production` (spike prompt explicitly forbids; conservative-default per Phase 2 instructions).
- Did not enumerate picklist values for fields where `rm-intelligence-agent` references them by name only.
- Did not inventory Salesforce objects entirely outside the rm-intelligence-agent + PM_CONTEXT scope (e.g., Marketing Cloud objects, custom apps unrelated to RM workflows).
- Did not write any Schema Sync codegen scaffolding — that is Phase 4 build, not Phase 2 design.

---

## G. Recommendation for Phase 2 / 3 / 4

1. **Phase 2 design** can proceed using §B as the design-against schema; the Three-Graph composition and Signal Source Adapter specs do not need full picklist enums.
2. **Resolve Q21** at the user's earliest convenience by refreshing sandbox auth. Once unblocked, re-run this spike for full coverage and update §B + §C accordingly.
3. **Phase 4 build** must run the full describe pass and emit codegen *before* writing any agent tool code.

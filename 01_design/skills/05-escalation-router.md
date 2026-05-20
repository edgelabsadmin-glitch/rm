# Skill 05 — escalation-router

**Lifecycle stage:** escalation
**Phase:** 1
**Tier-aware:** yes — Enterprise escalations route to VP of Client Success automatically; SMB stay with RM.

## Trigger
**Episode-driven.** Fires on:
1. A new risk-tagged `Case` being ingested (Design 02 SFDC adapter).
2. A `raised_concern_about` edge with `urgency >= high` being created by Skill 01 from a Chorus call.
3. An `Associates__c` `Stage__c` transition to `Replaced` or `Terminated`.

## Inputs
- Retrievers required: `get_customer_context()` and `get_talent_context()` if talent is involved.
- External calls (READ ONLY): Salesforce — full Case, related Account, related Associate.
- Per-Profile Markdown read: Customer profile + Associate profile.
- Policy inputs: tier; internal team routing table.

## Behavior
Classifies the escalation by **category** (the existing risk taxonomy from `rm-intelligence-agent/src/sfdc_pull.py`'s `signal_cats`) and routes to the right internal team. Phase 1 routing table (configurable):

| Risk category | Default internal team |
|---|---|
| `Risk - Talent Competency` | Talent Dev |
| `Risk - Resignation` | Talent Ops |
| `Risk - Talent Professionalism` | Talent Dev + HR |
| `Risk - Customer Payment Failure` | Finance |
| `Risk - ADP` | Payroll |
| `Risk – Role Change` | Sales (re-scope) |
| `Risk – Emergency Leaves` | HR |
| `Poor Experience with Edge` | CS leadership |
| `Competitor` | Sales |
| `Performance` | Talent Dev |
| `Relationship Management` | CS leadership |
| `Business Performance` | Finance + CS leadership |
| `Business Needs` | Sales |

Proposes one of:
- A **Jira ticket** to the routed team (v1.5+ — Jira adapter is not Phase 1; Phase 1 substitute below).
- **Phase 1 substitute:** an email to the team alias + a SFDC Task assigned to the team's lead.

The RM gets a copy of every escalation routed from their book of business.

**Reasoning** captures: the triggering Case/edge/transition, the routing category, the chosen team, and why this team rather than another (when ambiguous).

## Guardrails
- **Do not double-route.** If a Case already has an active Escalation Action open in the queue for the same `case_id`, the skill skips.
- **Do not escalate `Stage` transitions that are immediately followed by a successor placement.** If `Replaced` is followed by a new `Active` Associate placement to the same customer for the same role within 7 days, the system has self-healed and no escalation is needed.
- **Do not route Risk-Customer-Payment-Failure to Sales.** Finance owns this category; misrouting causes friction. Hard rule.
- **Tier-Awareness for Enterprise:** also cc VP of Client Success on every Enterprise escalation regardless of category.

## Output / Proposed action shape
```yaml
action_type: escalation-routed
delivery_channel: email + sfdc_task   # Jira upgrade in v1.5+
body:
  email_draft:
    to: <team_alias_or_lead>
    cc: <rm_email, vp_cs_if_enterprise>
    subject: "Escalation: <category> @ <customer_name>"
    body: <case context + recommended action, inline-tag-rendered>
  sfdc_task:
    subject: "Escalation routed: <category>"
    description: <full citation + routed team>
    related_to: <Case.Id>
    assigned_to: <team_lead_user_id>
    due_date: <urgency-driven, default 1 business day>
modifiable_fields: [body.email_draft.body, body.email_draft.cc,
                     body.sfdc_task.description, body.sfdc_task.due_date]
```

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | RM stays primary owner; no VP notification |
| **Mid** | RM stays primary; cc VP on `urgency >= high` |
| **Enterprise** | cc VP on every escalation; suggested 24h response SLA |

Approval mode: **human-required for all tiers** — escalations are high-blast-radius and should not auto-route.

## Outcome detection
- SFDC Task closed within SLA → `outcome-recorded` type `escalation-resolved-in-sla`.
- Email reply from routed team within 48h → `outcome-recorded` type `escalation-acknowledged`.
- No movement after 5 business days → `outcome-missing` and re-queue with elevated urgency.

## EDGE Coverage
- §13.5 row "Primary escalation point" — direct implementation.
- §13.5 row "Proactive risk monitoring" — paired with `01-detect-talent-signal`.
- §13.5 row "Bridge customers / Talent / internal teams" — routing is the bridge.
- §13.6 #6 "Escalation Router — JD responsibility, absent from EDGE doc" — receipt.

## Open questions
- **Q62** — Internal-team routing table source-of-truth. Phase 1 = hardcoded; v1.5+ = configurable by Admin via the policy module's config. PM proposes: hardcoded with a v1.5 promotion to config.
- **Q63** — Team-lead User.Id mapping. The skill needs to know who leads each internal team for `assigned_to`. Hardcode or read from a custom SFDC object? PM proposes: a simple `pulse_team_leads.yaml` config in Phase 1.
- **Q64** — Jira adapter timing. §13.2 EDGE-doc mentions Jira tickets as a delivery channel; Phase 1 substitutes email+SFDC Task. Filed in §12 #10. v1.5+ candidate.

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `escalation_signal_case_pattern_v1` | **Primary consumer.** Routes pattern detection to internal teams. |
| `escalation_signal_severity_jump_v1` | **Primary consumer.** Single severe Case → immediate routing. |
| `churn_signal_competitor_mention_v1` | **High-severity cascade consumer.** `tone=switching_intent` or Case-category `Competitor` → escalation to VP-CS + Sales. |
| `talent_pay_concern_v1` | **High-severity cascade consumer.** Competing-offer auto-high → route to Finance + HR. |

Skill 05's golden-trace tests verify the **routing table** (per category → team mapping in `pulse_team_leads.yaml`) and the **deconfliction** with Skill 09 (shared rate-limit table on `(case_id, dispatch_week)` per Q76).

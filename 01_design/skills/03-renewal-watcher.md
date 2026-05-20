# Skill 03 — renewal-watcher

**Lifecycle stage:** renewal
**Phase:** 1
**Tier-aware:** yes — Enterprise renewals trigger earlier (120 days ahead); SMB later (60 days).

## Trigger
**Schedule-driven (daily 06:00 local).** Scans all Customers with an upcoming renewal milestone. Renewal milestones derive from:
1. `Opportunity` records with `CloseDate` in the next 60/90/120 days (tier-dependent) AND `Type` indicating renewal.
2. `Account_Plan__c` records whose `Plan_End_Date__c` (TBD field name per Spike 1) is in the same window.
3. Fallback: `Associates__c` records whose `End_Date__c` clusters around a similar date (placement-end-as-implicit-renewal-checkpoint).

## Inputs
- Retrievers required: `get_customer_context(customer_id)`.
- External calls (READ ONLY): Salesforce — `Opportunity` pipeline scan, `Account_Plan__c` read.
- Per-Profile Markdown read: Customer profile (Design 06).
- Policy inputs: tier.

## Behavior
For each Customer in the renewal window, the skill assesses **renewal risk** using a small rule set on the `ContextBundle`:

| Risk factor | Weight |
|---|---|
| Churn-signal count last 90d | high if ≥3 |
| Open risk-tagged Cases | high if ≥1 |
| Replacement-rate on placed talent | high if ≥30% |
| RM_Outreach `Churn_Probability__c` ≥ 0.5 | high |
| Negative-sentiment trajectory last 60d | medium |
| No RM_Outreach update in last 60d (RM is silent on a renewing account) | medium |
| Positive expansion signal in last 90d | mitigating |

If composite risk ≥ medium, propose a renewal-watch action: a draft email to the customer's primary champion + a Salesforce Task for the RM + (if risk is high) an internal flag to the VP of Client Success.

**Reasoning structure** follows Design 04 §"Reasoning capture" with explicit signal citations. Verbatim quotes are pulled into the email draft via inline tags so the RM can show evidence to the customer if needed.

## Guardrails
- **Do not draft customer-facing emails that mention specific talent risk details by name.** Reference patterns ("we've had some staffing dynamics on your account") but not individual `Associates__c.Risk_Details__c` content.
- **Do not create the Salesforce Task without approval** (§6 rule 6). The Action Queue card includes the Task as a `recommended_action`; the dispatch handler creates it only on approval.
- **No outreach to multiple customers in the same dispatch batch.** Each customer is a separate action; bulk approve is out of Phase 1 (Q37).
- **Renewal-window guard.** Do not fire for customers whose renewal is >120 days out (avoids alert fatigue).

## Output / Proposed action shape
```yaml
action_type: renewal-touch
delivery_channel: email + sfdc_task
body:
  email_draft:
    to: <champion_contact_email>
    cc: [<additional_contacts>]
    subject: "Quick check-in ahead of <renewal_window>"
    body: <inline-tag-rendered draft>
  sfdc_task:
    subject: "Renewal at risk: <customer_name>"
    description: <RM-facing summary with full citation>
    related_to: <Account.Id>
    due_date: <2_business_days>
modifiable_fields: [body.email_draft.body, body.email_draft.subject,
                     body.sfdc_task.description, body.sfdc_task.due_date]
```

## Tier variants
| Tier | Lookahead window | Default approval |
|---|---|---|
| **SMB** | 60 days | auto-approve at +2h (low blast radius) |
| **Mid-Market** | 90 days | human-required |
| **Enterprise** | 120 days | human-required; also notify VP of Client Success on high-risk |

## Outcome detection
- **Email reply received** within 7 days → `outcome-recorded` type `customer-responsive`.
- **Renewal Opportunity moves to `Closed Won`** → `outcome-recorded` type `renewal-closed`.
- **Renewal Opportunity moves to `Closed Lost`** → `outcome-recorded` type `renewal-lost` (the bad outcome).
- **No movement after 30 days** → `outcome-missing`.

## EDGE Coverage
- §13.5 row "Manage renewals end-to-end" — direct implementation.
- §13.5 row "Proactive risk monitoring" — renewal risk is a core risk category.
- §13.6 #5 "Renewal Watcher — JD responsibility, absent from EDGE doc" — this artifact *is* the receipt.

## Open questions
- **Q56** — Champion contact identification. Who is the "primary champion" at a customer? Phase 1 fallback: most-recent Chorus call participant from the customer side. Phase 2: explicit Champion field on Contact (via Per-Profile Markdown).
- **Q57** — Risk-weight tuning. The rule weights are heuristic. PM proposes: ship Phase 1 with these defaults, instrument rejection rate, tune in v1.5.
- **Q58** — `Opportunity.Type` enumeration for renewals. Confirmed via Spike 1 / Q22 — need the actual enum values.

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `churn_signal_renewal_period_silence_v1` | **Primary trigger.** This signal's existence is the renewal-watcher's principal fire condition. |
| `churn_signal_contact_disengagement_v1` | Composed into the renewal-watcher's risk model; component of the renewal-period-silence rule. |
| `churn_signal_sentiment_decline_v1` | Weighted into the renewal-watcher's risk score; a negative trajectory near renewal triggers higher severity. |
| `churn_signal_competitor_mention_v1` | If active in last 90 days near a renewal window, renewal-watcher escalates severity and adds competitor-context to the email draft. |
| `client_termination_pattern_v1` | Consumed as **account context** — increases composite churn risk for the renewal evaluation. |
| `account_silence_pattern_v1` | Consumed as **account context** — informs urgency of the resulting check-in. |
| `escalation_signal_case_pattern_v1`, `escalation_signal_severity_jump_v1` | Read-only context; an active escalation near renewal alters the email-draft tone. |

Skill 03's golden-trace tests verify the **composite-risk scoring** logic given a fixture set of (signal_state, renewal_window) combinations.

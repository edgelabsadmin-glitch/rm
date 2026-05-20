# Skill 06 — advocacy

**Lifecycle stage:** expansion
**Phase:** 1
**Tier-aware:** yes — Enterprise advocacy proposals include reference-call coordination; SMB are simpler.

## Trigger
**Schedule-driven (weekly Monday 09:00 local).** Scans the last 30 days of episodes per Customer looking for **strong positive signals** from Skill 01:
- Direct positive quotes from customer contacts (e.g., *"the team you placed has been exceptional"*).
- Expansion signals (`raised_concern_about` edges of expansion type).
- Successful issue resolutions (closed risk-tagged Cases with positive resolution sentiment).
- High `Customer_Health__c` + `Expansion_Sentiment__c` ratings.

A customer is a **strong ambassador candidate** if at least 2 distinct positive signals exist in the window AND no open high-urgency risk-tagged Cases.

## Inputs
- Retrievers required: `get_customer_context()`.
- External calls (READ ONLY): Salesforce — `RM_Outreach__c`, related `Contact`s (champion identification).
- Per-Profile Markdown read: Customer profile.
- Policy inputs: tier; existing advocacy program participation (read from `Account` custom field if it exists).

## Behavior
Surfaces ambassador candidates and proposes one of three actions per candidate:
1. **Recognition note** to the customer champion (low-stakes thank-you, Skill 07 may already cover; coordinate by mutual rate-limit).
2. **Reference-call ask** for sales to use as a sales motion.
3. **Case-study candidate** flag — if customer agrees, Pulse drafts an interview outline.

The skill leans toward **fewer, higher-quality proposals** rather than volume. Median expected output: 1–3 advocacy actions per week per RM.

**Reasoning** highlights the strongest verbatim positive quote(s) from the window — these become the headline of the action card via the `<quote>` inline tag.

## Guardrails
- **Do not propose reference-call asks to customers who declined in the last 12 months.** Track in `Account` custom field or Per-Profile Markdown.
- **Do not surface advocacy for customers with active risk-tagged Cases** of `Risk – Talent Competency`, `Risk - Resignation`, `Risk - Customer Payment Failure`, `Poor Experience with Edge`, or `Competitor`. These categories override positive signals.
- **One advocacy action per customer per quarter.** Hard rate-limit.
- **No public-facing artifacts proposed without explicit case-study consent.**

## Output / Proposed action shape
```yaml
action_type: advocacy-touch
delivery_channel: email + sfdc_task
body:
  email_draft:
    to: <champion_contact_email>
    subject: <selected from variant pool>
    body: <inline-tag-rendered, opens with verbatim quote>
  sfdc_task:
    subject: "Advocacy candidate: <customer_name>"
    description: <signals summary + proposed motion>
    related_to: <Account.Id>
  proposed_motion: <recognition | reference-call | case-study>
modifiable_fields: [body.email_draft.body, body.proposed_motion]
```

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | Recognition note only; no reference-call asks (signal-to-noise low) |
| **Mid** | Recognition + reference-call asks |
| **Enterprise** | Recognition + reference-call + case-study suggestion; cc Sales lead |

Approval mode: human-required across all tiers (advocacy customer-facing motions have brand impact).

## Outcome detection
- Reply received within 14 days agreeing to motion → `outcome-recorded` type `advocacy-accepted`.
- Reply declining → `outcome-recorded` type `advocacy-declined` (recorded for the 12-month no-ask guardrail).
- No movement within 30 days → `outcome-missing`.

## EDGE Coverage
- §13.4 example "Who are my strongest ambassadors at Vertex?" — query-time variant of this skill's logic.
- §13.5 row "Recognition + advocacy programs" — direct implementation.
- §13.6 #4 talent-side first-class — advocacy includes recognizing the talent who drove the positive signal (paired with Skill 07).

## Open questions
- **Q65** — Champion identification heuristic. Same Q56 from `03-renewal-watcher`. Filed once across skills.
- **Q66** — Case-study artifact format. Out of Phase 1 scope; v1.5+ candidate.
- **Q67** — Coordination with `07-recognition` to prevent two skills both surfacing the same positive signal. PM proposes: shared rate-limit table keyed on (Customer, week).

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `recognition_signal_advocacy_candidate_v1` | **Primary consumer.** Score determines motion type (recognition note / reference-call ask / case-study suggestion). |

Skill 06's golden-trace tests verify the **score-to-motion mapping** (0.3-0.5 → recognition; 0.5-0.75 → reference-call; 0.75+ → case-study) and the **disqualifier-list enforcement** (no advocacy on customers with active high-severity risk cases, per the signal definition's rules).

# Skill 07 — recognition

**Lifecycle stage:** recognition
**Phase:** 1
**Tier-aware:** partial — same logic across tiers; auto-approval default differs.

## Trigger
**Episode-driven.** Fires on:
1. A positive `mentions` or `raised_concern_about(positive)` edge created by Skill 01.
2. An `Associates__c` placement reaching a milestone (90 days `Active`, 180 days `Active`, 1 year `Active`).
3. A risk-tagged Case being closed with `Status = Resolved` and positive resolution sentiment.
4. A customer reply to a Pulse-dispatched email being net-positive (parsed by a lightweight sentiment pass).

## Inputs
- Retrievers required: `get_customer_context()` if customer-side; `get_talent_context()` if talent-side; `get_rm_context()` for RM recognition.
- External calls (READ ONLY): Salesforce — current owner of the Associates / Account.
- Per-Profile Markdown read: relevant profile.
- Policy inputs: none beyond default tier-aware auto-approve.

## Behavior
Drafts a short, warm recognition note. Three audience types:
- **Customer-facing** (champion at the customer): thanks for partnership / quick mention of a recent positive moment.
- **Talent-facing** (placed Associate): congratulations on the milestone / acknowledgment of positive feedback.
- **Internal-facing** (RM): recognition note from VP of Client Success to the RM acknowledging their work. Drafted as if from the VP; the VP approves before send.

Volume is expected to be the highest of any skill — recognition fires whenever positive signals exist. Phase 1 default approval = **auto-approve at +1h** (low blast radius, low risk; per Design 04 policy rule 3).

**Reasoning** is compact: one verbatim quote (or one milestone fact), one sentence on the recognition moment, the draft.

## Guardrails
- **No recognition during active risk-tagged Cases at the same Customer.** Even with a positive signal, sending a "thanks for being great" note while a separate fire burns is bad timing. The skill defers until the Case is resolved.
- **No talent recognition for placements <30 days old.** Avoids generic "welcome aboard"-style content that misses the moment.
- **No internal RM recognition more than once per RM per week.** Volume cap.
- **No bulk send.** Each recognition is one Customer or one Talent or one RM. (See Q37 — bulk approve is v1.5+.)

## Output / Proposed action shape
```yaml
action_type: recognition-note
delivery_channel: email
body:
  audience: <customer | talent | rm>
  email_draft:
    to: <target_email>
    cc: <relevant_witnesses>
    subject: <short, warm>
    body: <2-4 sentences; one verbatim quote or milestone fact>
modifiable_fields: [body.email_draft.body, body.email_draft.subject]
```

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | Auto-approve at +1h |
| **Mid** | Auto-approve at +1h |
| **Enterprise** | Auto-approve at +1h for talent + RM audiences; **human-required** for customer-facing audiences (Enterprise customer-facing always passes a human gate) |

## Outcome detection
- Reply received within 7 days → `outcome-recorded` type `recognition-acknowledged`.
- No reply (this is fine for recognition) → `outcome-missing` not emitted; recognition is one-way by intent.

## EDGE Coverage
- §13.5 row "Recognition + advocacy programs" — paired with Skill 06.
- §13.5 row "Effective communication channels" — recognition is a positive-signal communication.
- Indirect support for §13.5 "Trust-based stakeholder relationships" — recognition is trust-currency.

## Open questions
- **Q68** — Sender identity. Customer-facing recognition: from RM's mailbox? From a VP mailbox? From an EDGE alias? PM proposes: RM mailbox via OAuth (consistent with Skill 03).
- **Q69** — RM-facing recognition surface. From whom does this "feel" like it comes? PM proposes: drafted as if from VP of Client Success, approval-required from the VP. User to confirm whether VP wants this surface.
- **Q70** — Sentiment-detection for triggering on positive customer replies (item #4 above). What threshold of positive? PM proposes: simple LLM-judged binary with audit log.

## Owned signals (Phase 3 cross-reference)

Skill 07's triggers (per its spec) are episode-driven on positive-signal events, milestone events, resolved Cases, and positive-reply detection. The Phase 1 signal library does not currently have a dedicated `recognition_trigger_v1` signal — Skill 07 fires on **structural events** (milestone dates, Case `Status='Resolved'` transitions) and on **Skill 01's `positive_quote` tag emissions** (which are consumed via the `mentions` edges in Graphiti rather than via a separate signal definition).

| Signal ID | Role |
|---|---|
| `recognition_signal_advocacy_candidate_v1` | **Coordination consumer.** Shared rate-limit table with Skill 06 prevents double-surfacing the same positive signal (Q67). Skill 07 defers to Skill 06 when the advocacy score is high enough to warrant the heavier motion. |

**v1.5+ candidate:** a dedicated `recognition_signal_v1` definition consolidating Skill 07's structural-event triggers + Skill 01's positive_quote tags. Phase 1 keeps Skill 07's trigger logic implicit (in the skill code) because the structural-event triggers are simpler than the LLM-driven definitions in the rest of the library; the no-black-box rule is still satisfied because the trigger conditions are documented in the skill spec itself. Filed in `99_open_questions.md` as Q146.

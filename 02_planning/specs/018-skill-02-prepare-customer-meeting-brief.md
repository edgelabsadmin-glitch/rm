# Spec 018 — Skill 02 — prepare-customer-meeting-brief

**Maps to:** §14 Skills (Skill 02); Design 05 + `01_design/skills/02-prepare-customer-meeting-brief.md`; §13.3 Workflow 2 (entire row table).
**Depends on:** specs 005, 006, 008, 009, 014, 020 (Skill 01 produces the sentiment_vector that Skill 02 reads as context).
**Effort:** 1.0 day. **One of the two Week-2 end-to-end skills per build-plan §4.**

## Description

Implement the meeting-brief skill per `01_design/skills/02-prepare-customer-meeting-brief.md`. Fires on `calendar.upcoming-customer-meeting` Episodes (Calendar adapter — spec 014) OR on RM-initiated queries ("prep me for my Pinnacle meeting at 2pm" via spec 039). Generates structured brief: headline, top 3 issues, at-risk talent, positive performers, talking points, recent activity. Tier-aware brief length (SMB ~400w / Mid ~700w / Enterprise ~1000w with stakeholder org-chart from Per-Profile Markdown).

## Inputs

- Calendar Episode trigger OR RM query.
- `get_customer_context(customer_id, as_of=now)`.
- Per-Profile Markdown (spec 029).
- SFDC reads: current `RM_Outreach__c`, `Account_Plan__c`, recent `Opportunity` rows (via the adapter / retrievers).
- Policy tier from `Account.Segment__c`.

## Outputs

- `03_build/pulse/skills/skill_02_prepare_customer_meeting_brief.py` exporting `async def run(ctx: SkillContext) -> list[ActionSuggested]`.
- Per-brief: an `action-suggested` event with the full Design 05 §"Output / Proposed action shape" payload.
- Prompt strings stored in `03_build/pulse/skills/prompts/skill_02_*.txt` (versioned; not inline).
- Reasoning capture per Design 04 §"Reasoning capture" with the inline-tag voice.

## Definition of Done

- [ ] Calendar-triggered path: a `calendar.upcoming-customer-meeting` Episode fires the skill within 10 seconds.
- [ ] RM-initiated path: a query containing "prep" + customer name + time fires the skill within 5 seconds.
- [ ] Tier variants produce different brief lengths (verified by golden-trace test).
- [ ] Each brief cites at least one source Episode per claim (no invented facts per guardrail).
- [ ] Modify flow: `modifiable_fields` per Design 05 §"Output" supported by spec 031 Action Queue API.
- [ ] Langfuse trace shows: retriever spans → context-bundle → reasoning span → action-compose span.

## Tests

- **Unit:** brief composition function with fixture inputs returns expected structure.
- **Integration:** real Calendar Episode + Graphiti fixture → brief emitted to Action Queue.
- **Golden-trace:** the brief's structure (sections present, citations present, length-tier-appropriate) is asserted per fixture (not exact text).

## Signal definitions involved

Per `01_design/skills/02-prepare-customer-meeting-brief.md` §"Owned signals" — Skill 02 is a consumer-only skill, reading the full signal state of the customer at brief-generation time.

## Open questions

- Q53 (RM-initiated trigger UX), Q54 (unknown attendee), Q55 (EBR detection fallback) — all dispositions in `99_open_questions.md`.

## What this is NOT

- Not Skill 03 (renewal-watcher — separate fire conditions).
- Not the briefing UI (the Action Queue card renders the brief — spec 035).
- Not the EBR-specific skill (folded into Skill 02 per Design 05).

# Design 05 — Skill Library

**Phase:** 2 (Design)
**Tier:** 2 — second-week lock
**Status:** Draft, Phase 2

---

## Purpose

The skill library is **what makes Pulse Pulse**. Skills are the codified RM playbooks the agent runs on top of the memory layer (Design 01) to produce proposed actions for the Action Queue (Design 03). Format and structure are inspired by `customer-success-skills` (`findings/customer-success-skills.md`); content is **EDGE-authored** and white-labeled.

This artifact defines: the skill spec contract (what every skill file must contain), the Phase 1 roster (10 skills), the lifecycle staging, the trigger model, and how skills compose with retrievers and the action queue.

Individual skill specs live under `01_design/skills/NN-name.md` and are listed in §B below.

---

## Inputs (skill library as a whole)

- **Triggers** — episodes ingested (Design 02), schedule (heartbeat), or RM-initiated (chat-like prompt from the dashboard, though chat is not the hero — §6 rule 17).
- **`ContextBundle`s** from the named retrievers (Design 01).
- **Per-Profile Markdown Layers** (Design 06) — read by skills that need durable narrative context.
- **Skill policy config** — which skills are enabled, per-tier auto-approve list, kill switch (Design 04 policy module).

## Outputs (skill library as a whole)

- **`action-suggested` events** to the event log (Design 04) — each containing the action card the queue renders.
- **`reasoning-completed` events** — capturing the agent's prose per skill firing (inline-tag voice per Design 04 §"Reasoning capture").
- **Skill-tuning telemetry** — which skills produce high-rejection-rate proposals; fed back into the policy module's dampening rule (Design 04 policy rule 4).

---

## Behavior

### The skill spec contract

Every skill file in `01_design/skills/` follows this exact structure:

```markdown
# Skill NN — <name>

**Lifecycle stage:** <one of: onboarding | adoption | renewal | expansion | escalation | recognition | operations>
**Phase:** 1 (Phase-2-deferred skills filed in §12 of PM_CONTEXT)
**Tier-aware:** <yes/no>; if yes, per-tier variants below

## Trigger
[When does this skill fire? — episode-driven, schedule-driven, or RM-initiated.
 Be specific: "an `Associates__c` record changes Stage to `Replaced`" not
 "when something happens with talent".]

## Inputs
- Retrievers required: [list of named retrievers from Design 01]
- External calls (READ ONLY): [Salesforce reads, etc.]
- Per-Profile Markdown read: [which profiles this skill reads]
- Policy inputs: [tier, kill switch, etc.]

## Behavior
[Plain-English description of what the skill does. Reference the
 reasoning structure from Design 04 §"Reasoning capture":
 - Signals consulted
 - Reasoning
 - Proposed action]

## Guardrails
[What the skill MUST NOT do. License-clean refusals, escalation paths,
 evidence requirements, false-positive controls.]

## Output / Proposed action shape
[The ActionPayload the skill emits. Be concrete: email draft body
 template, Salesforce Task fields, Jira ticket fields, etc.]

## Tier variants
[Per-tier behavior differences. Phase 1 default: same logic, different
 default approval mode per Design 03 §"Tier-aware behavior".]

## Outcome detection
[How does Pulse know this skill's action worked? Reference Design 03
 outcome capture table.]

## EDGE Coverage
[Which §13 rows this skill covers.]

## Open questions
[Anything that needs Phase 2/3/4 follow-up.]
```

### Trigger model

**Three trigger classes:**

1. **Episode-driven** — fires when a specific event ingests. Example: `escalation-router` fires on a new risk-tagged `Case`.
2. **Schedule-driven** (heartbeat) — fires on a cron-like schedule. Example: `renewal-watcher` runs daily at 06:00 local; `talent-care` runs hourly to find overdue check-ins.
3. **RM-initiated** — fires when an RM explicitly asks via a small Pulse query box (kept secondary per §6 rule 17). Example: an RM types "prep me for my Pinnacle meeting at 2pm" and the `prepare-customer-meeting-brief` skill fires immediately rather than waiting for the 24h-ahead calendar trigger.

The trigger is declared in each skill file; the runtime dispatches accordingly.

### Composition with retrievers

A skill **declares** which retrievers it needs. The runtime fetches the `ContextBundle`s, passes them to the skill's reasoning function, and routes the resulting proposal to the policy module. **Skills never run raw graph queries**; named retrievers are the only interface (Design 01).

Example signature (Phase 4 pseudocode):

```python
@skill(id="renewal-watcher", trigger="schedule:daily-06:00")
async def renewal_watcher_run(ctx: SkillContext) -> list[ActionSuggested]:
    suggestions = []
    for customer in ctx.scope.customers_with_renewals_within_90_days():
        bundle = await ctx.retrievers.get_customer_context(customer.id)
        if not _renewal_at_risk(bundle):
            continue
        reasoning, action = await ctx.reason_and_propose(
            template="renewal-at-risk",
            bundle=bundle,
            profile=ctx.profiles.customer(customer.id),
        )
        suggestions.append(ActionSuggested(
            skill_id="renewal-watcher",
            customer=customer.ref,
            why_oneline=reasoning.oneline,
            why_detail=reasoning.detail,
            recommended_action=action,
            urgency=_urgency_from_signals(bundle),
            source_episodes=bundle.recent_episodes[:5],
        ))
    return suggestions
```

### Skill authoring constraints

- **One file per skill.** Numbered `NN-name.md` in `01_design/skills/`.
- **EDGE-authored.** Content is EDGE's playbook. White-label discipline (§6 rule 1) — never name underlying tech.
- **Inline-tag voice** (Design 04) for `why_oneline` / `why_detail` — same tags as `rm-intelligence-agent`.
- **Guardrails are mandatory.** Every skill names what it must not do.
- **Tier variants explicit.** Even if Phase 1 has identical logic across tiers, the *approval mode* differs (Design 03).
- **No skill calls another skill directly.** If composition is needed, it goes through the action queue (one skill's approved action ingests as a signal and may trigger another skill on the next cycle).

### Lifecycle staging (per `customer-success-skills` pattern, EDGE-flavored)

| Stage | Skills | Notes |
|---|---|---|
| `onboarding` | 08-onboarding | Kickoff sequence for a new customer or new placement |
| `adoption` | (Phase 2 — `product-adoption-monitor`, deferred §12 #7) | EDGE-doc ask; not in first 10 |
| `renewal` | 03-renewal-watcher | Pipeline-watcher for renewal risk |
| `expansion` | 06-advocacy, 10-cross-account-pattern-finder | Positive-signal surfacing + cross-customer expansion patterns |
| `escalation` | 05-escalation-router, 04-talent-care, 09-coaching-signal-router | Issue routing, talent welfare, coaching handoff |
| `recognition` | 07-recognition | Low-stakes, high-volume; default auto-approve in Phase 1 |
| `operations` | 01-detect-talent-signal, 02-prepare-customer-meeting-brief | Plumbing skills the others depend on |

### The Phase 1 roster (10 skills)

| # | Skill ID | Lifecycle | Trigger class | EDGE §13 row |
|---|---|---|---|---|
| 01 | `detect-talent-signal` | operations | Episode-driven (any Chorus call or SFDC update) | §13.2 sentiment / theme tags |
| 02 | `prepare-customer-meeting-brief` | operations | Schedule (24h ahead) + RM-initiated | §13.3 Workflow 2 |
| 03 | `renewal-watcher` | renewal | Schedule (daily 06:00) | §13.5 "Manage renewals end-to-end" |
| 04 | `talent-care` | escalation | Schedule (hourly check for overdue cadence) | §13.5 "Quarterly check-ins, no slippage" |
| 05 | `escalation-router` | escalation | Episode-driven (risk-tagged Case) | §13.5 "Primary escalation point" |
| 06 | `advocacy` | expansion | Schedule (weekly Monday) | §13.5 "Recognition + advocacy programs" |
| 07 | `recognition` | recognition | Episode-driven (positive outcomes) | §13.5 "Recognition + advocacy programs" |
| 08 | `onboarding` | onboarding | Episode-driven (new Account or new Associate `Active` stage) | §13.5 "Kickoff calls with new customers" |
| 09 | `coaching-signal-router` | escalation | Episode-driven (talent feedback signals) | §13.5 "Coach Talent for long-term success" |
| 10 | `cross-account-pattern-finder` | expansion | Schedule (weekly Sunday) | §13.4 cross-account queries; §13.6 #1 |

Skill spec files: `01_design/skills/01-detect-talent-signal.md` through `01_design/skills/10-cross-account-pattern-finder.md`.

### Skills NOT in Phase 1 (filed)

- `product-adoption-monitor` — EDGE §13.5 ask, deferred to Phase 2 per §12 #7. Reason: requires product-usage telemetry that isn't yet ingested.
- `ebr-prep` as a separate skill — folded into `prepare-customer-meeting-brief` Phase 1 because the trigger pattern is identical (calendar 24h ahead + brief generation). May split out in Phase 2 if EBR-specific structure diverges.
- `briefing` as a distinct surface — same as `prepare-customer-meeting-brief`.

The PM_CONTEXT §3 Tier 2 list named "Renewal Watcher, Talent Care, EBR Prep, Escalation Router, Briefing, Advocacy, Onboarding, Coaching-Signal Router, plus signal extractors" — that's 8 explicit skills + "signal extractors" (= `detect-talent-signal`) + "Briefing" (= `prepare-customer-meeting-brief`). Phase 1 ships those 10 with `cross-account-pattern-finder` added as the differentiator skill (§13.4 cross-account queries are EDGE-doc-explicit examples).

---

## EDGE Coverage references

This artifact is the *index*; each per-skill file carries its own §13 mapping. Coverage summary:

| §13 row | Covered by |
|---|---|
| §13.2 sentiment / theme tags / 2-sentence summary | `01-detect-talent-signal` |
| §13.3 Workflow 2 (briefing) | `02-prepare-customer-meeting-brief` |
| §13.4 burnout / AI displacement / cross-account queries | `01-detect-talent-signal` (extractors) + `10-cross-account-pattern-finder` |
| §13.4 "prep me for my Pinnacle meeting" | `02-prepare-customer-meeting-brief` (RM-initiated trigger) |
| §13.4 sentiment-trajectory query | `01-detect-talent-signal` (extractors) + bi-temporal retriever |
| §13.4 advocacy query | `06-advocacy` |
| §13.5 EBRs | `02-prepare-customer-meeting-brief` |
| §13.5 renewals | `03-renewal-watcher` |
| §13.5 kickoff calls | `08-onboarding` |
| §13.5 quarterly check-ins | `04-talent-care` |
| §13.5 escalation point | `05-escalation-router` |
| §13.5 coach talent | `09-coaching-signal-router` |
| §13.5 recognition | `07-recognition` |
| §13.5 product adoption | deferred (§12 #7) |
| §13.5 trust-based stakeholder relationships | `02-prepare-customer-meeting-brief` + Per-Profile Markdown (Design 06) |

---

## Open questions

- **Q46** — Skill authoring tool. Markdown in repo for Phase 1; v1.5+ may want an admin UI for non-engineers to edit (RMs and the VP of Client Success). PM proposes: Phase 1 = git PRs from PM + Senior Dev; v1.5+ admin UI.
- **Q47** — Skill versioning. When `04-talent-care` changes its cadence threshold, do we keep the old skill version pinned for in-flight actions? PM proposes: yes; skills are versioned (`talent-care@v1`, `talent-care@v2`) and in-flight actions track which version proposed them.
- **Q48** — Skill A/B testing. v1.5+ desire — run two variants of `renewal-watcher` in parallel and compare outcome rates. Filed for v1.5+.
- **Q49** — Skill scope: account-bound vs. global. Most skills are per-customer; `10-cross-account-pattern-finder` is global. Is this categorization useful enough to formalize? PM proposes: yes, as a `scope` field on the skill spec (`per-customer` / `per-talent` / `global`).

---

## What this is NOT

- **Not an exhaustive RM playbook codex.** Phase 1 ships 10 skills. The full RM JD has more workflows; Phase 2+ adds them.
- **Not where prompts live as Python strings.** Skill files are Markdown specs, not implementation. Phase 4 implements each skill as a Python module under `03_build/skills/`, but with the spec file as the **canonical source of truth**. Prompt strings are in code; the *behavior contract* is in Markdown.
- **Not autonomous agents.** Skills propose; humans approve (§6 rule 3). The skill library is the catalog of *what kinds of proposals Pulse can make*.
- **Not a Salesforce package.** No managed-package compilation. Skills are pure Pulse code reading Salesforce as a system of record.
- **Not chained workflows.** Skills are single-pass: trigger → reason → propose. Multi-step chains go through the action queue (one approved action's outcome is a new signal that triggers a different skill).

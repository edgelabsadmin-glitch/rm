# Signal Definition Template

**Phase:** 3 (Planning) — locked as the canonical template
**Source of truth:** `02_planning/signals/*.md` — every Pulse signal has an instance of this template
**Standing rule:** §6 rule 8 — no black-box detection. Every signal Pulse surfaces has an entry here.

---

## How to use this template

1. Copy this file to `02_planning/signals/<signal_id>.md`.
2. Fill in every section. **No section may be left empty.** "N/A" is acceptable only with justification.
3. PR'd into git like any spec. Tunings post-merge happen as new commits with a version bump (e.g. `_v1` → `_v2`).
4. The template is **strict** — Phase 4 build provides a Python loader that validates each signal definition file against this template's structure. Missing required sections fail the loader and the signal is not loaded at runtime.

## Naming convention

- File name: `<signal_id>.md` (kebab-case, lowercase, ends with `_v1`, `_v2`, etc.)
- `signal_id` in front-matter matches the file basename.
- Category prefix is encouraged: `churn_signal_<name>_v1`, `expansion_signal_<name>_v1`, `talent_<name>_v1`, `escalation_signal_<name>_v1`, `recognition_signal_<name>_v1`, `<entity>_<pattern>_v1` for account-context.

---

## The template

```markdown
# <signal_id>

**Version:** v1
**Category:** churn | expansion | talent-care | escalation | recognition | account-context
**Severity model:** binary fire | tiered (low/medium/high) | scored (0-1)
**Owning skill(s):** Skill NN, Skill MM
**Status:** active | deprecated | candidate (not yet wired)

## Plain-English definition

[One paragraph in plain English. An RM should be able to read this and
understand exactly what the signal means without any technical context.
This is the section that satisfies §6 rule 8's inspectability promise —
when an RM asks "why did Pulse flag this?", the answer starts here.]

## Detection mechanism

- **Type:** rule-based | LLM-based | hybrid
- **If rule-based:** the explicit rule logic in pseudocode or plain SQL.
- **If LLM-based:** the prompt verbatim, including the JSON output schema.
- **If hybrid:** the rule layer first (cheap pre-filter), then the LLM ambiguity-resolution prompt verbatim.

## Evidence shape

What episodes / data sources are consulted to evaluate this signal.

| Source | Field(s) | Time window |
|---|---|---|
| (e.g. Chorus episode) | `content.summary`, `content.action_items` | last 90 days |
| (e.g. SFDC RM_Outreach__c) | `Customer_Health__c`, `Churn_Probability__c` | most recent |
| (e.g. Graphiti edges) | `mentions` / `raised_concern_about` | last N days |

## Triggering threshold

The exact rule that determines fire/don't-fire. **All numeric parameters named** (e.g. `silence_days=14`). If LLM-based, the threshold for "fire" within the LLM's structured output (e.g. `score >= 0.6`).

## Tier-aware variants

How the threshold changes by Account tier (per §6 rule 4):

| Account tier | Variant |
|---|---|
| SMB | (e.g. silence_days=21; auto-approve at +1h) |
| Mid-Market | (e.g. silence_days=14; human-required) |
| Enterprise | (e.g. silence_days=10; human-required + cc VP-CS) |

If tier-aware variation is not needed, state "same across tiers" explicitly.

## False-positive failure modes

Known cases where this signal over-fires. Workarounds documented if any.

- (e.g. "Customer is on PTO — silence is not a churn signal. Workaround: cross-check Account_Plan__c for stated PTO note before firing.")

## False-negative failure modes

Known cases where this signal misses. v1.5+ improvements noted if any.

- (e.g. "Customer is venting in private DMs (not on Chorus calls). Phase 1 can't see this. v1.5+ Slack adapter would catch it.")

## Adjustability

Which parameters are tunable and what changes when you tune them. Who can adjust.

| Parameter | Type | Default | Who can adjust | Effect of increasing |
|---|---|---|---|---|
| (e.g. silence_days) | int | 14 | Admin | Fewer false-positives, slower detection |
| (e.g. severity_threshold) | float | 0.6 | Admin | Tighter precision, lower recall |

## Performance metrics (populated by Layer 8 Mechanism 1)

These fields are written by the Signal Performance admin surface once production data accumulates. Initially blank.

- Fire rate (instances/day per RM): _TBD_
- Action-approval rate when this signal contributes: _TBD_
- Outcome-recorded rate among approved actions: _TBD_
- Apparent false-positive rate (rejections coded as "wrong signal"): _TBD_
- Last tuned: never

## Examples

Two or three concrete examples of signal-instances that would fire, with the evidence and the resulting action proposal.

### Example 1
- **Account:** (e.g. Acrisure)
- **Evidence:** (e.g. last RM_Outreach__c update >18 days ago; 0 Chorus calls in 21 days; renewal due in 45 days)
- **Signal fires at:** (e.g. tier="medium")
- **Action proposed:** (e.g. Skill 03 renewal-watcher drafts a check-in email)

### Example 2
- (similar shape)

## Open questions

Anything still ambiguous that needs PM / user input before Phase 4 implementation locks.
```

---

## What this template is NOT

- **Not a substitute for the skill spec.** Skills (in `01_design/skills/`) own *what to do* when a signal fires. Signal definitions own *whether to fire* and *why*. Cross-referenced bidirectionally — every skill spec has an "Owned signals" section listing the signal_ids it consumes; every signal definition has an "Owning skill(s)" header field.
- **Not a place for implementation code.** Phase 4 build implements the signal detection per the template's content; the template captures behavior, not Python.
- **Not user-facing.** Signal definitions are internal documentation. Per §6 rule 1 (white-label) they may name underlying tech and refer to internal architecture.
- **Not where rejection feedback lives.** RMs reject proposed actions through the Action Queue UI; the rejection feeds into Layer 8 Mechanism 1's metrics. The Signal Definition gets *tuned* based on that data; it is not where the data lands.
- **Not where Phase 4 stores Phase-1-versus-v1.5+ tunings.** Tunings are versioned (`_v1`, `_v2`); a signal that needs material redefinition gets a new file, and the old version is marked `status: deprecated`.

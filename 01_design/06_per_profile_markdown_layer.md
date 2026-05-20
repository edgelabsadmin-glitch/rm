# Design 06 — Per-Profile Markdown Layer

**Phase:** 2 (Design)
**Tier:** 2 — second-week lock
**Status:** Draft, Phase 2

---

## Purpose

The Per-Profile Markdown Layer is **Pulse's narrative memory complement to the temporal graph**. While the Three-Graph composition (Design 01) stores typed facts and edges, the markdown profiles store *human-readable narrative context* — the kind of color an RM accumulates over months: "Sarah Chen prefers structured agendas, cares deeply about audit accuracy, has been frustrated with onboarding speed in the past."

Pattern lifted from `b2b-sdr-agent-template-main` (`workspace/*.md` per `findings/b2b-sdr-agent-template-main.md`); confirmed by PM_CONTEXT memory `feedback_only_adopt_context_split` ("take per-profile Markdown layers, drop the rest").

This spec defines: profile types, storage, regeneration cadence, authoring tool, agent read interface, and edit semantics.

---

## Inputs

- **Episodes** (Design 02) and **graph edges** (Design 01) — the source data that summarizes into a profile.
- **RM-authored edits** — direct overrides RMs make in the UI to correct or augment the auto-generated narrative.
- **Skill outputs** — when skills like `02-prepare-customer-meeting-brief` produce stakeholder analysis, fragments may be promoted into the profile.

## Outputs

- **One Markdown profile per Customer, Talent, and RM entity** in scope.
- **Profile retrieved on-demand** by skills that declare a profile-read dependency.
- **Profile regeneration events** in the event log (Design 04) — `profile-regenerated`, `profile-edited`.

---

## Behavior

### Profile types

| Type | One per | Source SFDC entity | Size target |
|---|---|---|---|
| **Customer Profile** | Account | `Account` | 500–1500 words |
| **Associate (Talent) Profile** | Associates__c (Active or recently-Replaced) | `Associates__c` | 300–800 words |
| **RM Profile** | User (where role = RM) | `User` | 200–500 words (lighter — RM is the operator, not the subject) |

**Phase 1 does NOT include:**
- Per-Contact (customer-side individual stakeholder) profiles — Phase 2+ if needed; Phase 1 carries stakeholder context inside the Customer Profile.
- Per-Account+Talent-pair profiles — too granular; the relationship is captured by graph edges.

### Storage

**Postgres table `profiles`** (single-table, schema below):

```sql
-- Phase 4 schema sketch
CREATE TABLE profiles (
    profile_id      UUID PRIMARY KEY,
    profile_type    TEXT NOT NULL,            -- 'customer' | 'talent' | 'rm'
    entity_id       TEXT NOT NULL UNIQUE,     -- SFDC Id (Account / Associates__c / User)

    content_md      TEXT NOT NULL,            -- the Markdown profile
    content_hash    TEXT NOT NULL,            -- SHA256 of content_md (regeneration tracking)

    last_regenerated_at TIMESTAMPTZ NOT NULL,
    last_edited_at      TIMESTAMPTZ,
    last_edited_by      TEXT,                 -- User.Id if RM-edited; NULL if auto-generated

    -- Override layer: when an RM edits, the edited content_md is preserved
    -- across regenerations until the regenerator detects substantively new
    -- information. See §"Edit semantics" below.
    override_active     BOOLEAN NOT NULL DEFAULT FALSE,
    override_source_md  TEXT,                 -- the auto-gen output at the time the RM started editing

    INDEX (entity_id),
    INDEX (profile_type, last_regenerated_at)
);
```

**Why Postgres (not the file system, not the graph):**
- Profiles need durable cross-machine access (Phase 1 is single VPS; Phase 2 AWS is multi-instance).
- Edit history needs ACID semantics (the override layer below).
- Backup/restore parity with the event log (Design 04) — both live in the same Postgres instance.

### Profile shape — the Markdown structure

Each profile follows a **consistent section ordering** so skills can locate specific information by header. Schemas:

#### Customer Profile schema

```markdown
# <Customer Name>

**Industry:** <Insurance | Medical | Dental>  ·  **Tier:** <SMB | Mid | Enterprise>  ·  **RM Owner:** <RM Name>
**Pulse profile last updated:** <ISO date>

## Relationship origin
[One paragraph: when EDGE started working with this customer, how the relationship began,
 originating placement(s) or the originating sales motion. Maps to the monica.md
 "how we met" pattern.]

## Current shape
[2-3 paragraphs: current state of the relationship. Active placements summary,
 customer-side dynamics, recent trajectory.]

## Stakeholders
[Bullet list: known champions, decision-makers, detractors, with one-line context
 per person. Pulled from Chorus participant records + RM_Outreach references +
 Contact records. Editable by RM.]

## Strategic context
[The customer's broader business situation: industry pressures, recent leadership
 changes, mergers, vendor relationships. Sourced from external news (where available)
 + Account_Plan__c + RM-supplied context.]

## Communication preferences
[Anything the RM has learned about how this customer prefers to communicate.
 Channel, cadence, tone, what's worked and what hasn't.]

## History
[Chronologically ordered notable moments: significant escalations resolved,
 successful placements, EBR themes, churn scares and how they were resolved.
 The "institutional memory" layer.]

## Open threads
[Currently-unfinished business: outstanding asks, pending decisions, in-flight
 expansion conversations, ambient concerns not yet resolved.]
```

#### Associate Profile schema

```markdown
# <Talent Name> · <Role> @ <Customer>

**Stage:** <Active | Replaced | Terminated>  ·  **Started:** <date>  ·  **RM Manager:** <name>  ·  **Associate Manager:** <name>
**Pulse profile last updated:** <ISO date>

## Background
[Talent's professional background: prior roles, areas of expertise, tenure at EDGE,
 how they were sourced. Sourced from `Candidate__c` link, prior `Associates__c`
 records, and RM-supplied notes.]

## Placement context
[Why this talent at this customer. The role expectations, the customer-side
 stakeholders they report to, the success criteria set at kickoff.]

## Trajectory
[Performance evolution since placement: audit results, customer feedback,
 self-feedback from check-ins. Risk events (replacement, performance issues)
 if any, with how they were resolved.]

## Care notes
[Anything that should inform the next talent-care check-in: known stressors,
 career aspirations, pay/role asks, learning interests.]

## Recognition history
[Positive moments: customer praise, successful escalation handling,
 milestones reached. Sourced from Skill 07 episodes + RM_Outreach.]
```

#### RM Profile schema

```markdown
# <RM Name> · RM at EDGE

**Tier focus:** <SMB | Mid | Enterprise | Mixed>  ·  **Book size:** <customer count>  ·  **Talent under management:** <talent count>
**Pulse profile last updated:** <ISO date>

## Working style
[How this RM works: tools they prefer, cadence they keep, communication style.
 Less formal than Customer/Talent profiles.]

## Strengths & focus areas
[Drawn from approval / rejection / outcome patterns over time. e.g., "high
 outcome rate on advocacy actions; sometimes defers escalation actions."
 The Skills Layer of Pulse can use this for personalization.]

## Notes from VP of Client Success
[VP-supplied direct notes; intended as coaching context for the RM
 and routing input for the agent.]
```

### Regeneration cadence

Profiles auto-regenerate when **substantive new information** has accumulated. Phase 1 trigger rules:

| Profile type | Auto-regenerate trigger |
|---|---|
| Customer | (a) ≥5 new episodes since last regen, OR (b) any episode with `urgency >= high` since last regen, OR (c) weekly fallback if neither (a) nor (b) fired |
| Associate | (a) Stage transition, OR (b) any risk-tagged Case opened/closed, OR (c) ≥3 new episodes referencing this talent since last regen, OR (d) monthly fallback |
| RM | (a) Weekly throughput summary, OR (b) VP-of-CS edit |

Regeneration is async: the regenerator runs as a background job triggered by event-log fan-out (Design 04). The agent uses the **most recent profile available** when reasoning; profiles never block skill execution.

### Authoring tool — Phase 1 minimum

Phase 1 ships:
- **Auto-generation** is the default. The regenerator reads the relevant `ContextBundle` + recent episodes + SFDC data, and produces the Markdown profile via an LLM call. Per Decision 13, Claude is used.
- **Inline edit in the Pulse UI** — every profile has an "edit" button. Edits save as an override (see §"Edit semantics"). Phase 1 surface: simple Markdown editor in the profile's side-panel view (accessed from the Action Queue card or from a directory listing).
- **No standalone CMS.** Profiles live in Postgres; the editor is a Pulse-internal surface.
- **No version history UI** in Phase 1 (the event log records every regeneration and edit; admins can query). v1.5+ may add a UI.

### Edit semantics — the override layer

The hard case: an RM hand-edits a profile, and later the auto-regenerator runs. What happens?

**Phase 1 rule (preserve human edits with explicit re-merge):**

```
when regenerator runs on a profile with override_active = true:
  generate the fresh auto-gen content
  if hash(fresh_auto) == hash(override_source_md):
    # No substantive new info accumulated since the RM edited.
    # Keep the RM's edit. No-op.
  else:
    # New info has accumulated. The RM's edit might be stale.
    # Surface a "profile re-merge needed" Action Queue card.
    # Card shows side-by-side diff: RM edit vs. fresh auto-gen.
    # RM can:
    #   - Accept the new auto-gen (override cleared)
    #   - Re-apply their edit on top of the new auto-gen (override updated)
    #   - Keep their current edit (override_source_md updated to new auto-gen)
```

**Why surface this rather than merge automatically:** LLM merges of human-edited prose introduce subtle hallucinations. The RM is the authoritative voice when they've edited; we ask before we override.

### Agent read interface

```python
# Pseudocode — Phase 4
@dataclass
class ProfileRef:
    profile_type: str
    entity_id: str
    content_md: str
    last_regenerated_at: datetime
    last_edited_at: datetime | None

# Skills request profiles via the SkillContext:
ctx.profiles.customer(account_id) -> ProfileRef
ctx.profiles.talent(associates_id) -> ProfileRef
ctx.profiles.rm(user_id) -> ProfileRef
```

**The agent never edits profiles directly.** Edits are RM-initiated through the UI. The regenerator is a separate background process. This separation prevents the agent from "rewriting history" within its own reasoning loop.

---

## EDGE Coverage references

- **§13.5 row "Trust-based stakeholder relationships"** — Customer Profile's Stakeholders section is the core data.
- **§13.5 row "Document customer workflows, Talent feedback, success plans"** — direct mapping; this is the documentation surface.
- **§13.5 row "Cohesive customer + Talent experience"** — the parallel Customer + Associate profile structure encodes both sides.
- **§13.6 #2** "Three-graph architecture replaces EDGE's persistent-Claude-conversation-per-customer misconception" — the Per-Profile Markdown Layer is the *narrative* half of that replacement; the graph is the *structured* half.

---

## Open questions

- **Q80** — Profile content authority on conflict. Phase 1 = RM edits are authoritative until they choose to re-merge. v1.5+ may want a finer-grained "this section is RM-owned, this section auto-regens" model. Filed.
- **Q81** — Cross-profile coherence. Two profiles may reference the same fact (Customer mentions a stakeholder, Stakeholder appears in another Customer's profile). Phase 1 makes no cross-profile consistency guarantee. v1.5+ may.
- **Q82** — Profile export. Can an RM export a profile as a PDF before a sensitive meeting? PM proposes: yes, simple Phase 1 capability (Markdown → PDF), with explicit audit-log event when exported.
- **Q83** — Profile content sensitivity. Some content (pay concerns, performance issues) is sensitive. Is the profile readable by all RMs, or owner-scoped? PM proposes: scoped per Design 09 role model — Manager sees their reports' profiles; RM sees their own book's profiles; Admin sees all.
- **Q84** — Profile staleness signal. Should the UI show a "this profile is N days old" badge? PM proposes: yes, with subtle styling once a profile is >14 days unmodified.

---

## What this is NOT

- **Not a CMS for the customer or talent themselves.** RMs read and edit. Customers and talent never see profiles.
- **Not a free-form chat with the agent about the entity.** That's the (deliberately secondary) Pulse query box. Profiles are durable narrative; chat is ephemeral.
- **Not where graph edges live.** Structured facts go in Kuzu (Design 01). Profiles are narrative summaries of what the graph already knows, plus RM color.
- **Not an LLM-rewritable surface during agent reasoning.** Reasoning reads profiles; the regenerator is a separate process.
- **Not versioned in Git.** Edits are in Postgres with event-log history. v1.5+ may add export-to-Git capability for admin-readable diffs.
- **Not Slack-delivered.** Per `feedback_dont_flood_slack`. Profiles surface in the Pulse UI.

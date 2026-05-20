# Design 03 — Action Queue

**Phase:** 2 (Design); refreshed Phase 2.5 against Tier-0
**Tier:** 1 — first-week lock
**Status:** Locked on substance Phase 2; **visual references refreshed Phase 2.5** against `00_design_language.md`

---

## Purpose

The Action Queue is Pulse's **hero UI surface** (§6 design rule 17 — "the hero is the action queue + the situational hero card"; two-hero design accepted Session 8). It is where every proposed agent action surfaces for an RM (or Manager, or Admin) to approve, modify, or reject. It is the embodied form of "human-in-the-loop is the product, not the fallback" (§6 rule 3). When the CEO sees Pulse, they see this. When the VP of Client Success measures Pulse's value, they measure throughput here.

This spec defines: the queue's information architecture, ranking logic, item shape, approval flow, tier-aware behavior, **design-language application (all references resolve through Tier-0: `01_design/00_design_language.md`)**, the agent-presence integration (**Pulse Bar (Breathing)** — locked Session 10, Tier-0 §8.14), and the after-action outcome capture loop.

**Visual register reference:** `01_design/00_design_language_preview.tsx` — the React preview the user provided Session 8. The Action Queue is the right-rail column in that preview (`<aside class="ps-rail ps-rail-right">`).

---

## Inputs

- **Proposed actions** emitted by the agent layer (Design 05 skills). Each proposed action is an `action-suggested` event (Design 04 schema).
- **Approval policy** from the governance module (Design 04 + 09): tier-aware thresholds (SMB auto-approve some categories; Enterprise human-approval-only).
- **Per-user RBAC** from the role model (Design 09): Admin sees all queues; Manager sees their direct reports' queues; RM sees their own + the Overall view.

## Outputs

- **Approval decisions:** `action-approved` / `action-rejected` / `action-modified-and-approved` events (Design 04).
- **Dispatched actions:** Email draft sent to Gmail/Outlook drafts; Salesforce Task created; Jira ticket filed; Calendar hold placed; recognition note saved. Each dispatch emits an `action-executed` event.
- **Outcome captures:** Post-action, a follow-up `outcome-recorded` event when the action's effect is observable (e.g., the email got a reply; the customer agreed to the proposed EBR date).

---

## Behavior

### Information architecture — three-column shell + opt-in depth

Pulse uses the **three-column layout** from the React preview (Tier-0 §9). The Action Queue is the right rail; the situational hero card lives in the middle column; the account list lives in the left rail. **The Action Queue and the situational hero card together form the two-hero surface** (§6 design rule 21).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [⚡] Pulse · Relationship intelligence    [search ····]   [🔔 Queue]  [DZ]   │
├──────────────────┬─────────────────────────────────┬────────────────────────┤
│ ACCOUNTS · Today │                                 │ ACTION QUEUE · 3       │
│                  │  ✦ AI briefing · grounded in    │                        │
│ ▣ Helix Labs     │     account memory              │ ┌──────────────────┐   │
│   Renewal · 3d   │  ┌───────────────────────────┐  │ │ ⌚ Renewal note    │   │
│   ━━━━━━━━━╴ 64% │  │   HELIX LABS              │  │ │ Helix sponsor →    │   │
│                  │  │   Composite 6.4/10  ⊙     │  │ │ 3 verified signals │   │
│ ◇ Mendota Health │  │   Pulse is prioritizing…  │  │ │ [RM approval] >    │   │
│   EBR tomorrow   │  │                           │  │ └──────────────────┘   │
│                  │  │   [temporal] [evidence]   │  │ ┌──────────────────┐   │
│ ◇ Vertex Group   │  │   [RM approval] [health]  │  │ │ ✿ EBR brief        │   │
│                  │  └───────────────────────────┘  │ │ Mendota Thursday   │   │
│                  │                                 │ │ [Prepared] >       │   │
│                  │  Signal vector | Verified themes│ └──────────────────┘   │
│                  │  (opt-in depth: click to expand)│ ┌──────────────────┐   │
│                  │                                 │ │ 👤 Coaching route  │   │
│                  │  Meeting brief                  │ │ Talent → Talent Dev│   │
│                  │  [Generate brief]               │ │ [Care action] >    │   │
│                  │                                 │ └──────────────────┘   │
│                  │                                 │                        │
│                  │                                 │ ┌──────────────────┐   │
│                  │                                 │ │ 🛡 Trust layer     │   │
│                  │                                 │ │ Source · date ·    │   │
│                  │                                 │ │ confidence · owner │   │
│                  │                                 │ └──────────────────┘   │
└──────────────────┴─────────────────────────────────┴────────────────────────┘
```

(See the React preview for the rendered version. The ASCII wireframe above is reference; the implementation matches the preview's geometry exactly.)

### Opt-in depth — what the queue shows by default vs. on click

**Hero + Action Queue are the *default* surface.** The deeper context — the situational hero card's signal vector, verified themes, meeting brief — reveals on click (§6 design rule 18, Session 8 lock).

Each queue card by default shows: a small purple-tinted icon container (`--color-brand-primary-muted` per Tier-0 §8.4), a chevron-right affordance, a 1-line action title (text-sm font-semibold), a 1-line detail (text-xs slate-500), and a foot row with a neutral Pill (the owner state, e.g. "RM approval") + a ghost-button "Review" link (purple text on hover purple/7).

**On click of "Review"**, the card expands inline to reveal:
- The full reasoning prose (inline-tag voice from Tier-0 §10 — `<num>`, `<bad>`, `<good>`, `<quote>`, `<em>`)
- The provenance episodes (Chorus link, SFDC link, calendar event link — each clickable)
- The skill that fired (admin-only)
- Approve / Modify / Reject controls

**No top-nav tabs. No dashboard. No chat box.** The hero stays singular (two surfaces, one register).

### Left-rail navigation — accounts list as queue scope

The left rail in the Tier-0 layout is the **account list** (per the React preview), not the queue navigation. Queue filtering happens via the right-rail header's "3 pending" Pill (clickable → filter modal) and a secondary scope chip row above the cards:

- **My Queue** (default) — actions for the logged-in user's book
- **Overall** — cross-RM view (shared per §13.6 and `project_role_model`)
- **Approved** — recently approved items (audit trail; click into each)
- **Dispatched** — actions already sent/created

Filter chips (tier / customer / skill / owner) live in the same row, collapsible. Persistence per Q36 — browser localStorage in Phase 1.

### Item shape — what each action card carries

```
ActionCard = {
  action_id: UUID,
  proposed_at: datetime,
  source_skill: str,                # "renewal-watcher" | "ebr-prep" | ...
  source_episodes: list[EpisodeRef],# provenance to specific signals
  customer: CustomerRef,
  talent: TalentRef | None,         # if talent-side action
  rm: RMRef,                        # the action's owning RM
  tier_class: "SMB" | "Mid" | "Enterprise",

  headline: str,                    # one-line action ("Draft EBR prep brief for Sarah Chen")
  why_oneline: str,                 # one-sentence rationale shown in card
  why_detail: dict,                 # expandable: the inline-tag-rendered reasoning
                                    # (lifted from rm-intelligence-agent's <num>/<bad>/<good>/<quote>/<em>)
  recommended_action: ActionPayload,# the concrete artifact (email draft, task body, etc.)
  modifiable_fields: list[str],     # which fields of the payload the user can edit before approval

  urgency: "low" | "medium-low" | "medium" | "medium-high" | "high",
  auto_approve_at: datetime | None, # tier-aware: only populated when policy says auto-approve
  expires_at: datetime | None,      # actions go stale (e.g., a brief for a meeting that already passed)

  approval_state: "pending" | "approved" | "modified-approved" | "rejected" | "expired" | "dispatched",
  decided_by: UserRef | None,
  decided_at: datetime | None,
  outcome_captured_at: datetime | None,
  outcome: OutcomePayload | None,
}
```

### Ranking logic

Cards are ordered by a **composite score** computed at retrieval time. Phase 1 formula (kept simple and tunable):

```
score = (urgency_weight)
      + (proximity_to_deadline_bonus)      # exponential ramp when expires_at approaches
      + (tier_signal_bonus)                # Enterprise > Mid > SMB
      + (recency_bonus)                    # newer surfaces above older, ceteris paribus
      - (already_acknowledged_penalty)     # cards the user has clicked but not decided
```

**Urgency weights (Phase 1 defaults; tunable in Design 04 policy module):**
- `high`: 100 — actions tied to imminent churn signals or expansion windows closing
- `medium-high`: 60 — risk-tagged Cases recently opened; EBR within 24h
- `medium`: 30 — talent-care cadence overdue, advocacy opportunity surfaced
- `medium-low`: 10 — recognition notes, low-stakes follow-ups
- `low`: 1 — informational nudges

**Tie-breaker:** proposed_at DESC.

**Manual reordering not allowed in Phase 1.** Filtering yes; reordering no. The agent's ranking is the canonical answer; if it's wrong, the right fix is to tune the policy, not to drag cards around. Reconsider in v1.5 if RMs ask repeatedly.

### Per-item explainability — the "why"

Two layers:

1. **`why_oneline`** in the card itself. One sentence. Examples:
   - *"2 risk-tagged Cases open + vendor-consolidation mentioned in 2 recent calls. EBR booked Thursday."*
   - *"CEO Maria Lopez asked verbatim 2026-05-08; no follow-up yet."*
2. **`why_detail`** revealed by clicking *Review* on the card. The card expands inline (no modal) to reveal:
   - The agent's full reasoning prose, rendered with inline-tag voice per Tier-0 §10 ("Inline-tag voice"):
     - `<num>2 risk-tagged Cases</num>` → JetBrains Mono, slate-900 (Tier-0 token `--font-mono`)
     - `<bad>Acrisure CFO mandate to cut vendor count by 20%</bad>` → `--color-risk-high-fg` (Tier-0 token)
     - `<good>Marcus Wells replacement plan delivered on time</good>` → `--color-risk-low-fg`
     - `<quote>"Our CFO is asking us to cut vendor count by 20% this fiscal year."</quote>` → Inter italic, slate-700
     - `<em>EBR is Thursday</em>` → Inter italic, slate-900
   - The list of provenance episodes (Chorus call links, SFDC record links, calendar event links) — each clickable
   - The skill that fired (e.g., "renewal-watcher" — visible to admins for tuning, hidden from non-admins per white-label internal/external distinction)
   - The `ContextBundle` summary that fed the reasoning (admin-only)

**Design-language application — all references resolve through Tier-0:**
- Cards use `--color-surface-card` (white) with `rounded-3xl` (24px) + `--color-border-subtle` border + `shadow-sm` per Tier-0 §8.3. Padding `p-4` for queue cards (denser than `p-5` standard — right-rail density is higher).
- Hero card uses `--color-brand-primary` + `--color-text-on-brand` + `rounded-[2rem]` + `shadow-xl shadow-[--color-brand-primary-glow]` — the tinted-shadow signature (Tier-0 §6).
- Primary CTA buttons (Approve, Generate brief): `--color-brand-primary` background, hover `--color-brand-primary-hover`, `rounded-full`, white text (Tier-0 §8.4).
- Ghost CTAs ("Review", "Reject"): purple text on transparent, hover `--color-brand-primary-ghost` (Tier-0 §8.6).
- Pills (status chips, "RM approval"): per Tier-0 §8.1 — neutral variant for queue cards.
- Inline-tag rendering uses the Tier-0 §10 whitelist exactly. No raw HTML.
- Motion: card fade-and-lift on new action per Tier-0 §7 (250ms ease-out). No spinners. No "thinking…" dots.
- Per §6 design rule 20 ("Outcome-led, not workflow-led"): no agent-thinking dashboards visible by default. The reasoning expands on demand.
- **No dark mode default.** Phase 1 ships `--color-surface-page` / `--color-surface-chrome` / white cards (Session 6 reversal). Dark variant is v1.5+.

### Agent-presence indicator — Pulse Bar (Breathing) integration

**Locked Session 10.** The indicator is the **Pulse Bar (Breathing)** — Tier-0 §8.14 + §6 design rule 22. Canonical render: `01_design/agent_presence_variants/04_pulse_bar_breathing.html`.

The Action Queue receives the indicator's action-ready state directly: when a new `action-suggested` event lands and surfaces as a queue item, the Pulse Bar performs its 600ms heartbeat (peak 80% opacity / 2px height, then return to idle) and the numbered badge on the Action Queue header button increments. The badge persists until the RM handles the items (approve / modify-and-approve / reject / expire); the badge count is live and decrements as items leave the queue. See Tier-0 §8.14 for the motion specs, throttling rules, and anti-patterns.

The queue card itself receives a fade-and-lift entrance animation per Tier-0 §7 (250ms ease-out) — never a slide-in-from-the-side or a flash. New cards land at the top of the list, in their ranking position. The bar's heartbeat and the card's entrance animation fire on the same `action-suggested` event but are visually independent — the bar is in the chrome, the card is in the content.

The Action Queue does *not* own the indicator design — Tier-0 §8.14 owns it. This spec only constrains the queue's response when the indicator fires.

### Approval flow

Three primary actions per card:

1. **Approve** — dispatches the proposed action immediately.
2. **Modify** — opens an inline editor for `modifiable_fields` (the email body, the calendar date, the recipient list, etc.). Save → `action-modified-and-approved` event → dispatch.
3. **Reject** — opens a small "why" picker (4 reasons + free text) to feed back into skill tuning. Phase 1 reasons:
   - *Wrong customer / context*
   - *Wrong action type / tone*
   - *Already done elsewhere*
   - *Not now* (with optional snooze duration)

**One-tap dispatch:** Approve = single click. No confirmation dialog for the common case. Confirmation only for **destructive or high-blast-radius** actions (e.g., "Send mass email to 12 contacts") — and even then, the confirmation is a 3-second auto-confirming countdown, not a modal.

**Modal-by-default is wrong** for this surface. The whole point is *fast approval*.

### Tier-aware behavior (§6 rule 4)

The approval policy module (Design 04) decides per (skill × customer-tier × action-category):

| Customer tier | Default approval mode | Notes |
|---|---|---|
| **SMB** | Auto-approve at +1h delay (visible countdown on the card) | RM can cancel during the window |
| **Mid-Market** | Human approval required for most categories; auto-approve for low-stakes recognition notes only | |
| **Enterprise** | Human approval required for all categories | No auto-approval, full stop |

**Auto-approval has a kill switch.** The policy module (Design 04) is the source of truth; turning off all auto-approvals globally is a single toggle that admins can flip. Required by §6 rule 12 ("no silent failure" — applied here as "the human can always interrupt").

**Tier classification source:** read from `Account.{Tier__c or Segment__c}` (TBD per Spike 1 / Q22). If absent, default to Mid-Market (the safe middle).

### After-action outcome capture

The Action Queue is not done when the action dispatches. It's done when we know whether the action worked.

**Outcome capture loop:**

```
Action dispatched → wait for signal → outcome event emitted → card moves to "Approved → Outcome captured"
```

Outcome detection is **passive** — Pulse watches the same signal sources for evidence that the action worked:

| Action type | Outcome signal | How detected |
|---|---|---|
| Email draft → sent | Reply received | Calendar adapter / email IMAP scan |
| Salesforce Task created | Task marked done | Salesforce CDC / poll |
| EBR brief delivered | EBR happened on Chorus | Chorus engagement matching attendee + customer |
| Jira ticket filed | Ticket transitions to "in progress" | Jira webhook (v1.5+ adapter) — Phase 1 manual |
| Recognition note sent | Acknowledgement reply | Email IMAP scan |

In Phase 1, **only the first three outcome types are wired** (email reply, SFDC task done, Chorus EBR detection). The rest emit a manual "did this work?" follow-up card a week after dispatch.

Outcome data feeds back into ranking (`recency_bonus` for skills with high outcome rates; `negative_bonus` for skills with low outcome rates — per memory pattern `audit_before_building_surfaces_imagined_questions_not_real_ones`, keep this simple and tunable).

### CEO view of the queue

The CEO does not approve actions. The CEO View (Design 08) shows **aggregated approved+dispatched+outcome-captured throughput**, with the AI-RM narrative voice describing what's happening across the book. The Action Queue is the operator surface; the CEO View is the narrative sibling surface.

---

## EDGE Coverage references

- **§13.2 Workflow 1** rows "Push structured data to Salesforce via API" — implemented as an *Action* on the queue requiring explicit approval (§6 rule 6 compliance).
- **§13.3 Workflow 2** row "Delivered to Slack or email" — Action Queue is the delivery surface; Slack/email are downstream dispatch targets.
- **§13.4 Customer Intelligence Hub** — the query examples are not strictly Action Queue items, but a query that surfaces actionable findings (e.g., "Which talent across ALL accounts have raised pay concerns?") naturally generates Action Queue items via the cross-account-pattern-finder skill (Design 05).
- **§13.5 JD area "Customer Success & Relationship Management"** rows "Proactive feedback gathering" and "Trust-based stakeholder relationships" — Action Queue is where this manifests.
- **§13.5 JD area "Issue Resolution & Escalation Management"** rows "Primary escalation point" / "Proactive risk monitoring" — risk-tagged signals surface as Action Queue items.
- **§13.5 JD area "Communication & Stakeholder Engagement"** — Action Queue is the bridge between customers/talent/internal teams (the Escalation Router skill routes to the right internal team via Jira-or-equivalent).
- **§13.6 #1** "Action Queue + agentic action proposals" — this artifact *is* the receipt for that claim.
- **§6 rule 3** "Human-in-the-loop is the product, not the fallback" — Action Queue is the embodiment.
- **§6 rule 6** "Salesforce write-back only through Action Queue with explicit approval" — Action Queue is the only path; ingestion is read-only (Design 02).

---

## Open questions

- **Q36** — Filter persistence across sessions. Should filter selections be remembered per-user? PM proposes: yes, in browser localStorage.
- **Q37** — Bulk approve. Some skills (recognition notes, low-stakes nudges) generate volume. Should the queue support multi-select + bulk approve? PM proposes: not in Phase 1; if RMs complain, add in v1.5.
- **Q38** — Notification escalation. If a high-urgency item sits >1h without a decision, does Pulse ping the RM via email/Slack? PM proposes: yes for `high` urgency; otherwise the queue is the canonical notification surface.
- **Q39** — Action history limits. How far back does "Approved" / "Dispatched" history go in the UI? PM proposes: 90 days in-UI, full audit log in event log (Design 04) for longer-tail queries.
- **Q40** — Mobile / responsive scope. RMs may want to approve from a phone. PM proposes: out of Phase 1; responsive layout is a v1.5+ candidate.

---

## What this is NOT

- **Not a dashboard.** No charts on the hero. No KPIs. Outcomes live in the CEO View (Design 08); operator surface is action-by-action.
- **Not a chat box.** The agent does not converse with the RM here. Proposals are presented; modifications are inline edits, not dialogue.
- **Not a generic workflow tool.** Not Linear, not Asana, not Trello. The queue is *only* for agent-proposed actions; manual RM task lists live in Salesforce.
- **Not an admin console.** Admin / Manager / RM views are different *scopes* of the same queue (Design 09); the queue itself is operator-singular.
- **Not where outcome analysis lives.** Outcome capture flows back to the event log (Design 04) and feeds the CEO View (Design 08). The queue card shows a small "outcome captured ✓" indicator; deep analysis is elsewhere.
- **Not Slack.** Per `feedback_dont_flood_slack`, Slack is not a Pulse output surface for v1. Notifications about queue items use email; the queue itself is in-app.

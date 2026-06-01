/*
 * SPEC-035 — Phase-1 demo Action Queue fixture (live wiring is the Week-4 pulse-api
 * cutover, same convention as hero/fixtures.ts + demo_characters.ts). The real
 * GET /api/actions is authoritative; this fixture is only served as a DEV fallback
 * when the backend is absent (see api.ts listActions), so the demo + preview render
 * ranked cards without a running FastAPI.
 *
 * The three cards mirror the Executive View "What I'd ask of you" asks (DHR escalate /
 * Bayhealth expand / NAVADERM reference). Dollar exposure is derived from the revenue
 * heuristic ($10K/seat) via accountARR/formatARR — single source of truth — and carried
 * in why_detail as <num> inline tags (Tier-0 §10), rendered by the spec-035 renderer.
 */
import { accountARR, DEMO_RMS, formatARR, REVENUE_PER_SEAT_USD } from "@/fixtures/demo_characters";
import { STUB_SESSION } from "@/session/useSession";
import type { ActionDTO, ActionsResponse, QueueFilters } from "./types";

const rmName = (id: string) => DEMO_RMS.find((r) => r.id === id)?.name ?? id;
const seats = (id: string) => accountARR(id) / REVENUE_PER_SEAT_USD; // verifiable active placements

const DHR_ARR = formatARR(accountARR("dhr-health-clinics")); // $760K

// Real-data integrity (Session 19 operator review): narrative content carries ONLY
// figures verifiable against the rm-intelligence-agent data (active-placement counts +
// the $10K/seat ARR heuristic). Qualitative signals that need live Chorus extraction
// (e.g. "vendor-consolidation talk") are NOT asserted until the Week-4 pulse-api cutover.
export const DEMO_ACTIONS: ActionDTO[] = [
  {
    action_id: "demo-dhr-churn",
    customer_id: "dhr-health-clinics",
    talent_id: null,
    rm_id: "sidra-zia",
    tier_class: "Enterprise",
    urgency: "high",
    action_card: { headline: "Churn signal flagged for DHR Health Clinics", action_type: "escalation" },
    why_oneline: `Composite churn risk crossed 50% — ${seats("dhr-health-clinics")} active placements, ${DHR_ARR} book.`,
    why_detail:
      `<bad>50% churn risk</bad> detected across <num>${seats("dhr-health-clinics")} active placements</num>. ` +
      `Composite signal escalation in progress. Owning RM: ${rmName("sidra-zia")}.`,
    modifiable_fields: ["headline", "summary"],
    source_episodes: ["sfdc:dhr-placements", "sfdc:case-dhr-escalation"],
    proposed_at: "2026-05-20T15:10:00Z",
    status: "pending",
    rank_score: 0.97,
    skill_id: "skill-03-renewal-watcher",
  },
  {
    action_id: "demo-bayhealth-expansion",
    customer_id: "bayhealth",
    talent_id: null,
    rm_id: "ameer-ali",
    tier_class: "Mid-Market",
    urgency: "medium",
    action_card: { headline: "Expansion signal at Bayhealth", action_type: "expansion" },
    why_oneline: `Current book at ${seats("bayhealth")} active placements — expansion opportunity identified.`,
    why_detail:
      `Bayhealth currently at <num>${seats("bayhealth")} active placements</num> with healthy engagement ` +
      `signal. Expansion opportunity surfaced through opp-tracker. Owning RM: ${rmName("ameer-ali")}.`,
    modifiable_fields: ["headline", "summary"],
    source_episodes: ["opp-tracker:bayhealth-postings", "sfdc:bayhealth-placements"],
    proposed_at: "2026-05-20T16:02:00Z",
    status: "pending",
    rank_score: 0.81,
    skill_id: "skill-07-expansion-spotter",
  },
  {
    action_id: "demo-navaderm-reference",
    customer_id: "navaderm",
    talent_id: null,
    rm_id: "mubeen-sohail",
    tier_class: "SMB",
    urgency: "medium-low",
    action_card: { headline: "Reference candidate: NAVADERM", action_type: "reference" },
    why_oneline: `${seats("navaderm")} healthy placements, no escalations — strong reference profile.`,
    why_detail:
      `NAVADERM at <good>${seats("navaderm")} active placements</good> with no escalations or churn signals. ` +
      `<good>Healthy engagement pattern.</good> Owning RM: ${rmName("mubeen-sohail")}.`,
    modifiable_fields: ["headline", "summary"],
    source_episodes: ["sfdc:navaderm-placements", "sfdc:navaderm-csat"],
    proposed_at: "2026-05-20T16:40:00Z",
    status: "pending",
    rank_score: 0.64,
    skill_id: "skill-09-reference-builder",
  },
];

/**
 * Filter the demo cards the way GET /api/actions would. Honors a real rm_id deep-link
 * (Constellation ?rm=) and the tier chip; the demo session stub (rm-demo) is treated as
 * book-wide so My Queue isn't empty in the demo (real scoping is server-side, spec 042).
 */
export function filterDemoActions(filters: QueueFilters = {}): ActionsResponse {
  let actions = DEMO_ACTIONS;
  if (filters.rm_id && filters.rm_id !== STUB_SESSION.id) {
    actions = actions.filter((a) => a.rm_id === filters.rm_id);
  }
  if (filters.tier) {
    actions = actions.filter((a) => a.tier_class === filters.tier);
  }
  if (filters.customer_id) {
    actions = actions.filter((a) => a.customer_id === filters.customer_id);
  }
  return { actions, count: actions.length, limit: 200, offset: 0 };
}

// Three action templates — cycled per-account so each account shows varied cards.
const _TEMPLATES = [
  {
    suffix: "renewal",
    urgency: "high" as const,
    tier_class: "Enterprise",
    action_type: "renewal",
    headline: "Schedule renewal review",
    why_oneline: "Contract renewal window opening in 30 days — initiate RM outreach now.",
    why_detail:
      "<bad>Renewal in 30 days</bad> with no outreach logged yet. " +
      "Book this week to avoid last-minute pressure on terms.",
  },
  {
    suffix: "checkin",
    urgency: "medium" as const,
    tier_class: "Mid-Market",
    action_type: "check-in",
    headline: "Proactive health check-in",
    why_oneline: "Engagement cadence lapsed — schedule a touchpoint this week.",
    why_detail:
      "Activity has been quieter than the account's baseline. " +
      "A <em>proactive check-in</em> now is lower-cost than a reactive recovery later.",
  },
  {
    suffix: "talent",
    urgency: "medium-low" as const,
    tier_class: "SMB",
    action_type: "talent-care",
    headline: "Review active talent satisfaction",
    why_oneline: "Talent feedback cycle due — verify satisfaction before next renewal.",
    why_detail:
      "Active placements are due for a satisfaction pulse. " +
      "<good>Positive scores strengthen the renewal position</good> and surface early risk.",
  },
] as const;

/**
 * Generate 2 deterministic test actions for any account that has no real demo data.
 * Used as the DEV fallback when a real SF account ID is passed as customer_id.
 */
export function generateAccountActions(customerId: string): ActionDTO[] {
  const idx = customerId.charCodeAt(customerId.length - 1) % _TEMPLATES.length;
  return [_TEMPLATES[idx], _TEMPLATES[(idx + 1) % _TEMPLATES.length]].map((t, i) => ({
    action_id: `demo-${customerId}-${t.suffix}`,
    customer_id: customerId,
    talent_id: null,
    rm_id: STUB_SESSION.id,
    tier_class: t.tier_class,
    urgency: t.urgency,
    action_card: { headline: t.headline, action_type: t.action_type },
    why_oneline: t.why_oneline,
    why_detail: t.why_detail,
    modifiable_fields: ["headline", "summary"],
    source_episodes: [`sfdc:${customerId}-placements`],
    proposed_at: new Date(Date.now() - i * 3_600_000).toISOString(),
    status: "pending" as const,
    rank_score: 0.8 - i * 0.15,
    skill_id: null,
  }));
}

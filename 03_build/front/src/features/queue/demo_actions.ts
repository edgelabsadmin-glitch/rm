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

const DHR_ARR = formatARR(accountARR("dhr-health-clinics")); // $760K
const NAVADERM_ARR = formatARR(accountARR("navaderm"));
const BAYHEALTH_EXPANSION = formatARR(12 * REVENUE_PER_SEAT_USD); // +$120K incremental

export const DEMO_ACTIONS: ActionDTO[] = [
  {
    action_id: "demo-dhr-escalation",
    customer_id: "dhr-health-clinics",
    talent_id: null,
    rm_id: "sidra-zia",
    tier_class: "Enterprise",
    urgency: "high",
    action_card: { headline: "Escalate DHR Health Clinics renewal", action_type: "escalation" },
    why_oneline: `Churn crossed 50% — ${DHR_ARR} at stake. ${rmName("sidra-zia")} needs air cover.`,
    why_detail:
      `<bad>Vendor-consolidation</bad> surfaced across two recent calls and the replacement rate ` +
      `is up this quarter. <num>${DHR_ARR}</num> ARR is at stake on the renewal. Pulse drafted ` +
      `talking points and can hold a Thursday slot so <em>${rmName("sidra-zia")}</em> gets VP-CS air cover.`,
    modifiable_fields: ["headline", "talking_points", "meeting_time"],
    source_episodes: ["chorus:dhr-2026-05-19", "sfdc:case-dhr-escalation"],
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
    action_card: { headline: "Route Bayhealth expansion to VP-CS", action_type: "expansion" },
    why_oneline: `12-nurse need identified — ${BAYHEALTH_EXPANSION} ARR potential.`,
    why_detail:
      `<em>${rmName("ameer-ali")}</em> surfaced a 12-nurse expansion need at Bayhealth — roughly ` +
      `<good>+${BAYHEALTH_EXPANSION} ARR</good> (<num>${BAYHEALTH_EXPANSION}</num>) on top of the ` +
      `current book. Ready for VP-CS framing.`,
    modifiable_fields: ["headline", "summary"],
    source_episodes: ["opp-tracker:bayhealth-postings", "chorus:bayhealth-2026-05-18"],
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
    action_card: { headline: "Make NAVADERM the Q3 reference customer", action_type: "reference" },
    why_oneline: `14 healthy placements, no escalations — ${NAVADERM_ARR} book.`,
    why_detail:
      `NAVADERM has <good>14 healthy placements</good> and zero escalations this quarter — a ` +
      `<num>${NAVADERM_ARR}</num> book that's <em>${rmName("mubeen-sohail")}</em>'s quiet win. ` +
      `Strong Q3 reference candidate.`,
    modifiable_fields: ["headline", "summary"],
    source_episodes: ["sfdc:navaderm-csat", "chorus:navaderm-2026-05-15"],
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

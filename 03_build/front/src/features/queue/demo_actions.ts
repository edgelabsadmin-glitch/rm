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
import type { UserRole } from "@/lib/rbac/types";
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
 * Filter the demo cards the way GET /api/actions would. Role-aware (spec 042 A3 re-anchor):
 * RMs see only their own book (filter by rm_id); Manager / Executive / Admin see the full
 * book (the rm_id self-filter is skipped — their "My Queue" rm_id wouldn't match RM-owned
 * cards anyway). Tier + customer filters always apply. Real scoping is server-side (spec 042
 * Caller model). `callerRole` defaults to undefined = unscoped (legacy / pre-RBAC).
 */
export function filterDemoActions(
  filters: QueueFilters = {},
  callerRole?: UserRole,
): ActionsResponse {
  let actions = DEMO_ACTIONS;
  if (filters.rm_id && callerRole === "rm") {
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

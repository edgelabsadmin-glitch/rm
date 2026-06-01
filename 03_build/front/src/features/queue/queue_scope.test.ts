import { describe, expect, it } from "vitest";
import { DEMO_ACTIONS } from "./demo_actions";
import {
  applyStatusFilter,
  applyTimeFilter,
  scopeAndRefineCards,
  visibleRmIdsForCaller,
} from "./queue_scope";

// DEMO_ACTIONS (5) rm_ids: DHR→sidra-zia, Bayhealth→ameer-ali, NAVADERM→mubeen-sohail,
// Mendota→sajjal-shaheedi, Cirventis→sajjal-shaheedi.

describe("visibleRmIdsForCaller (spec-042 Step-5)", () => {
  it("admin → null (no filter, sees all)", () => {
    expect(visibleRmIdsForCaller("admin", "pulse-admin")).toBeNull();
  });
  it("rm → only their own id", () => {
    expect(visibleRmIdsForCaller("rm", "sidra-zia")).toEqual(["sidra-zia"]);
  });
  it("manager → their team's rm ids", () => {
    expect(new Set(visibleRmIdsForCaller("manager", "sarah-hooper"))).toEqual(
      new Set(["sajjal-shaheedi", "sidra-zia", "yozeline-candia"]),
    );
    expect(new Set(visibleRmIdsForCaller("manager", "muhammad-ibrahim"))).toEqual(
      new Set(["ameer-ali", "mubeen-sohail", "akash-tahir"]),
    );
  });
  it("executive → [] (route-blocked; defensive)", () => {
    expect(visibleRmIdsForCaller("executive", "iffi-wahla")).toEqual([]);
  });
});

describe("scopeAndRefineCards — scope (security) then URL ?rm= (UX)", () => {
  it("admin sees all cards", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "admin", "pulse-admin")).toHaveLength(7);
  });
  it("RM sees only their own cards (Sidra → 2 DHR cards: pending churn + approved follow-up)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia");
    expect(cards).toHaveLength(2);
    expect(cards.every((c) => c.rm_id === "sidra-zia")).toBe(true);
  });
  it("RM with no demo card (Yozeline) → empty", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "yozeline-candia")).toHaveLength(0);
  });
  it("Manager Sarah → 4 team cards (scope is status-agnostic: DHR pending + DHR approved + Mendota + Cirventis)", () => {
    // scopeAndRefineCards filters by rm_id only (no status filter), so the approved Sidra/DHR
    // card is in scope too. Status filtering is a separate UX layer (applyStatusFilter).
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper");
    expect(cards).toHaveLength(4);
    expect(new Set(cards.map((c) => c.rm_id))).toEqual(new Set(["sidra-zia", "sajjal-shaheedi"]));
  });
  it("Manager Muhammad → team cards (Bayhealth + NAVADERM)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "manager", "muhammad-ibrahim");
    expect(new Set(cards.map((c) => c.rm_id))).toEqual(new Set(["ameer-ali", "mubeen-sohail"]));
  });
  it("executive → empty (route-blocked)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "executive", "iffi-wahla")).toHaveLength(0);
  });

  // URL ?rm= refinement applied ON TOP of scope (cannot widen).
  it("RM + own ?rm= → no-op (still her 2 cards)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia", "sidra-zia")).toHaveLength(2);
  });
  it("RM + other ?rm= → empty (cannot escape scope)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia", "ameer-ali")).toHaveLength(0);
  });
  it("Manager + in-team ?rm= → that RM's cards within team (Sidra → 2)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "sidra-zia")).toHaveLength(2);
  });
  it("Manager + out-of-team ?rm= → empty (cannot escape scope)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "ameer-ali")).toHaveLength(0);
  });
  it("admin + ?rm= → just that RM's cards (Ameer → 2: Bayhealth expansion + approved outreach)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "admin", "pulse-admin", "ameer-ali")).toHaveLength(2);
  });

  it("Manager Sarah + ?rm=sajjal-shaheedi → narrows to Sajjal's 2 cards (Story B investigate)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "sajjal-shaheedi");
    expect(cards).toHaveLength(2);
    expect(cards.every((c) => c.rm_id === "sajjal-shaheedi")).toBe(true);
  });
});

describe("applyStatusFilter / applyTimeFilter (spec-042 Step-5 follow-up Q3)", () => {
  const NOW = new Date("2026-05-22T12:00:00Z").getTime();
  const cards = [
    { status: "pending", proposed_at: "2026-05-22T06:00:00Z" }, // 6h ago — today
    { status: "approved", proposed_at: "2026-05-20T12:00:00Z" }, // 2d ago — this week
    { status: "pending", proposed_at: "2026-05-10T12:00:00Z" }, // 12d ago — older
  ];

  it("status 'active' → only pending", () => {
    expect(applyStatusFilter(cards, "active")).toHaveLength(2);
  });
  it("status 'approved' → only approved", () => {
    expect(applyStatusFilter(cards, "approved")).toHaveLength(1);
  });
  it("status 'all' → no filter", () => {
    expect(applyStatusFilter(cards, "all")).toHaveLength(3);
  });
  it("time 'today' → within 24h", () => {
    expect(applyTimeFilter(cards, "today", NOW)).toHaveLength(1);
  });
  it("time 'this-week' → within 7d", () => {
    expect(applyTimeFilter(cards, "this-week", NOW)).toHaveLength(2);
  });
  it("time 'all-time' → no filter", () => {
    expect(applyTimeFilter(cards, "all-time", NOW)).toHaveLength(3);
  });
  it("status + time combine cumulatively (active AND today)", () => {
    const combined = applyTimeFilter(applyStatusFilter(cards, "active"), "today", NOW);
    expect(combined).toHaveLength(1);
  });
});

describe("applyStatusFilter against the real DEMO_ACTIONS (5 pending + 2 approved)", () => {
  it("'approved' → 2 cards", () => {
    expect(applyStatusFilter(DEMO_ACTIONS, "approved")).toHaveLength(2);
  });
  it("'active' → 5 cards (pending)", () => {
    expect(applyStatusFilter(DEMO_ACTIONS, "active")).toHaveLength(5);
  });
  it("'all' → 7 cards", () => {
    expect(applyStatusFilter(DEMO_ACTIONS, "all")).toHaveLength(7);
  });
});

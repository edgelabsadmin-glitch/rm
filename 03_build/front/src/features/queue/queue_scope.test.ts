import { describe, expect, it } from "vitest";
import { DEMO_ACTIONS } from "./demo_actions";
import { scopeAndRefineCards, visibleRmIdsForCaller } from "./queue_scope";

// DEMO_ACTIONS rm_ids: DHR→sidra-zia, Bayhealth→ameer-ali, NAVADERM→mubeen-sohail.

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
    expect(scopeAndRefineCards(DEMO_ACTIONS, "admin", "pulse-admin")).toHaveLength(3);
  });
  it("RM sees only their own card (Sidra → DHR)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia");
    expect(cards).toHaveLength(1);
    expect(cards[0].rm_id).toBe("sidra-zia");
  });
  it("RM with no demo card (Yozeline) → empty", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "yozeline-candia")).toHaveLength(0);
  });
  it("Manager Sarah → team cards (DHR via Sidra)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper");
    expect(cards.map((c) => c.rm_id)).toEqual(["sidra-zia"]);
  });
  it("Manager Muhammad → team cards (Bayhealth + NAVADERM)", () => {
    const cards = scopeAndRefineCards(DEMO_ACTIONS, "manager", "muhammad-ibrahim");
    expect(new Set(cards.map((c) => c.rm_id))).toEqual(new Set(["ameer-ali", "mubeen-sohail"]));
  });
  it("executive → empty (route-blocked)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "executive", "iffi-wahla")).toHaveLength(0);
  });

  // URL ?rm= refinement applied ON TOP of scope (cannot widen).
  it("RM + own ?rm= → no-op (still own card)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia", "sidra-zia")).toHaveLength(1);
  });
  it("RM + other ?rm= → empty (cannot escape scope)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "sidra-zia", "ameer-ali")).toHaveLength(0);
  });
  it("Manager + in-team ?rm= → that RM's cards within team", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "sidra-zia")).toHaveLength(1);
  });
  it("Manager + out-of-team ?rm= → empty (cannot escape scope)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "ameer-ali")).toHaveLength(0);
  });
  it("admin + ?rm= → just that RM's cards", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "admin", "pulse-admin", "ameer-ali")).toHaveLength(1);
  });
});

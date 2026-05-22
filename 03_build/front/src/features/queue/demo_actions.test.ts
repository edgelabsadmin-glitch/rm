import { describe, expect, it } from "vitest";
import { DEMO_ACTIONS, filterDemoActions } from "./demo_actions";

describe("DEMO_ACTIONS fixture shape (spec-042 Step-5 follow-up Q1 — Sajjal seeds)", () => {
  it("has 5 cards", () => {
    expect(DEMO_ACTIONS).toHaveLength(5);
  });
  it("Sajjal owns exactly 2 cards (Mendota + Cirventis)", () => {
    const sajjal = DEMO_ACTIONS.filter((a) => a.rm_id === "sajjal-shaheedi");
    expect(sajjal).toHaveLength(2);
    expect(new Set(sajjal.map((a) => a.customer_id))).toEqual(
      new Set(["mendota-insurance", "cirventis"]),
    );
  });
  it("every card has the same ActionDTO field shape (no missing/extra keys)", () => {
    const keys = Object.keys(DEMO_ACTIONS[0]).sort();
    for (const card of DEMO_ACTIONS) {
      expect(Object.keys(card).sort()).toEqual(keys);
    }
  });
});

describe("filterDemoActions role-aware fallback (spec-042 Step-2 A3 re-anchor)", () => {
  const TOTAL = DEMO_ACTIONS.length; // 5 demo cards

  it("RM sees only their own book (filters by rm_id)", () => {
    const res = filterDemoActions({ rm_id: "sidra-zia" }, "rm");
    expect(res.actions.every((a) => a.rm_id === "sidra-zia")).toBe(true);
    expect(res.actions.length).toBeLessThan(TOTAL);
    expect(res.actions.length).toBeGreaterThan(0);
  });

  it("Manager sees the full book (rm_id self-filter skipped)", () => {
    const res = filterDemoActions({ rm_id: "sarah-hooper" }, "manager");
    expect(res.actions).toHaveLength(TOTAL);
  });

  it("Executive sees the full book", () => {
    const res = filterDemoActions({ rm_id: "iffi-wahla" }, "executive");
    expect(res.actions).toHaveLength(TOTAL);
  });

  it("Admin sees the full book", () => {
    const res = filterDemoActions({ rm_id: "pulse-admin" }, "admin");
    expect(res.actions).toHaveLength(TOTAL);
  });

  it("undefined role (legacy/unscoped) does not rm-filter", () => {
    expect(filterDemoActions({ rm_id: "sidra-zia" }).actions).toHaveLength(TOTAL);
  });

  it("tier filter applies regardless of role", () => {
    const all = filterDemoActions({}, "admin").actions;
    const tier = all[0]?.tier_class;
    if (tier) {
      const res = filterDemoActions({ tier }, "admin");
      expect(res.actions.every((a) => a.tier_class === tier)).toBe(true);
    }
  });
});

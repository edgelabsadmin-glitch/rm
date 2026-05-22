import { describe, expect, it } from "vitest";
import { DEMO_ACTIONS, filterDemoActions } from "./demo_actions";

describe("filterDemoActions role-aware fallback (spec-042 Step-2 A3 re-anchor)", () => {
  const TOTAL = DEMO_ACTIONS.length; // 3 demo cards

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

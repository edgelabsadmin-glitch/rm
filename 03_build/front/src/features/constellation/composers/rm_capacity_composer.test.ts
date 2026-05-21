import { describe, expect, it } from "vitest";
import {
  composeCapacityImbalance,
  computeRmLoads,
} from "./rm_capacity_composer";

describe("rm_capacity_composer (spec-041 Step-6, derived from canonical fixture)", () => {
  it("computes per-RM loads for every demo RM", () => {
    const loads = computeRmLoads();
    expect(loads).toHaveLength(6);
    const sajjal = loads.find((l) => l.rmId === "sajjal-shaheedi")!;
    // Sajjal owns Mendota (at-risk) + DMV (healthy) + Cirventis (at-risk).
    expect(sajjal.accountCount).toBe(3);
    expect(sajjal.churnExposureCount).toBe(2);
    expect(sajjal.totalARR).toBe(760_000);
    expect(sajjal.riskWeightedScore).toBeCloseTo(2.76, 2); // 2 + 760000/1e6
  });

  it("riskWeightedScore = churnExposureCount + totalARR/1e6", () => {
    const loads = computeRmLoads();
    for (const l of loads) {
      expect(l.riskWeightedScore).toBeCloseTo(l.churnExposureCount + l.totalARR / 1_000_000, 6);
    }
  });

  it("emits one imbalance card for the demo data (top score > 2× median)", () => {
    const cards = composeCapacityImbalance();
    expect(cards).toHaveLength(1);
    const c = cards[0];
    expect(c.id).toBe("capacity-imbalance-001");
    // Top-loaded is Sajjal (2 churn-state accounts), NOT Sidra (1) — derived, not assumed.
    expect(c.topLoadedRmId).toBe("sajjal-shaheedi");
    expect(c.topLoadedRmName).toBe("Sajjal Shaheedi");
    expect(c.topLoadedAccountCount).toBe(3);
    expect(c.topLoadedChurnExposureCount).toBe(2);
    expect(c.topLoadedARR).toBe(760_000);
    expect(c.topLoadedScore).toBeCloseTo(2.76, 2);
  });

  it("compares against the lowest-loaded teammate under the same manager", () => {
    const c = composeCapacityImbalance()[0];
    expect(c.managerId).toBe("sarah-hooper");
    expect(c.managerName).toBe("Sarah Hooper");
    // Sarah's team: Sajjal (2.76), Sidra (1.99), Yozeline (1.1) → lowest is Yozeline.
    expect(c.comparisonRmId).toBe("yozeline-candia");
    expect(c.comparisonRmName).toBe("Yozeline Candia");
    expect(c.comparisonScore).toBeCloseTo(1.1, 2);
  });

  it("the top-loaded RM is in the comparison RM's manager team (same manager)", () => {
    const c = composeCapacityImbalance()[0];
    const loads = computeRmLoads();
    const top = loads.find((l) => l.rmId === c.topLoadedRmId)!;
    const cmp = loads.find((l) => l.rmId === c.comparisonRmId)!;
    expect(top.managerId).toBe(cmp.managerId);
    expect(top.riskWeightedScore).toBeGreaterThan(cmp.riskWeightedScore);
  });
});

/*
 * SPEC-042 Step-8 (§6.7) — nodeTooltip workload extension.
 * The Constellation tooltip is react-force-graph's `nodeLabel` string (rendered as HTML), not a
 * JSX hover component — so the workload extension is unit-tested at the string-builder level
 * (canvas-free, the established Constellation testing pattern). RM nodes gain a workload line for
 * Executive + Admin viewers ONLY; every other role and node type is unchanged.
 */
import { describe, expect, it } from "vitest";
import type { ConstellationNode } from "./fixtures";
import { nodeTooltip } from "./ForceGraph";

// Sajjal owns 3 accounts (Mendota/DMV/Cirventis) and carries 2 pending cards in the fixture.
const sajjalRm: ConstellationNode = {
  id: "sajjal-shaheedi",
  type: "rm",
  label: "Sajjal Shaheedi",
  size: 10,
};

describe("nodeTooltip — base content preserved for all roles (spec-041 Step-4)", () => {
  it("RM node always shows book ARR + account count", () => {
    for (const role of ["rm", "manager", "executive", "admin", undefined] as const) {
      const t = nodeTooltip(sajjalRm, role);
      expect(t).toContain("Sajjal Shaheedi");
      expect(t).toMatch(/book/);
      expect(t).toMatch(/account/);
    }
  });
});

describe("nodeTooltip — workload section gated to Executive + Admin (spec-042 §6.7)", () => {
  it("appends workload metrics for an Executive viewer", () => {
    const t = nodeTooltip(sajjalRm, "executive");
    expect(t).toContain("pending");
    expect(t).toContain("approved this week");
  });

  it("appends workload metrics for an Admin viewer", () => {
    const t = nodeTooltip(sajjalRm, "admin");
    expect(t).toContain("pending");
    expect(t).toContain("approved this week");
  });

  it("does NOT append workload for an RM viewer", () => {
    expect(nodeTooltip(sajjalRm, "rm")).not.toContain("pending");
  });

  it("does NOT append workload for a Manager viewer", () => {
    expect(nodeTooltip(sajjalRm, "manager")).not.toContain("pending");
  });

  it("does NOT append workload when no viewer role is supplied", () => {
    expect(nodeTooltip(sajjalRm)).not.toContain("pending");
  });

  it("workload section is RM-node only — account/manager/globe nodes never get it", () => {
    const account: ConstellationNode = {
      id: "dhr-health-clinics",
      type: "account",
      label: "DHR Health Clinics",
      size: 8,
      rm_id: "sidra-zia",
    };
    const manager: ConstellationNode = {
      id: "sarah-hooper",
      type: "manager",
      label: "Sarah Hooper",
      size: 12,
    };
    expect(nodeTooltip(account, "executive")).not.toContain("pending");
    expect(nodeTooltip(manager, "executive")).not.toContain("pending");
  });
});

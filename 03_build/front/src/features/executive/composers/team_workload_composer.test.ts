import { describe, expect, it } from "vitest";
import { DEMO_ACTIONS } from "@/features/queue/demo_actions";
import { DEMO_RMS } from "@/fixtures/demo_characters";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import { composeTeamWorkload } from "./team_workload_composer";

// Fixed clock: the demo anchor week. Both approved cards (Sidra/DHR 2026-05-18, Ameer/Bayhealth
// 2026-05-16) fall inside the 7-day window ending here.
const NOW = new Date("2026-05-22T12:00:00Z");
const compose = (scope?: ReturnType<typeof deriveAccountScope>) =>
  composeTeamWorkload(DEMO_RMS, DEMO_ACTIONS, scope, NOW);
const rowFor = (scope: ReturnType<typeof deriveAccountScope> | undefined, rmId: string) =>
  compose(scope).find((r) => r.rmId === rmId)!;

describe("composeTeamWorkload — scope filtering (spec-042 Step-8)", () => {
  it("unscoped (full org) → all 6 RMs", () => {
    expect(compose(undefined)).toHaveLength(6);
  });

  it("Executive / Admin full-org scope → all 6 RMs", () => {
    expect(compose(deriveAccountScope("admin", "pulse-admin"))).toHaveLength(6);
    expect(compose(deriveAccountScope("executive", "iffi-wahla"))).toHaveLength(6);
  });

  it("Sarah's team scope → her 3 RMs (Sajjal, Sidra, Yozeline)", () => {
    const rows = compose(deriveAccountScope("manager", "sarah-hooper"));
    expect(rows).toHaveLength(3);
    expect(new Set(rows.map((r) => r.rmId))).toEqual(
      new Set(["sajjal-shaheedi", "sidra-zia", "yozeline-candia"]),
    );
  });

  it("Muhammad's team scope → his 3 RMs (Ameer, Mubeen, Akash)", () => {
    const rows = compose(deriveAccountScope("manager", "muhammad-ibrahim"));
    expect(rows).toHaveLength(3);
    expect(new Set(rows.map((r) => r.rmId))).toEqual(
      new Set(["ameer-ali", "mubeen-sohail", "akash-tahir"]),
    );
  });

  it("Yozeline's RM scope (Manhattan only) → just herself", () => {
    const rows = compose(deriveAccountScope("rm", "yozeline-candia"));
    expect(rows).toHaveLength(1);
    expect(rows[0].rmId).toBe("yozeline-candia");
  });
});

describe("composeTeamWorkload — per-RM metrics derived from canonical DEMO_ACTIONS", () => {
  it("Sajjal: 2 pending (Mendota + Cirventis), 0 approved this week → flat", () => {
    const sajjal = rowFor(undefined, "sajjal-shaheedi");
    expect(sajjal.pendingCount).toBe(2);
    expect(sajjal.approvedThisWeek).toBe(0);
    expect(sajjal.throughputIndicator).toBe("flat");
    expect(sajjal.combinedLoad).toBe(2);
  });

  it("Sidra: 1 pending (DHR churn), 1 approved this week (DHR follow-up) → steady", () => {
    const sidra = rowFor(undefined, "sidra-zia");
    expect(sidra.pendingCount).toBe(1);
    expect(sidra.approvedThisWeek).toBe(1);
    expect(sidra.throughputIndicator).toBe("steady");
    expect(sidra.combinedLoad).toBe(1.5);
  });

  it("Ameer: 1 pending (Bayhealth expansion), 1 approved this week (Bayhealth outreach) → steady", () => {
    const ameer = rowFor(undefined, "ameer-ali");
    expect(ameer.pendingCount).toBe(1);
    expect(ameer.approvedThisWeek).toBe(1);
    expect(ameer.throughputIndicator).toBe("steady");
  });

  it("modifiedThisWeek / rejectedThisWeek resolve to 0 (statuses absent from Phase-1A fixture)", () => {
    for (const row of compose(undefined)) {
      expect(row.modifiedThisWeek).toBe(0);
      expect(row.rejectedThisWeek).toBe(0);
    }
  });

  it("avatarInitials derived from rm.name (matches DEMO_USERS conventions)", () => {
    const initials = Object.fromEntries(compose(undefined).map((r) => [r.rmId, r.avatarInitials]));
    expect(initials["sajjal-shaheedi"]).toBe("SS");
    expect(initials["sidra-zia"]).toBe("SZ");
    expect(initials["yozeline-candia"]).toBe("YC");
    expect(initials["ameer-ali"]).toBe("AA");
    expect(initials["mubeen-sohail"]).toBe("MS");
    expect(initials["akash-tahir"]).toBe("AT");
  });
});

describe("composeTeamWorkload — sort by combinedLoad descending", () => {
  it("Sajjal (2.0) sorts first; rows are non-increasing by combinedLoad", () => {
    const rows = compose(undefined);
    expect(rows[0].rmId).toBe("sajjal-shaheedi");
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].combinedLoad).toBeGreaterThanOrEqual(rows[i].combinedLoad);
    }
  });

  it("stable order within equal load: Sidra before Ameer (both 1.5)", () => {
    const ids = compose(undefined).map((r) => r.rmId);
    expect(ids.indexOf("sidra-zia")).toBeLessThan(ids.indexOf("ameer-ali"));
  });
});

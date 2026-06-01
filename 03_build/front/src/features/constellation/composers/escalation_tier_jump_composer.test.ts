import { describe, expect, it } from "vitest";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { TierJumpEvent } from "@/fixtures/demo_tier_jump_events";
import { composeEscalationTierJumps } from "./escalation_tier_jump_composer";

const BASE: TierJumpEvent = {
  id: "tier-jump-demo-001",
  accountId: "manhattan-restorative",
  previousTier: "watch",
  newTier: "at-risk",
  occurredAt: "2026-05-21T08:00:00Z",
  reason: "Composite health declined past at-risk threshold",
};
const NOW = new Date("2026-05-21T20:00:00Z").getTime(); // 12h after the event
// Signature (spec-042 Step-4): composeEscalationTierJumps(events, accountScope?, now?)

describe("escalation_tier_jump_composer (spec-041 Step-7)", () => {
  it("emits a hydrated card for an event inside the 48h window", () => {
    const cards = composeEscalationTierJumps([BASE], undefined, NOW);
    expect(cards).toHaveLength(1);
    const c = cards[0];
    expect(c.id).toBe("escalation-tier-jump-demo-001");
    expect(c.accountId).toBe("manhattan-restorative");
    expect(c.accountName).toBe("Manhattan Restorative Health Sciences");
    expect(c.owningRmId).toBe("yozeline-candia");
    expect(c.owningRmName).toBe("Yozeline Candia");
    expect(c.previousTier).toBe("watch");
    expect(c.newTier).toBe("at-risk");
    expect(c.hoursAgo).toBe(12);
    expect(c.reason).toBe(BASE.reason);
  });

  it("filters out events older than 48h", () => {
    const old = new Date("2026-05-24T20:00:00Z").getTime();
    expect(composeEscalationTierJumps([BASE], undefined, old)).toHaveLength(0);
  });

  it("filters out future-dated events (negative elapsed)", () => {
    const before = new Date("2026-05-20T00:00:00Z").getTime();
    expect(composeEscalationTierJumps([BASE], undefined, before)).toHaveLength(0);
  });

  it("skips events whose account is not in the canonical fixture", () => {
    const bogus = { ...BASE, accountId: "no-such-account" as TierJumpEvent["accountId"] };
    expect(composeEscalationTierJumps([bogus], undefined, NOW)).toHaveLength(0);
  });

  it("returns empty for no events", () => {
    expect(composeEscalationTierJumps([], undefined, NOW)).toHaveLength(0);
  });
});

describe("escalation_tier_jump_composer — accountScope filtering (spec-042 Step-4)", () => {
  it("undefined scope → unscoped (same as no filter)", () => {
    expect(composeEscalationTierJumps([BASE], undefined, NOW)).toHaveLength(1);
  });

  it("empty scope → no events", () => {
    expect(composeEscalationTierJumps([BASE], [], NOW)).toHaveLength(0);
  });

  it("Manhattan in scope → event surfaces", () => {
    expect(composeEscalationTierJumps([BASE], ["manhattan-restorative"], NOW)).toHaveLength(1);
  });

  it("Manhattan NOT in scope (DHR-only) → event filtered out", () => {
    expect(composeEscalationTierJumps([BASE], ["dhr-health-clinics"], NOW)).toHaveLength(0);
  });

  it("Yozeline's scope includes Manhattan → event surfaces", () => {
    const scope = deriveAccountScope("rm", "yozeline-candia");
    expect(composeEscalationTierJumps([BASE], scope, NOW)).toHaveLength(1);
  });

  it("full org scope → event surfaces", () => {
    const scope = deriveAccountScope("admin", "pulse-admin");
    expect(composeEscalationTierJumps([BASE], scope, NOW)).toHaveLength(1);
  });
});

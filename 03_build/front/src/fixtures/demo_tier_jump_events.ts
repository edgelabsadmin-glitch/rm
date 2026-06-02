/*
 * SPEC-041 Step-7 — composite health tier-jump events (Design 07 dual-sided health).
 * Phase-1 demo fixture: real `health-tier-changed` events flow from pulse-api at the
 * Week-4 cutover. Real-data integrity (Session 19): the `reason` is GENERALIZED ("composite
 * health declined past threshold") — never a fabricated qualitative cause; account/RM are
 * hydrated from the canonical fixture by the composer.
 */
import type { DemoAccountId } from "./demo_characters";

export type HealthTier = "healthy" | "watch" | "at-risk" | "escalated";

export interface TierJumpEvent {
  id: string;
  accountId: DemoAccountId;
  previousTier: HealthTier;
  newTier: HealthTier;
  occurredAt: string; // ISO timestamp
  reason: string; // generalized; honest-data-only
}

// Single demo event. Manhattan Restorative is churn-signal in the canonical fixture, so a
// watch→at-risk escalation is consistent with its existing state.
export const DEMO_TIER_JUMP_EVENTS: TierJumpEvent[] = [
  {
    id: "tier-jump-demo-001",
    accountId: "manhattan-restorative",
    previousTier: "watch",
    newTier: "at-risk",
    occurredAt: "2026-05-21T08:00:00Z", // recent — within 48h of the demo "now" (2026-05-22)
    reason: "Composite health declined past at-risk threshold",
  },
];

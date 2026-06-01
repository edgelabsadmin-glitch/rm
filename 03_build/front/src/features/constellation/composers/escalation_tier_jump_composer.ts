/*
 * SPEC-041 Step-7 — escalation tier-jump composer (the third agentic overlay's brain).
 * Pure function, no React. Filters tier-jump events to the recent window (< 48h) and
 * hydrates each from the canonical fixture (account name, owning RM id + name, hoursAgo).
 * Real-data principle: every field is derived; the `reason` is the generalized fixture
 * string. No fabricated cause prose.
 */
import { DEMO_ACCOUNTS, DEMO_RMS, type DemoAccountId } from "@/fixtures/demo_characters";
import type { AccountScope } from "@/lib/rbac/types";
import {
  DEMO_TIER_JUMP_EVENTS,
  type HealthTier,
  type TierJumpEvent,
} from "@/fixtures/demo_tier_jump_events";

export const TIER_JUMP_WINDOW_MS = 48 * 60 * 60 * 1000; // 48h "active" window

export interface EscalationTierJumpCard {
  id: string;
  accountId: DemoAccountId;
  accountName: string;
  previousTier: HealthTier;
  newTier: HealthTier;
  occurredAt: string;
  hoursAgo: number;
  owningRmId: string;
  owningRmName: string;
  reason: string;
}

/**
 * Compose escalation cards for tier-jump events within the active window. Spec 042 Step-4:
 * events whose `accountId` is outside `accountScope` are filtered out before hydration
 * (watched concern #26). `accountScope` undefined = unscoped. `now` is injectable for
 * deterministic tests; defaults to wall-clock. Events whose account is missing from the
 * fixture are skipped (defensive).
 */
export function composeEscalationTierJumps(
  events: ReadonlyArray<TierJumpEvent> = DEMO_TIER_JUMP_EVENTS,
  accountScope?: AccountScope,
  now: number = Date.now(),
): EscalationTierJumpCard[] {
  const scopedEvents = accountScope
    ? events.filter((e) => accountScope.includes(e.accountId))
    : events;
  const cards: EscalationTierJumpCard[] = [];
  for (const ev of scopedEvents) {
    const elapsed = now - new Date(ev.occurredAt).getTime();
    if (elapsed < 0 || elapsed >= TIER_JUMP_WINDOW_MS) continue; // outside the 48h window
    const account = DEMO_ACCOUNTS.find((a) => a.id === ev.accountId);
    if (!account) continue;
    const rm = DEMO_RMS.find((r) => r.id === account.rmId);
    cards.push({
      id: `escalation-${ev.id}`,
      accountId: ev.accountId,
      accountName: account.name,
      previousTier: ev.previousTier,
      newTier: ev.newTier,
      occurredAt: ev.occurredAt,
      hoursAgo: Math.round(elapsed / (60 * 60 * 1000)),
      owningRmId: account.rmId,
      owningRmName: rm?.name ?? account.rmId,
      reason: ev.reason,
    });
  }
  return cards;
}

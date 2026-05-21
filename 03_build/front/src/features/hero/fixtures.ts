/*
 * SPEC-036 — Hero mock data (pulse-api not deployed; live binding is Week 4).
 *
 * API contract this surface WILL consume (so spec 030 dual-sided health wires in
 * Week 4 without UI changes):
 *
 *   GET /accounts/{id}/health  →  {
 *     account_id: string,
 *     name: string,                      // display name (Account.Name)
 *     composite_health: number,          // 0..10 for the ring  ← SEE NORMALIZATION NOTE
 *     tier: string,                       // Healthy|Stable|Watch|At-Risk|Escalated (spec 030)
 *     positioning: string,                // AI-RM voice paragraph (per-account context)
 *   }
 *
 * NORMALIZATION NOTE / FLAG: spec 030 (core/health/dual_sided.py) produces
 * composite_score in -100..+100, not 0..10. The ring + preview use 0..10. The
 * Week-4 wiring must map -100..100 → 0..10 (e.g. (score+100)/20) at the endpoint
 * or in a thin adapter. Flagged for PM; not resolved here.
 */
export interface AccountHealth {
  account_id: string;
  name: string;
  composite_health: number; // 0..10
  tier: string;
  positioning: string;
}

// The Tier-0 §10 AI-RM voice anchor (DoD-mandated subtitle).
export const AI_RM_POSITIONING =
  "Pulse is prioritizing evidence, next best action, and stakeholder context. " +
  "No auto-send. Every customer-facing move waits for RM approval.";

// Static descriptor pills (what Pulse IS, not per-account data — Tier-0 §10 "Pulse Facts").
export const PULSE_FACTS = [
  "Temporal account memory",
  "Evidence-backed signals",
  "RM approval before action",
  "Customer + talent health",
] as const;

// Phase-1 demo fixture — Helix Labs (preview anchor; composite_health 6.4).
const FIXTURES: Record<string, AccountHealth> = {
  "helix-labs": {
    account_id: "helix-labs",
    name: "Helix Labs",
    composite_health: 6.4,
    tier: "Watch",
    positioning: AI_RM_POSITIONING,
  },
};

export function getAccountHealthFixture(accountId: string): AccountHealth {
  return FIXTURES[accountId] ?? FIXTURES["helix-labs"];
}

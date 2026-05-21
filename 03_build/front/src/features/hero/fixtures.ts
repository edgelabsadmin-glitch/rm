/*
 * SPEC-036/037 — Hero + per-account mock data (pulse-api not deployed; live binding
 * is Week 4).
 *
 * API contract these surfaces WILL consume (so spec 030 dual-sided health + spec 029
 * profiles wire in Week 4 without UI changes):
 *
 *   GET /accounts                 →  [{ account_id, name, composite_health(0..10),
 *                                       risk, meeting }]   // left-rail summaries
 *   GET /accounts/{id}/health     →  { account_id, name, composite_health(0..10),
 *                                       tier, positioning, signal_vector[], themes[] }
 *
 * NORMALIZATION (ratified): spec 030 produces composite_score in -100..+100; the ring
 * + preview use 0..10. UI-side mapping is (score + 100) / 20. Back-end shape stays as-is.
 */
import type { RiskLevel } from "@/components/RiskBadge";
import { DEMO_ACCOUNTS, type DemoAccount } from "@/fixtures/demo_characters";

export interface AccountSummary {
  account_id: string;
  name: string;
  composite_health: number; // 0..10
  risk: RiskLevel;
  meeting: string; // next-key-event subtitle
}

export interface SignalAxis {
  label: string;
  pct: number; // 0..100
}

export interface AccountHealth extends AccountSummary {
  tier: string; // Healthy|Stable|Watch|At-Risk|Escalated (spec 030)
  positioning: string;
  signal_vector: SignalAxis[];
  themes: string[];
}

// The Tier-0 §10 AI-RM voice anchor (DoD-mandated hero subtitle).
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

const SIGNAL_AXES = ["Engagement", "Satisfaction", "Retention safety", "Growth orientation"];

// score → 4 axes, mirroring the preview's derivation (max(54, score*10 - i*7)).
function vectorFor(score: number): SignalAxis[] {
  return SIGNAL_AXES.map((label, i) => ({
    label,
    pct: Math.max(54, Math.round(score * 10 - i * 7)),
  }));
}

// Per-account demo health derived from the canonical demo characters
// (src/fixtures/demo_characters.ts) — single source of truth, real account names.
const HEALTH_SCORE: Record<DemoAccount["healthState"], number> = {
  healthy: 8.5,
  "churn-signal": 5.2,
  "at-risk": 4.0,
};
const HEALTH_RISK: Record<DemoAccount["healthState"], RiskLevel> = {
  healthy: "Low",
  "churn-signal": "High",
  "at-risk": "Medium",
};
const HEALTH_TIER: Record<DemoAccount["healthState"], string> = {
  healthy: "Healthy",
  "churn-signal": "Watch",
  "at-risk": "At-Risk",
};
const HEALTH_THEMES: Record<DemoAccount["healthState"], string[]> = {
  healthy: ["Strong ambassador pool", "Adoption rising", "Positive performer feedback"],
  "churn-signal": [
    "<bad>Vendor-consolidation</bad> mentioned in recent calls",
    "Replacement rate elevated this quarter",
    "Champion engagement dropping",
  ],
  "at-risk": [
    "<em>Renewal window approaching</em>",
    "Open escalation case",
    "<bad>Pay-concern signal</bad> from senior talent",
  ],
};
// A few anchor accounts get a concrete next event; the rest are quiet.
const MEETINGS: Record<string, string> = {
  "dhr-health-clinics": "Renewal sync in 3 days",
  "mendota-insurance": "EBR tomorrow, 10:30 AM",
  cirventis: "Renewal sync in 5 days",
  "manhattan-restorative": "Escalation review Friday",
};

const ACCOUNTS: AccountHealth[] = DEMO_ACCOUNTS.map((a) => {
  const score = HEALTH_SCORE[a.healthState];
  return {
    account_id: a.id,
    name: a.name,
    composite_health: score,
    risk: HEALTH_RISK[a.healthState],
    meeting: MEETINGS[a.id] ?? "No meeting scheduled",
    tier: HEALTH_TIER[a.healthState],
    positioning: AI_RM_POSITIONING,
    signal_vector: vectorFor(score),
    themes: HEALTH_THEMES[a.healthState],
  };
});

export function getAccountSummaries(): AccountSummary[] {
  return ACCOUNTS.map(({ account_id, name, composite_health, risk, meeting }) => ({
    account_id,
    name,
    composite_health,
    risk,
    meeting,
  }));
}

export function getAccountHealthFixture(accountId: string): AccountHealth {
  return ACCOUNTS.find((a) => a.account_id === accountId) ?? ACCOUNTS[0];
}

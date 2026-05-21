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

// Phase-1 demo accounts — match the React preview / Image 1 left rail.
const ACCOUNTS: AccountHealth[] = [
  {
    account_id: "helix-labs",
    name: "Helix Labs",
    composite_health: 6.4,
    risk: "High",
    meeting: "Renewal sync in 3 days",
    tier: "Watch",
    positioning: AI_RM_POSITIONING,
    signal_vector: vectorFor(6.4),
    themes: [
      "AI displacement concern",
      "Pay concern from senior talent",
      "Champion quiet for 21 days",
    ],
  },
  {
    account_id: "mendota-health",
    name: "Mendota Health",
    composite_health: 7.8,
    risk: "Medium",
    meeting: "EBR tomorrow, 10:30 AM",
    tier: "Stable",
    positioning: AI_RM_POSITIONING,
    signal_vector: vectorFor(7.8),
    themes: ["Burnout mentions easing", "Recognition gap still recurring", "2 open case themes"],
  },
  {
    account_id: "vertex-group",
    name: "Vertex Group",
    composite_health: 8.9,
    risk: "Low",
    meeting: "No meeting scheduled",
    tier: "Healthy",
    positioning: AI_RM_POSITIONING,
    signal_vector: vectorFor(8.9),
    themes: ["Strong ambassador pool", "Positive performer feedback", "Adoption rising"],
  },
];

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

/*
 * SPEC-041 Step-6 — RM capacity-imbalance composer (the second agentic overlay's brain).
 * Pure function, no React. EVERY number is derived from the canonical demo_characters.ts
 * (real-data principle, Session 19): rmBookARR for the dollar book, account/churn counts
 * from the account states. No hardcoded figures, no prose claims about cause — it only
 * surfaces the pattern; the human interprets via Investigate.
 *
 * riskWeightedScore = churnExposureCount + (totalARR / 1_000_000): a single comparable
 * scalar blending volume-of-risk (accounts in at-risk/churn-signal) with dollar exposure.
 * Imbalance trigger (Phase-1 heuristic): top RM's score > 2 × the team-median score.
 */
import {
  accountARR,
  DEMO_ACCOUNTS,
  DEMO_MANAGERS,
  DEMO_RMS,
  type DemoAccount,
  type DemoRM,
} from "@/fixtures/demo_characters";
import type { AccountScope } from "@/lib/rbac/types";

export interface CapacityImbalanceCard {
  id: string;
  topLoadedRmId: string;
  topLoadedRmName: string;
  topLoadedScore: number;
  topLoadedAccountCount: number;
  topLoadedChurnExposureCount: number;
  topLoadedARR: number;
  comparisonRmId: string;
  comparisonRmName: string;
  comparisonScore: number;
  managerId: string;
  managerName: string;
}

interface RmLoad {
  rmId: string;
  rmName: string;
  managerId: string;
  accountCount: number;
  churnExposureCount: number;
  totalARR: number;
  riskWeightedScore: number;
}

const isChurnState = (s: string) => s === "at-risk" || s === "churn-signal";

/**
 * Per-RM load metrics over the given account + RM sets (default = full canonical fixture).
 * totalARR is summed from the *passed* accounts (so a scoped account set yields scoped ARR);
 * unscoped this equals rmBookARR(rm.id) exactly. Spec 042 Step-4: filter-before-formula.
 */
export function computeRmLoads(
  accounts: ReadonlyArray<DemoAccount> = DEMO_ACCOUNTS,
  rms: ReadonlyArray<DemoRM> = DEMO_RMS,
): RmLoad[] {
  return rms.map((rm) => {
    const rmAccounts = accounts.filter((a) => a.rmId === rm.id);
    const churnExposureCount = rmAccounts.filter((a) => isChurnState(a.healthState)).length;
    const totalARR = rmAccounts.reduce((s, a) => s + accountARR(a.id), 0);
    return {
      rmId: rm.id,
      rmName: rm.name,
      managerId: rm.managerId,
      accountCount: rmAccounts.length,
      churnExposureCount,
      totalARR,
      riskWeightedScore: churnExposureCount + totalARR / 1_000_000,
    };
  });
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Detect a capacity imbalance. Returns one card when the top RM's risk-weighted score
 * exceeds 2× the org median; the comparison RM is the lowest-loaded teammate under the
 * same manager. Returns [] when no imbalance clears the threshold (overlay renders nothing).
 */
export function composeCapacityImbalance(
  accounts: ReadonlyArray<DemoAccount> = DEMO_ACCOUNTS,
  rms: ReadonlyArray<DemoRM> = DEMO_RMS,
  accountScope?: AccountScope,
): CapacityImbalanceCard[] {
  // Filter the working set BEFORE the formula (spec 042 Step-4 / watched concern #26).
  const scopedAccounts = accountScope
    ? accounts.filter((a) => accountScope.includes(a.id))
    : accounts;
  const scopedRmIds = new Set(scopedAccounts.map((a) => a.rmId));
  const scopedRms = rms.filter((r) => scopedRmIds.has(r.id));

  const loads = computeRmLoads(scopedAccounts, scopedRms);
  if (loads.length < 2) return [];

  const sorted = [...loads].sort((a, b) => b.riskWeightedScore - a.riskWeightedScore);
  const top = sorted[0];
  const med = median(loads.map((l) => l.riskWeightedScore));

  if (med <= 0 || top.riskWeightedScore <= 2 * med) return [];

  // Lowest-loaded teammate under the same manager (exclude the top RM).
  const teammates = loads
    .filter((l) => l.managerId === top.managerId && l.rmId !== top.rmId)
    .sort((a, b) => a.riskWeightedScore - b.riskWeightedScore);
  if (!teammates.length) return [];
  const comparison = teammates[0];

  const manager = DEMO_MANAGERS.find((m) => m.id === top.managerId);

  return [
    {
      id: "capacity-imbalance-001",
      topLoadedRmId: top.rmId,
      topLoadedRmName: top.rmName,
      topLoadedScore: top.riskWeightedScore,
      topLoadedAccountCount: top.accountCount,
      topLoadedChurnExposureCount: top.churnExposureCount,
      topLoadedARR: top.totalARR,
      comparisonRmId: comparison.rmId,
      comparisonRmName: comparison.rmName,
      comparisonScore: comparison.riskWeightedScore,
      managerId: top.managerId,
      managerName: manager?.name ?? top.managerId,
    },
  ];
}

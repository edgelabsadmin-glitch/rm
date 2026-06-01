/*
 * SPEC-042 Step-8 — team_workload_composer: per-RM workload metrics for the Executive View
 * Team workload panel + the Constellation RM-node hover extension (spec §3.3 / §6.5 / §6.6 / §6.7,
 * Edit 11). Pure function; every count DERIVED from the canonical fixtures (real-data principle —
 * no hardcoded counts). Scope-aware: a Manager view filters to the RMs whose accounts fall in the
 * manager's AccountScope; Executive / Admin (full-org scope) include every RM.
 *
 * Schema notes (Phase-1 verification):
 *  - DEMO_RMS is { id, name, managerId } — no displayName/avatarInitials. We surface rm.name and
 *    derive initials from it (first letter of each word → SS/SZ/YC/AA/MS/AT, matching DEMO_USERS).
 *  - DEMO_ACTIONS.status carries only 'pending' | 'approved' in the Phase-1A fixture, so
 *    modifiedThisWeek / rejectedThisWeek resolve to 0 until those statuses exist (Phase-1B signal
 *    data). The timestamp field is `proposed_at` (spec §6.5 says created_at; actual schema wins).
 *  - throughputIndicator is the Phase-1A heuristic (rising >1 / steady =1 / flat =0 approved this
 *    week); 'declining' is reserved for Phase-1B real-signal comparison (spec §6.5).
 */
import { DEMO_ACCOUNTS, DEMO_RMS } from "@/fixtures/demo_characters";
import { DEMO_ACTIONS } from "@/features/queue/demo_actions";
import type { AccountScope } from "@/lib/rbac/types";

export type ThroughputIndicator = "rising" | "steady" | "flat" | "declining";

export interface TeamWorkloadRow {
  rmId: string;
  rmName: string;
  avatarInitials: string;
  pendingCount: number;
  approvedThisWeek: number;
  modifiedThisWeek: number;
  rejectedThisWeek: number;
  throughputIndicator: ThroughputIndicator;
  combinedLoad: number; // sort key — pending + approvedThisWeek * 0.5
}

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

/** Initials from a display name: "Sajjal Shaheedi" → "SS". Falls back to the first two id chars. */
function initialsFromName(name: string, id: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return id.slice(0, 2).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Compose per-RM workload rows, scope-filtered and sorted by combinedLoad descending.
 *
 * @param rms          the RM roster (DEMO_RMS)
 * @param actions      the action cards (DEMO_ACTIONS)
 * @param accountScope optional RBAC scope; when given, only RMs owning an in-scope account appear.
 *                     Executive / Admin pass their full-org scope (all 14) → every RM. undefined =
 *                     unscoped (every RM), used by the Constellation tooltip lookup.
 * @param now          injectable clock for deterministic "this week" windows (default = now)
 */
export function composeTeamWorkload(
  rms: typeof DEMO_RMS = DEMO_RMS,
  actions: typeof DEMO_ACTIONS = DEMO_ACTIONS,
  accountScope?: AccountScope,
  now: Date = new Date(),
): TeamWorkloadRow[] {
  // Scope → the set of RM ids that own at least one in-scope account.
  const scopedAccounts = accountScope
    ? DEMO_ACCOUNTS.filter((a) => accountScope.includes(a.id))
    : DEMO_ACCOUNTS;
  const inScopeRmIds = new Set(scopedAccounts.map((a) => a.rmId));
  const scopedRms = accountScope ? rms.filter((rm) => inScopeRmIds.has(rm.id)) : rms;

  const sevenDaysAgo = now.getTime() - SEVEN_DAYS_MS;
  const withinWeek = (iso: string) => new Date(iso).getTime() >= sevenDaysAgo;

  return scopedRms
    .map((rm) => {
      const rmCards = actions.filter((c) => c.rm_id === rm.id);
      const pendingCount = rmCards.filter((c) => c.status === "pending").length;
      const approvedThisWeek = rmCards.filter(
        (c) => c.status === "approved" && withinWeek(c.proposed_at),
      ).length;
      // ApprovalStatus models 'modified-approved' (not 'modified') + 'rejected'; neither appears
      // in the Phase-1A fixture (only pending/approved), so both resolve to 0 until Phase-1B.
      const modifiedThisWeek = rmCards.filter(
        (c) => c.status === "modified-approved" && withinWeek(c.proposed_at),
      ).length;
      const rejectedThisWeek = rmCards.filter(
        (c) => c.status === "rejected" && withinWeek(c.proposed_at),
      ).length;

      let throughputIndicator: ThroughputIndicator;
      if (approvedThisWeek === 0) throughputIndicator = "flat";
      else if (approvedThisWeek === 1) throughputIndicator = "steady";
      else throughputIndicator = "rising";

      return {
        rmId: rm.id,
        rmName: rm.name,
        avatarInitials: initialsFromName(rm.name, rm.id),
        pendingCount,
        approvedThisWeek,
        modifiedThisWeek,
        rejectedThisWeek,
        throughputIndicator,
        combinedLoad: pendingCount + approvedThisWeek * 0.5,
      };
    })
    .sort((a, b) => b.combinedLoad - a.combinedLoad);
}

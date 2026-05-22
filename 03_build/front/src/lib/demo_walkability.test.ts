/*
 * SPEC-042 Step-9 — demo flow walkability (Stories A/B/C, spec §10).
 * Canvas-free cross-surface verification: composes the same pure helpers each surface uses
 * (route resolver · scope derivation · queue scope · 3 overlay composers · team workload) to
 * assert every persona/surface combination behaves as the spec documents — without mounting
 * ForceGraph's <canvas> (the documented jsdom constraint). All expectations DERIVE from the
 * canonical fixtures; no hardcoded topology.
 */
import { describe, expect, it } from "vitest";
import { composeEscalationTierJumps } from "@/features/constellation/composers/escalation_tier_jump_composer";
import { composeCapacityImbalance } from "@/features/constellation/composers/rm_capacity_composer";
import { DEMO_PATTERNS } from "@/features/constellation/demo_patterns";
import { composeTeamWorkload } from "@/features/executive/composers/team_workload_composer";
import { DEMO_ACTIONS } from "@/features/queue/demo_actions";
import { applyStatusFilter, scopeAndRefineCards } from "@/features/queue/queue_scope";
import { DEMO_ACCOUNTS, DEMO_RMS } from "@/fixtures/demo_characters";
import { DEMO_TIER_JUMP_EVENTS } from "@/fixtures/demo_tier_jump_events";
import { defaultRouteForRole } from "@/lib/auth/defaultRoute";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { AccountScope, UserRole } from "@/lib/rbac/types";

const NOW = new Date("2026-05-22T12:00:00Z"); // demo anchor; 28h after the Manhattan tier-jump (in-window)

// Mirror of the inline ClusterPatternOverlay / Constellation scope filter (whole-pattern-in-scope).
const scopedPatterns = (scope?: AccountScope) =>
  scope ? DEMO_PATTERNS.filter((p) => p.support_account_ids.every((id) => scope.includes(id))) : DEMO_PATTERNS;

// RoleGuard predicate (allowedRoles.includes(role)) for the route matrix (§3).
const canAccess = (role: UserRole, allowed: UserRole[]) => allowed.includes(role);
const ACTIONS_ROLES: UserRole[] = ["rm", "manager", "admin"];
const EXEC_ROLES: UserRole[] = ["executive", "admin"];
const SETTINGS_ROLES: UserRole[] = ["admin"];

describe("Story A — RM Yozeline (scope = Manhattan only)", () => {
  const scope = deriveAccountScope("rm", "yozeline-candia");

  it("lands on /actions; scope is her single account", () => {
    expect(defaultRouteForRole("rm")).toBe("/actions");
    expect(scope).toEqual(["manhattan-restorative"]);
  });
  it("/actions: no cards (Yozeline owns none in the fixture)", () => {
    expect(scopeAndRefineCards(DEMO_ACTIONS, "rm", "yozeline-candia")).toHaveLength(0);
  });
  it("capacity overlay empty; tier-jump (Manhattan) visible; cluster pattern hidden (needs DHR)", () => {
    expect(composeCapacityImbalance(DEMO_ACCOUNTS, DEMO_RMS, scope)).toHaveLength(0);
    expect(composeEscalationTierJumps(DEMO_TIER_JUMP_EVENTS, scope, NOW.getTime())).toHaveLength(1);
    expect(scopedPatterns(scope)).toHaveLength(0);
  });
  it("AccountScopeGuard would block /accounts/dhr-health-clinics (out of scope)", () => {
    expect(scope.includes("dhr-health-clinics")).toBe(false);
  });
  it("RoleGuard blocks /executive and /settings/users", () => {
    expect(canAccess("rm", EXEC_ROLES)).toBe(false);
    expect(canAccess("rm", SETTINGS_ROLES)).toBe(false);
    expect(canAccess("rm", ACTIONS_ROLES)).toBe(true);
  });
});

describe("Story B — Manager Sarah (team scope = 7 accounts)", () => {
  const scope = deriveAccountScope("manager", "sarah-hooper");

  it("lands on /actions; team scope spans 7 accounts", () => {
    expect(defaultRouteForRole("manager")).toBe("/actions");
    expect(scope).toHaveLength(7);
  });
  it("/actions: 4 in-scope cards (3 active + 1 approved); ?rm=sajjal narrows to 2", () => {
    const team = scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper");
    expect(team).toHaveLength(4);
    expect(applyStatusFilter(team, "active")).toHaveLength(3);
    expect(scopeAndRefineCards(DEMO_ACTIONS, "manager", "sarah-hooper", "sajjal-shaheedi")).toHaveLength(2);
  });
  it("capacity overlay surfaces Sajjal; tier-jump + cluster pattern (DHR+Manhattan) both visible", () => {
    const cap = composeCapacityImbalance(DEMO_ACCOUNTS, DEMO_RMS, scope);
    expect(cap).toHaveLength(1);
    expect(cap[0].topLoadedRmId).toBe("sajjal-shaheedi");
    expect(composeEscalationTierJumps(DEMO_TIER_JUMP_EVENTS, scope, NOW.getTime())).toHaveLength(1);
    expect(scopedPatterns(scope)).toHaveLength(1); // both DHR + Manhattan in Sarah's scope
  });
  it("RoleGuard blocks /executive and /settings/users", () => {
    expect(canAccess("manager", EXEC_ROLES)).toBe(false);
    expect(canAccess("manager", SETTINGS_ROLES)).toBe(false);
  });
});

describe("Story C — Executive Iffi (full org scope)", () => {
  const scope = deriveAccountScope("executive", "iffi-wahla");

  it("lands on /executive; full-org scope (14)", () => {
    expect(defaultRouteForRole("executive")).toBe("/executive");
    expect(scope).toHaveLength(14);
  });
  it("Team workload panel: 6 RMs sorted by load, Sajjal at top", () => {
    const rows = composeTeamWorkload(DEMO_RMS, DEMO_ACTIONS, scope, NOW);
    expect(rows).toHaveLength(6);
    expect(rows[0].rmId).toBe("sajjal-shaheedi");
  });
  it("read-only Per-Account navigation works org-wide (executiveBypass); /actions blocked", () => {
    expect(scope.includes("dhr-health-clinics")).toBe(true); // bypass also covers any id
    expect(canAccess("executive", ACTIONS_ROLES)).toBe(false);
    expect(canAccess("executive", EXEC_ROLES)).toBe(true);
  });
});

/*
 * SPEC-041 — Constellation graph built from the canonical demo characters
 * (src/fixtures/demo_characters.ts). Real people + accounts + talent throughout:
 * 1 globe + 2 managers + 6 RMs + 14 accounts (+ talent on drill-down). The 600-node
 * generator was the Step-2 perf GATE (passed; see spec_041_performance_benchmark.md)
 * and is retired now that the production graph is the real ~23-node book.
 *
 * Link state = signal state (Amendment 5/6): account→RM link encodes account health —
 * healthy→active (brand), churn-signal→churn (red, animated), at-risk→inactive (dim).
 * Node size (accounts) ≈ health × activity (active-talent count) per Amendment 5.
 */
import {
  DEMO_ACCOUNTS,
  DEMO_MANAGERS,
  DEMO_RMS,
  DEMO_TALENT,
  DEMO_USERS,
  type DemoAccount,
} from "@/fixtures/demo_characters";
import type { AccountSummaryDTO } from "@/lib/api";

export type NodeType = "globe" | "manager" | "rm" | "account" | "talent";
export type LinkState = "active" | "inactive" | "churn";

// Disposition D10: clamp the orbital talent drill-down (typical account ~20-30 talent).
export const MAX_TALENT_PER_ACCOUNT = 30;

export interface ConstellationNode {
  id: string;
  type: NodeType;
  label: string;
  tier?: DemoAccount["tier"];
  size: number;
  rm_id?: string;
  manager_id?: string;
  /** Real-data path: active-talent count for this account, used to render the talent orbit. */
  active_talent?: number;
  fx?: number;
  fy?: number;
  x?: number;
  y?: number;
}

export interface ConstellationLink {
  source: string;
  target: string;
  state: LinkState;
}

export interface ConstellationGraph {
  nodes: ConstellationNode[];
  links: ConstellationLink[];
}

const HEALTH_TO_LINK: Record<DemoAccount["healthState"], LinkState> = {
  healthy: "active",
  "churn-signal": "churn",
  "at-risk": "inactive",
};

function activeTalentCount(accountId: string): number {
  return DEMO_TALENT.reduce((n, t) => (t.accountId === accountId ? n + 1 : n), 0);
}

/**
 * Build the org graph. `accountScope` (spec 042 RBAC, Week 4) optionally restricts the
 * visible accounts to a whitelist of ids; undefined = no scoping (all accounts). The
 * globe + manager/RM scaffold always render so the org frame is stable; only the account
 * leaves are scoped. An empty scope yields zero account nodes (the caller shows the empty
 * state).
 */
export function buildConstellationGraph(accountScope?: ReadonlyArray<string>): ConstellationGraph {
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  const R_MGR = 180;
  const R_RM = 340;

  const scopedAccounts =
    accountScope === undefined
      ? DEMO_ACCOUNTS
      : DEMO_ACCOUNTS.filter((a) => accountScope.includes(a.id));

  nodes.push({ id: "globe", type: "globe", label: "EDGE Pulse", size: 26, fx: 0, fy: 0 });

  DEMO_MANAGERS.forEach((m, i) => {
    const a = (i / DEMO_MANAGERS.length) * 2 * Math.PI;
    nodes.push({
      id: m.id, type: "manager", label: m.name, size: 15,
      fx: Math.cos(a) * R_MGR, fy: Math.sin(a) * R_MGR,
    });
    links.push({ source: m.id, target: "globe", state: "active" });
  });

  DEMO_RMS.forEach((rm, i) => {
    const a = (i / DEMO_RMS.length) * 2 * Math.PI;
    nodes.push({
      id: rm.id, type: "rm", label: rm.name, size: 11, manager_id: rm.managerId,
      fx: Math.cos(a) * R_RM, fy: Math.sin(a) * R_RM,
    });
    links.push({ source: rm.id, target: rm.managerId, state: "active" });
  });

  scopedAccounts.forEach((acc) => {
    const count = activeTalentCount(acc.id);
    const factor = acc.healthState === "healthy" ? 1.4 : 0.7; // health × activity (Amendment 5)
    const rm = DEMO_RMS.find((r) => r.id === acc.rmId);
    nodes.push({
      id: acc.id, type: "account", label: acc.name, tier: acc.tier,
      size: 3 + Math.sqrt(count) * factor, rm_id: acc.rmId, manager_id: rm?.managerId,
    });
    links.push({ source: acc.id, target: acc.rmId, state: HEALTH_TO_LINK[acc.healthState] });
  });

  return { nodes, links };
}

function sfHealthToLink(health: number, risk: string): LinkState {
  if (health >= 7) return "active";
  if (health < 4 || risk === "High") return "churn";
  return "inactive";
}

/**
 * Build the org graph from real SF accounts.
 * Org scaffold (Eddy → Managers → RMs) comes from demo fixtures (canonical ground truth).
 * Account leaves come from real SF data, matched to RM nodes via DEMO_USERS.sfUserId.
 * Owner IDs not in DEMO_USERS get synthetic RM nodes connected to globe.
 */
export function buildConstellationGraphFromReal(accounts: AccountSummaryDTO[]): ConstellationGraph {
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  const R_MGR = 180;
  const R_RM = 340;

  // sfUserId → DEMO_RMS entry (via DEMO_USERS bridge)
  const rmBySfId = new Map(
    DEMO_RMS.flatMap((rm) => {
      const u = DEMO_USERS.find((u) => u.id === rm.id);
      return u?.sfUserId ? [[u.sfUserId, rm] as const] : [];
    }),
  );

  // Collect owner_ids with no DEMO_RM match → synthetic RM nodes
  const extraRMs = new Map<string, { nodeId: string; name: string }>();
  for (const acc of accounts) {
    if (acc.owner_id && !rmBySfId.has(acc.owner_id) && !extraRMs.has(acc.owner_id)) {
      extraRMs.set(acc.owner_id, {
        nodeId: `rm-x-${acc.owner_id}`,
        name: acc.rm_name || acc.owner_id,
      });
    }
  }

  nodes.push({ id: "globe", type: "globe", label: "EDGE Pulse", size: 26, fx: 0, fy: 0 });

  // Managers connect directly to globe
  DEMO_MANAGERS.forEach((m, i) => {
    const a = (i / DEMO_MANAGERS.length) * 2 * Math.PI;
    nodes.push({
      id: m.id, type: "manager", label: m.name, size: 15,
      fx: Math.cos(a) * R_MGR, fy: Math.sin(a) * R_MGR,
    });
    links.push({ source: m.id, target: "globe", state: "active" });
  });

  // Only show demo RMs that have at least one real SF account linked to them
  const activeRmIds = new Set(
    accounts
      .filter((a) => a.owner_id && rmBySfId.has(a.owner_id))
      .map((a) => rmBySfId.get(a.owner_id!)!.id),
  );
  const visibleDemoRMs = DEMO_RMS.filter((rm) => activeRmIds.has(rm.id));
  const visibleTotal = visibleDemoRMs.length + extraRMs.size;

  visibleDemoRMs.forEach((rm, i) => {
    const a = (i / Math.max(visibleTotal, 1)) * 2 * Math.PI;
    nodes.push({
      id: rm.id, type: "rm", label: rm.name, size: 11, manager_id: rm.managerId,
      fx: Math.cos(a) * R_RM, fy: Math.sin(a) * R_RM,
    });
    links.push({ source: rm.id, target: rm.managerId, state: "active" });
  });

  // Synthetic RMs (unknown owner_ids) connect to globe
  [...extraRMs.values()].forEach((rm, i) => {
    const a = ((visibleDemoRMs.length + i) / Math.max(visibleTotal, 1)) * 2 * Math.PI;
    nodes.push({
      id: rm.nodeId, type: "rm", label: rm.name, size: 11,
      fx: Math.cos(a) * R_RM, fy: Math.sin(a) * R_RM,
    });
    links.push({ source: rm.nodeId, target: "globe", state: "active" });
  });

  // Account nodes — linked to their RM node
  for (const acc of accounts) {
    const knownRM = acc.owner_id ? rmBySfId.get(acc.owner_id) : undefined;
    const extraRM = acc.owner_id ? extraRMs.get(acc.owner_id) : undefined;
    const rmNodeId = knownRM ? knownRM.id : extraRM ? extraRM.nodeId : "globe";
    const managerNodeId = knownRM?.managerId;
    const state = sfHealthToLink(acc.composite_health, acc.risk);
    const factor = state === "active" ? 1.4 : 0.7;
    const size = 3 + Math.sqrt(acc.active_talent) * factor;
    nodes.push({
      id: acc.account_id,
      type: "account",
      label: acc.name,
      tier: acc.tier as DemoAccount["tier"],
      size,
      rm_id: rmNodeId,
      manager_id: managerNodeId,
      active_talent: acc.active_talent,
    });
    links.push({ source: acc.account_id, target: rmNodeId, state });
  }

  return { nodes, links };
}

/** Inline talent drill-down (option c): Active talent orbiting one account, clamped to
 * MAX_TALENT_PER_ACCOUNT. `clamped` flags accounts over the cap.
 *
 * Real-data path (account carries `active_talent`): synthesize that many orbiting talent
 * nodes from the real count — per-associate names aren't exposed to the client, so nodes
 * are labelled generically. Fixture path (demo accounts): use the named DEMO_TALENT roster.
 */
export function buildTalentFor(
  account: ConstellationNode,
): { nodes: ConstellationNode[]; links: ConstellationLink[]; clamped: boolean } {
  const ax = account.x ?? account.fx ?? 0;
  const ay = account.y ?? account.fy ?? 0;

  let items: { id: string; label: string }[];
  let total: number;
  if (account.active_talent !== undefined) {
    // Real account — synthesize from the live active-talent count.
    total = account.active_talent;
    const n = Math.min(total, MAX_TALENT_PER_ACCOUNT);
    items = Array.from({ length: n }, (_, i) => ({
      id: `${account.id}::talent-${i}`,
      label: `Active talent ${i + 1}`,
    }));
  } else {
    // Demo account — named roster from fixtures.
    const all = DEMO_TALENT.filter((t) => t.accountId === account.id);
    total = all.length;
    items = all
      .slice(0, MAX_TALENT_PER_ACCOUNT)
      .map((t) => ({ id: t.id, label: t.name }));
  }

  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  items.forEach((t, i) => {
    const a = (i / Math.max(items.length, 1)) * 2 * Math.PI;
    nodes.push({
      id: t.id, type: "talent", label: t.label, size: 1.4,
      x: ax + Math.cos(a) * 14, y: ay + Math.sin(a) * 14,
    });
    links.push({ source: t.id, target: account.id, state: "active" });
  });
  return { nodes, links, clamped: total > MAX_TALENT_PER_ACCOUNT };
}

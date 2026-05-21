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
  type DemoAccount,
} from "@/fixtures/demo_characters";

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

export function buildConstellationGraph(): ConstellationGraph {
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  const R_MGR = 160;
  const R_RM = 340;

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

  DEMO_ACCOUNTS.forEach((acc) => {
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

/** Inline talent drill-down (option c): real Active talent (deduped) orbiting one
 * account, clamped to MAX_TALENT_PER_ACCOUNT. `clamped` flags accounts over the cap. */
export function buildTalentFor(
  account: ConstellationNode,
): { nodes: ConstellationNode[]; links: ConstellationLink[]; clamped: boolean } {
  const all = DEMO_TALENT.filter((t) => t.accountId === account.id);
  const show = all.slice(0, MAX_TALENT_PER_ACCOUNT);
  const ax = account.x ?? account.fx ?? 0;
  const ay = account.y ?? account.fy ?? 0;
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  show.forEach((t, i) => {
    const a = (i / show.length) * 2 * Math.PI;
    nodes.push({
      id: t.id, type: "talent", label: t.name, size: 1.4,
      x: ax + Math.cos(a) * 14, y: ay + Math.sin(a) * 14,
    });
    links.push({ source: t.id, target: account.id, state: "active" });
  });
  return { nodes, links, clamped: all.length > MAX_TALENT_PER_ACCOUNT };
}

/*
 * SPEC-041 Step-2 — 610-node benchmark fixture (the GATE). Realistic density:
 * 1 center globe + 3 managers + 8 RMs + 600 accounts (200 SMB / 280 Mid / 120
 * Enterprise), varied health + link states. Links: account→RM, RM→manager,
 * manager→globe. Deterministic (seeded) so benchmark runs are comparable.
 */
export type NodeType = "globe" | "manager" | "rm" | "account" | "talent";
export type LinkState = "active" | "inactive" | "churn";
export type Tier = "SMB" | "Mid-Market" | "Enterprise";

// Phase-1 cap (audit Dim 10): a typical EDGE account has ~20-30 placed talent.
export const MAX_TALENT_PER_ACCOUNT = 30;

export interface ConstellationNode {
  id: string;
  type: NodeType;
  label: string;
  tier?: Tier;
  health?: number; // 0..10
  size: number;
  rm_id?: string;
  manager_id?: string;
  activity?: number; // 0..1 recent signal volume
  fx?: number; // pinned x (globe/managers/RMs form the orbital rings)
  fy?: number; // pinned y
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

// Tiny deterministic PRNG (mulberry32) so the fixture is stable run-to-run.
function rng(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const TIER_PLAN: { tier: Tier; count: number }[] = [
  { tier: "SMB", count: 200 },
  { tier: "Mid-Market", count: 280 },
  { tier: "Enterprise", count: 120 },
];
const LINK_STATES: LinkState[] = ["active", "active", "inactive", "churn"]; // ~50/25/25

export function buildBenchmarkGraph(
  managers = 3,
  rmsPerBook = 8,
  accountsTotal = 600,
): ConstellationGraph {
  const r = rng(0x5eed);
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];

  // Globe pinned at center; managers on an inner ring; RMs on a mid ring (the
  // orbital hierarchy — accounts free-float on the outside via charge/link forces).
  const R_MGR = 160;
  const R_RM = 340;
  nodes.push({ id: "globe", type: "globe", label: "EDGE Pulse", size: 26, fx: 0, fy: 0 });

  const managerIds: string[] = [];
  for (let m = 0; m < managers; m++) {
    const id = `mgr-${m}`;
    const a = (m / managers) * 2 * Math.PI;
    managerIds.push(id);
    nodes.push({
      id, type: "manager", label: `Manager ${m + 1}`, size: 15,
      fx: Math.cos(a) * R_MGR, fy: Math.sin(a) * R_MGR,
    });
    links.push({ source: id, target: "globe", state: "active" });
  }

  const rmIds: string[] = [];
  for (let i = 0; i < rmsPerBook; i++) {
    const id = `rm-${i}`;
    const manager_id = managerIds[i % managers];
    const a = (i / rmsPerBook) * 2 * Math.PI;
    rmIds.push(id);
    nodes.push({
      id, type: "rm", label: `RM ${i + 1}`, size: 11, manager_id,
      fx: Math.cos(a) * R_RM, fy: Math.sin(a) * R_RM,
    });
    links.push({ source: id, target: manager_id, state: "active" });
  }

  // Expand the tier plan into one entry per account, then distribute round-robin.
  const tiers: Tier[] = [];
  for (const { tier, count } of TIER_PLAN) for (let k = 0; k < count; k++) tiers.push(tier);
  const total = Math.min(accountsTotal, tiers.length);

  for (let a = 0; a < total; a++) {
    const id = `acct-${a}`;
    const rm_id = rmIds[a % rmIds.length];
    const manager_id = nodes.find((n) => n.id === rm_id)?.manager_id;
    const state = LINK_STATES[Math.floor(r() * LINK_STATES.length)];
    // Activity loosely tracks link state (active→high, churn→low) for coherence.
    const activity = state === "active" ? 0.6 + r() * 0.4 : state === "inactive" ? 0.2 + r() * 0.3 : r() * 0.2;
    const health = Math.round(r() * 100) / 10; // 0..10
    // Amendment 5: node size = composite-health × activity (single dimension).
    const size = 2 + (health / 10) * activity * 9;
    nodes.push({
      id, type: "account", label: `Account ${a + 1}`, tier: tiers[a],
      health, activity, size, rm_id, manager_id,
    });
    links.push({ source: id, target: rm_id, state });
  }

  return { nodes, links };
}

/** Inline talent drill-down (option c): small talent nodes orbiting one account.
 * Capped at MAX_TALENT_PER_ACCOUNT; `clamped` flags when the cap was hit. */
export function buildTalentFor(
  account: ConstellationNode,
  requested = 18,
): { nodes: ConstellationNode[]; links: ConstellationLink[]; clamped: boolean } {
  const n = Math.min(requested, MAX_TALENT_PER_ACCOUNT);
  const ax = (account as { x?: number }).x ?? account.fx ?? 0;
  const ay = (account as { y?: number }).y ?? account.fy ?? 0;
  const nodes: ConstellationNode[] = [];
  const links: ConstellationLink[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * 2 * Math.PI;
    nodes.push({
      id: `tal-${account.id}-${i}`,
      type: "talent",
      label: `Talent ${i + 1}`,
      size: 1.4,
      x: ax + Math.cos(a) * 14, // seed on a small ring → settles into orbit fast
      y: ay + Math.sin(a) * 14,
    } as ConstellationNode);
    links.push({ source: `tal-${account.id}-${i}`, target: account.id, state: "active" });
  }
  return { nodes, links, clamped: requested > MAX_TALENT_PER_ACCOUNT };
}

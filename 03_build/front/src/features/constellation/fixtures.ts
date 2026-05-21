/*
 * SPEC-041 Step-2 — 610-node benchmark fixture (the GATE). Realistic density:
 * 1 center globe + 3 managers + 8 RMs + 600 accounts (200 SMB / 280 Mid / 120
 * Enterprise), varied health + link states. Links: account→RM, RM→manager,
 * manager→globe. Deterministic (seeded) so benchmark runs are comparable.
 */
export type NodeType = "globe" | "manager" | "rm" | "account";
export type LinkState = "active" | "inactive" | "churn";
export type Tier = "SMB" | "Mid-Market" | "Enterprise";

export interface ConstellationNode {
  id: string;
  type: NodeType;
  label: string;
  tier?: Tier;
  health?: number; // 0..10
  size: number;
  rm_id?: string;
  manager_id?: string;
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

  nodes.push({ id: "globe", type: "globe", label: "EDGE Pulse", size: 24 });

  const managerIds: string[] = [];
  for (let m = 0; m < managers; m++) {
    const id = `mgr-${m}`;
    managerIds.push(id);
    nodes.push({ id, type: "manager", label: `Manager ${m + 1}`, size: 14 });
    links.push({ source: id, target: "globe", state: "active" });
  }

  const rmIds: string[] = [];
  for (let i = 0; i < rmsPerBook; i++) {
    const id = `rm-${i}`;
    const manager_id = managerIds[i % managers];
    rmIds.push(id);
    nodes.push({ id, type: "rm", label: `RM ${i + 1}`, size: 10, manager_id });
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
    const health = Math.round(r() * 100) / 10; // 0..10
    nodes.push({
      id,
      type: "account",
      label: `Account ${a + 1}`,
      tier: tiers[a],
      health,
      size: 3 + Math.round(r() * 5),
      rm_id,
      manager_id,
    });
    links.push({ source: id, target: rm_id, state: LINK_STATES[Math.floor(r() * LINK_STATES.length)] });
  }

  return { nodes, links };
}

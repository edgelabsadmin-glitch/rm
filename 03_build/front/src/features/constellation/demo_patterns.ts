/*
 * SPEC-041 Step-5 / SPEC-027 (Skill 10) — cluster-pattern fixture. The cluster-pattern
 * alert overlay consumes the extended Skill-10 `pattern_card` payload (support_account_ids
 * + owning_rm_id + severity). pulse-api isn't deployed, so Phase-1 reads this fixture; the
 * live Skill-10 + Skill-01 pattern stream wires at the Week-4 cutover.
 *
 * Real-data integrity (Session 19 §7 rules 25-26): the demo pattern uses GENERALIZED
 * language ("engagement-signal patterns"), never specific Chorus quotes ("vendor-
 * consolidation talk") — those require live extraction. Account/RM ids are real
 * (demo_characters.ts); the qualitative pattern is the placeholder until Skill 10 emits
 * a grounded one.
 */
export type PatternSeverity = "high" | "medium" | "low";

/** Mirrors the spec-027 Skill-10 pattern_card payload (front-end view shape). */
export interface PatternCard {
  id: string;
  title: string;
  summary: string;
  support_account_ids: string[];
  owning_rm_id: string;
  severity: PatternSeverity;
}

export const DEMO_PATTERNS: PatternCard[] = [
  {
    id: "pattern-demo-001",
    title: "Healthcare cluster — engagement signal",
    summary:
      "Multiple healthcare accounts in Sidra Zia's book showing similar engagement-signal patterns this month",
    support_account_ids: ["dhr-health-clinics", "manhattan-restorative"],
    owning_rm_id: "sidra-zia",
    severity: "high",
  },
];

/**
 * Centroid (graph coords) of the support accounts present in the rendered graph.
 * Returns null if none are positioned yet (node x/y are mutated in place by the sim).
 * Pure + node-shape-agnostic so it's unit-testable without a live ForceGraph.
 */
export function clusterCentroid(
  accountIds: string[],
  nodes: ReadonlyArray<{ id: string; x?: number; y?: number }>,
): { x: number; y: number } | null {
  const pts = accountIds
    .map((id) => nodes.find((n) => n.id === id))
    .filter((n): n is { id: string; x: number; y: number } => !!n && n.x != null && n.y != null);
  if (!pts.length) return null;
  const x = pts.reduce((s, n) => s + n.x, 0) / pts.length;
  const y = pts.reduce((s, n) => s + n.y, 0) / pts.length;
  return { x, y };
}

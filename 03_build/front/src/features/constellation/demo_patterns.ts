/*
 * SPEC-041 Step-5 / SPEC-027 (Skill 10) — cluster-pattern fixture. The cluster-pattern
 * alert overlay consumes the extended Skill-10 `pattern_card` payload (support_account_ids
 * + owning_rm_ids). pulse-api isn't deployed, so Phase-1 reads this fixture; the live
 * Skill-10 + Skill-01 pattern stream wires at the Week-4 cutover.
 *
 * Real-data integrity (Session 19): the demo pattern uses GENERALIZED language ("reduced
 * engagement signals"), never specific Chorus quotes — those require live extraction.
 * Account ids + RM ids are real (demo_characters.ts); the qualitative pattern is the
 * placeholder until Skill 10 emits a grounded one.
 */
export type PatternSeverity = "high" | "medium" | "low";

export interface DemoPattern {
  id: string;
  title: string;
  summary: string;
  support_account_ids: string[];
  owning_rm_ids: string[];
  severity: PatternSeverity;
}

export const DEMO_PATTERNS: DemoPattern[] = [
  {
    id: "pattern-001",
    title: "Healthcare cluster engagement drop",
    summary: "Multiple healthcare accounts showing reduced engagement signals this month",
    support_account_ids: ["dhr-health-clinics", "manhattan-restorative", "denver-wellness"],
    owning_rm_ids: ["sidra-zia", "yozeline-candia"],
    severity: "high",
  },
];

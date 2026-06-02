/*
 * SPEC-042 Step-1 — RBAC core types. Phase 1A introduces four roles + an account scope
 * primitive. Scope is always DERIVED from canonical demo_characters.ts (no hardcoded
 * counts); see deriveAccountScope in ./accountScope.ts.
 */
import type { DemoAccountId } from "@/fixtures/demo_characters";

export type UserRole = "rm" | "manager" | "executive" | "admin";

export type AccountScope = DemoAccountId[];
// Semantics:
// - undefined  = unscoped (legacy / pre-RBAC code paths; treat as no filter)
// - []         = no access (empty scope; empty state)
// - [...ids]   = filtered to these account IDs

export const ALL_ROLES: UserRole[] = ["rm", "manager", "executive", "admin"];

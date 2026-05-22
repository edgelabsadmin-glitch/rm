/*
 * SPEC-042 Step-1 — deriveAccountScope: the single source of account-visibility scope
 * per role. Pure function; every scope value is derived from canonical demo_characters.ts
 * (real-data principle §7 rule 27 — no hardcoded counts). RM → own book; Manager → team
 * book; Executive/Admin → full org.
 */
import { DEMO_ACCOUNTS, DEMO_RMS } from "@/fixtures/demo_characters";
import type { AccountScope, UserRole } from "./types";

/**
 * Derives the AccountScope for a given role + user identity.
 *
 * @param role - The user's role (RM / Manager / Executive / Admin)
 * @param userId - The user's id; for RM, matches account.rmId; for Manager, matches
 *   rm.managerId; for Executive/Admin, ignored (full org scope)
 * @returns Array of in-scope DemoAccountId values (empty when nothing matches)
 */
export function deriveAccountScope(role: UserRole, userId: string): AccountScope {
  switch (role) {
    case "rm":
      // RM sees their own book — accounts where account.rmId === userId
      return DEMO_ACCOUNTS.filter((a) => a.rmId === userId).map((a) => a.id);

    case "manager": {
      // Manager sees accounts owned by RMs they manage
      const teamRmIds = DEMO_RMS.filter((rm) => rm.managerId === userId).map((rm) => rm.id);
      return DEMO_ACCOUNTS.filter((a) => teamRmIds.includes(a.rmId)).map((a) => a.id);
    }

    case "executive":
    case "admin":
      // Full org scope
      return DEMO_ACCOUNTS.map((a) => a.id);

    default: {
      // Exhaustive check; throws if a new role is added without scope logic.
      const _exhaustive: never = role;
      throw new Error(`Unknown role: ${_exhaustive}`);
    }
  }
}

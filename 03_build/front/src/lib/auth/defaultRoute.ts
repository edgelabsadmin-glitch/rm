/*
 * SPEC-042 Step-3 — default landing route per role (permission matrix §3). Executives land
 * on the surface designed for them (/executive); everyone else on the action queue. Also
 * used as RoleGuard's role-aware fallback so a blocked user never redirects into a loop.
 */
import type { UserRole } from "@/lib/rbac/types";

export function defaultRouteForRole(role: UserRole): string {
  switch (role) {
    case "rm":
    case "manager":
    case "admin":
      return "/actions";
    case "executive":
      return "/executive";
    default: {
      const _exhaustive: never = role;
      throw new Error(`Unknown role: ${_exhaustive}`);
    }
  }
}

/*
 * SPEC-042 Step-2 — RoleGuard + AccountScopeGuard. Front-end route protection (visibility;
 * server-side `Caller` enforcement in api/actions.py is the security boundary). RoleGuard
 * gates a route by role; AccountScopeGuard gates `/accounts/:id` by the caller's scope, with
 * an Executive/Admin read-only bypass. Wired into the route tree in Step 3.
 */
import { type ReactNode } from "react";
import { Navigate, useParams } from "react-router-dom";
import type { DemoAccountId } from "@/fixtures/demo_characters";
import type { UserRole } from "@/lib/rbac/types";
import { useAuth } from "./AuthContext";
import { defaultRouteForRole } from "./defaultRoute";

interface RoleGuardProps {
  allowedRoles: UserRole[];
  // Optional explicit redirect target. Omitted → the caller's role-default route. Computing
  // the fallback from the role avoids an infinite loop for a role blocked from /actions
  // (e.g. Executive), which a static "/actions" default would cause (Step-3 HALT #1).
  fallbackRoute?: string;
  children: ReactNode;
}

export function RoleGuard({ allowedRoles, fallbackRoute, children }: RoleGuardProps) {
  const { user } = useAuth();
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={fallbackRoute ?? defaultRouteForRole(user.role)} replace />;
  }
  return <>{children}</>;
}

interface AccountScopeGuardProps {
  // When true, Executive + Admin roles bypass the scope check (read-only navigation).
  executiveBypass?: boolean;
  children: ReactNode;
}

export function AccountScopeGuard({ executiveBypass = false, children }: AccountScopeGuardProps) {
  const { user, accountScope } = useAuth();
  const { id } = useParams();

  // Executive + Admin bypass when the flag is set (read-only navigation to any account).
  if (executiveBypass && (user.role === "executive" || user.role === "admin")) {
    return <>{children}</>;
  }

  // Out-of-scope account id → redirect to the default route.
  if (id && !accountScope.includes(id as DemoAccountId)) {
    return <Navigate to="/actions" replace />;
  }

  return <>{children}</>;
}

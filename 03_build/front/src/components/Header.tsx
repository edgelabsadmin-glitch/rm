/*
 * SPEC-034 — App header (chrome). Brand mark (purple Zap tile, §6 tinted-shadow
 * moment #2), primary nav, Queue button with live badge, and the user avatar from
 * the stubbed session. Admin nav is hidden unless the session role is admin
 * (visibility only — server-side scope is authoritative).
 */
import { Bell, Zap } from "lucide-react";
import { NavLink } from "react-router-dom";
import { usePulseState } from "@/components/PulseStateProvider";
import { useAuth } from "@/lib/auth/AuthContext";
import type { UserRole } from "@/lib/rbac/types";
import { cn } from "@/lib/utils";

// SPEC-042 Step 3: nav links are role-gated (visibility layer; RoleGuard enforces direct
// URL access). Executive View is exec/admin only; Settings is admin only.
const NAV: { to: string; label: string; roles: UserRole[] }[] = [
  { to: "/accounts", label: "Accounts", roles: ["rm", "manager", "executive", "admin"] },
  { to: "/constellation", label: "Constellation", roles: ["rm", "manager", "executive", "admin"] },
  { to: "/executive", label: "Executive View", roles: ["executive", "admin"] },
  { to: "/submit", label: "Submit", roles: ["rm", "manager", "executive", "admin"] },
  { to: "/settings/users", label: "Settings", roles: ["admin"] },
];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Header() {
  const { user } = useAuth();
  const { queueCount } = usePulseState();

  return (
    <header className="flex items-center justify-between border-b border-line-subtle px-7 py-5">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <div className="text-lg font-semibold tracking-tight text-ink-primary">Pulse</div>
            <div className="text-xs text-ink-secondary">Relationship intelligence for RMs</div>
          </div>
        </div>

        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.filter((item) => item.roles.includes(user.role)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3 py-1.5 text-sm font-medium transition",
                  isActive
                    ? "bg-brand-muted text-brand"
                    : "text-ink-secondary hover:bg-brand-ghost hover:text-brand",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          {user.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3 py-1.5 text-sm font-medium transition",
                  isActive
                    ? "bg-brand-muted text-brand"
                    : "text-ink-secondary hover:bg-brand-ghost hover:text-brand",
                )
              }
            >
              Admin
            </NavLink>
          )}
        </nav>
      </div>

      <div className="flex items-center gap-3">
        {/* Action Queue is RM/Manager/Admin workspace — hidden for Executive (§3 matrix). */}
        {user.role !== "executive" && (
          <NavLink
            to="/actions"
            className="relative inline-flex items-center gap-2 rounded-full border border-brand-edge px-4 py-2 text-sm font-medium text-brand transition hover:bg-brand-ghost"
          >
            <Bell className="h-4 w-4" />
            Queue
            {queueCount > 0 && (
              <span className="ml-1 inline-grid h-5 min-w-5 place-items-center rounded-full bg-brand px-1 text-xs font-medium text-ink-on-brand shadow-[0_0_0_3px_var(--color-brand-primary-glow)]">
                {queueCount}
              </span>
            )}
          </NavLink>
        )}
        <div
          className="grid h-10 w-10 place-items-center rounded-full bg-ink-primary text-sm font-semibold text-ink-on-brand"
          title={`${user.displayName} · ${user.email}`}
        >
          {initials(user.displayName)}
        </div>
      </div>
    </header>
  );
}

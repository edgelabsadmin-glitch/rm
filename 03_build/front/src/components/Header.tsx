/*
 * SPEC-034 — App header (chrome). Brand mark (purple Zap tile, §6 tinted-shadow
 * moment #2), primary nav, Queue button with live badge, and the user avatar from
 * the stubbed session. Admin nav is hidden unless the session role is admin
 * (visibility only — server-side scope is authoritative).
 */
import { Bell, LogOut, Zap } from "lucide-react";
import { NavLink } from "react-router-dom";
import { usePulseState } from "@/components/PulseStateProvider";
import { DEMO_USERS } from "@/fixtures/demo_characters";
import { useAuth } from "@/lib/auth/AuthContext";
import type { UserRole } from "@/lib/rbac/types";
import { cn } from "@/lib/utils";

// SPEC-042 Step-9 (DoD §12): dev-only persona switcher so the demo operator can walk Stories
// A/B/C (Yozeline RM / Sarah Manager / Iffi Executive) without real SSO. Gated on
// import.meta.env.DEV — never shipped to production (spec 043 OAuth hydrates AuthContext instead).
const ROLE_RANK: Record<UserRole, number> = { executive: 0, manager: 1, rm: 2, admin: 3 };
const SWITCHER_USERS = [...DEMO_USERS].sort((a, b) => ROLE_RANK[a.role] - ROLE_RANK[b.role]);

// SPEC-042 Step 3: nav links are role-gated (visibility layer; RoleGuard enforces direct
// URL access). Executive View is exec/admin only; Settings is admin only.
const NAV: { to: string; label: string; roles: UserRole[] }[] = [
  { to: "/accounts",   label: "Accounts",       roles: ["rm", "manager", "executive", "admin"] },
  { to: "/constellation", label: "Constellation", roles: ["rm", "manager", "executive", "admin"] },
  { to: "/executive",  label: "Executive View",  roles: ["executive", "admin"] },
  { to: "/submit",     label: "Submit",          roles: ["rm", "manager", "executive", "admin"] },
  { to: "/support",    label: "Support",         roles: ["rm", "manager", "executive", "admin"] },
  { to: "/settings/users", label: "Settings",   roles: ["admin"] },
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
  const { user, switchUser, logout } = useAuth();
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
        {/* Dev-only persona switcher (DoD §12) — hidden in production builds. */}
        {import.meta.env.DEV && (
          <label className="flex items-center gap-1.5 text-xs text-ink-secondary">
            <span className="hidden sm:inline">View as</span>
            <select
              data-testid="dev-user-switcher"
              aria-label="Switch demo user"
              value={user.id}
              onChange={(e) => switchUser(e.target.value)}
              className="rounded-md border border-line-strong bg-surface-card px-2 py-1 text-xs text-ink-primary"
            >
              {SWITCHER_USERS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.displayName} · {u.role}
                </option>
              ))}
            </select>
          </label>
        )}
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
        {/* Avatar + logout */}
        <div className="group relative">
          <div
            className="grid h-10 w-10 cursor-pointer place-items-center rounded-full bg-ink-primary text-sm font-semibold text-ink-on-brand"
            title={`${user.displayName} · ${user.email}`}
          >
            {initials(user.displayName)}
          </div>
          {/* Logout tooltip on hover */}
          {!import.meta.env.DEV && (
            <button
              type="button"
              onClick={logout}
              className="absolute right-0 top-full mt-1 hidden items-center gap-1.5 whitespace-nowrap rounded-xl border border-line-subtle bg-white px-3 py-2 text-xs text-ink-secondary shadow-lg hover:text-ink-primary group-hover:flex"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

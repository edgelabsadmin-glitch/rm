/*
 * SPEC-034 — nested admin layout. Role-gated to admin (visibility only; server-side
 * scope per spec 042 is the security boundary). Sub-nav for the Layer-8 admin
 * surfaces (specs 044/045) + Settings/kill-switch (spec 010). Non-admins are
 * redirected to /accounts.
 */
import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useUser } from "@/lib/auth/AuthContext";
import { cn } from "@/lib/utils";

const ADMIN_NAV = [
  { to: "/admin/signals", label: "Signal Performance" },
  { to: "/admin/outcomes", label: "Outcome Tracking" },
  { to: "/admin/settings", label: "Settings" },
];

export function AdminLayout() {
  const user = useUser();
  if (user.role !== "admin") return <Navigate to="/accounts" replace />;

  return (
    <div className="p-6">
      <nav className="mb-5 flex items-center gap-1">
        {ADMIN_NAV.map((item) => (
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
      </nav>
      <Outlet />
    </div>
  );
}

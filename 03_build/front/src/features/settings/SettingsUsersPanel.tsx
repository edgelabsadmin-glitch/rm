/*
 * SPEC-042 Step-7 — Settings panel /settings/users (Admin-only; RoleGuard enforces the route).
 * Hybrid disposition: read-only role topology in Phase 1A; the "Change role" workflow lands
 * Phase 2. Three-column workspace (role-filter chips · 11-user table · selected-user detail),
 * mirroring the AccountWorkspace grid-cols-12 (3/6/3) pattern. All scope counts derived from
 * deriveAccountScope (no hardcoding); permission summaries from the spec §3 matrix.
 */
import { useMemo, useState } from "react";
import { DEMO_ACCOUNTS, DEMO_USERS, type DemoUser } from "@/fixtures/demo_characters";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { UserRole } from "@/lib/rbac/types";
import { cn } from "@/lib/utils";

type RoleFilter = "all" | UserRole;
type Severity = "warning" | "reference" | "opportunity";

const ROLE_FILTERS: { id: RoleFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "executive", label: "Executive" },
  { id: "manager", label: "Manager" },
  { id: "rm", label: "RM" },
  { id: "admin", label: "Admin" },
];

// Sort order Executives → Managers → RMs → Admin (spec §9).
const ROLE_ORDER: Record<UserRole, number> = { executive: 0, manager: 1, rm: 2, admin: 3 };
const ROLE_SEVERITY: Record<UserRole, Severity> = {
  executive: "warning",
  manager: "warning",
  rm: "reference",
  admin: "opportunity",
};
const ROLE_LABEL: Record<UserRole, string> = {
  executive: "Executive",
  manager: "Manager",
  rm: "RM",
  admin: "Admin",
};

const accountName = (id: string) => DEMO_ACCOUNTS.find((a) => a.id === id)?.name ?? id;

/** "14 (full org)" / "7 (team scope)" / "3" — derived count, contextual label. */
function formatScope(role: UserRole, count: number): string {
  if (role === "executive" || role === "admin") return `${count} (full org)`;
  if (role === "manager") return `${count} (team scope)`;
  return String(count);
}

const PERMISSIONS: Record<UserRole, string> = {
  rm: "Can access: Action Queue (own book), Per-Account View (in scope), Constellation (own book). Cannot access: Executive View, Settings.",
  manager:
    "Can access: Action Queue (team), Per-Account View (team), Constellation (team). Cannot access: Executive View, Settings.",
  executive:
    "Can access: Executive View, Constellation (full org), Per-Account View (read-only, full org). Cannot access: Action Queue, Settings.",
  admin:
    "Can access: everything — Action Queue, Per-Account View, Constellation, Executive View, Settings.",
};

function RoleChip({ role }: { role: UserRole }) {
  const sev = ROLE_SEVERITY[role];
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: `var(--color-chip-${sev}-bg)`, color: `var(--color-chip-${sev}-text)` }}
    >
      {ROLE_LABEL[role]}
    </span>
  );
}

function Avatar({ initials, size = 24 }: { initials: string; size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-md bg-surface-card text-[10px] font-semibold text-ink-primary"
      style={{ height: size, width: size, border: "0.5px solid var(--color-line-strong)" }}
    >
      {initials}
    </span>
  );
}

interface UserRow extends DemoUser {
  scope: string[];
}

export function SettingsUsersPanel() {
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [showRoleNote, setShowRoleNote] = useState(false);

  const userRows = useMemo<UserRow[]>(
    () =>
      [...DEMO_USERS]
        .sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role])
        .map((u) => ({ ...u, scope: deriveAccountScope(u.role, u.id) })),
    [],
  );

  const visibleUsers = useMemo(
    () => (roleFilter === "all" ? userRows : userRows.filter((u) => u.role === roleFilter)),
    [userRows, roleFilter],
  );

  const selectedUser = userRows.find((u) => u.id === selectedUserId) ?? null;

  return (
    <div className="grid grid-cols-12 gap-0">
      {/* Left — role filter chips */}
      <aside className="col-span-12 border-b border-line-subtle bg-surface-sidebar p-5 lg:col-span-3 lg:border-b-0 lg:border-r">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Users
        </h2>
        <div className="flex flex-wrap gap-2 lg:flex-col lg:items-start">
          {ROLE_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setRoleFilter(f.id)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition",
                roleFilter === f.id
                  ? "border-brand-edge bg-brand-muted text-brand"
                  : "border-line-strong bg-surface-card text-ink-secondary hover:bg-brand-ghost hover:text-brand",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </aside>

      {/* Center — user table */}
      <main className="col-span-12 p-6 lg:col-span-6">
        <div className="grid grid-cols-[24px_1.4fr_1.6fr_0.8fr_1fr] items-center gap-2 px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
          <span />
          <span>Name</span>
          <span>Email</span>
          <span>Role</span>
          <span>Scope</span>
        </div>
        <div className="space-y-1">
          {visibleUsers.map((u) => (
            <button
              key={u.id}
              type="button"
              data-testid="user-row"
              aria-current={u.id === selectedUserId}
              onClick={() => {
                setSelectedUserId(u.id);
                setShowRoleNote(false);
              }}
              className={cn(
                "grid w-full grid-cols-[24px_1.4fr_1.6fr_0.8fr_1fr] items-center gap-2 rounded-lg px-2 py-2 text-left text-xs transition",
                u.id === selectedUserId
                  ? "bg-surface-card shadow-sm"
                  : "hover:bg-brand-ghost",
              )}
            >
              <Avatar initials={u.avatarInitials} />
              <span className="font-medium text-ink-primary">{u.displayName}</span>
              <span className="truncate text-ink-secondary">{u.email}</span>
              <span><RoleChip role={u.role} /></span>
              <span className="font-mono text-ink-secondary">{formatScope(u.role, u.scope.length)}</span>
            </button>
          ))}
        </div>
      </main>

      {/* Right — selected-user detail */}
      <aside className="col-span-12 border-t border-line-subtle bg-surface-sidebar-soft p-6 lg:col-span-3 lg:border-l lg:border-t-0">
        {selectedUser ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Avatar initials={selectedUser.avatarInitials} size={40} />
              <div className="min-w-0">
                <div className="truncate font-semibold text-ink-primary">{selectedUser.displayName}</div>
                <div className="truncate text-xs text-ink-secondary">{selectedUser.email}</div>
              </div>
            </div>
            <RoleChip role={selectedUser.role} />

            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Account scope · {selectedUser.scope.length}
              </div>
              <ul className="space-y-1 text-xs text-ink-secondary">
                {selectedUser.scope.map((id) => (
                  <li key={id}>{accountName(id)}</li>
                ))}
              </ul>
            </div>

            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Permissions
              </div>
              <p className="text-xs leading-5 text-ink-secondary">{PERMISSIONS[selectedUser.role]}</p>
            </div>

            <button
              type="button"
              onClick={() => setShowRoleNote(true)}
              className="rounded-md px-3 py-1.5 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
              style={{ border: "0.5px solid var(--color-line-strong)" }}
            >
              Change role
            </button>
            {showRoleNote && (
              <p className="rounded-md bg-surface-tinted-row p-3 text-xs text-ink-secondary">
                Role assignment workflow coming in Phase 2. Contact Pulse support to change role
                assignments.
              </p>
            )}
          </div>
        ) : (
          <div className="text-sm text-ink-secondary">Click a user to view details.</div>
        )}
      </aside>
    </div>
  );
}

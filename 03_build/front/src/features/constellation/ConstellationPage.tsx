/*
 * ConstellationPage — top-level shell for /constellation.
 *
 * Owns filter state (team-member scope, account expansion) and composes:
 *   left  → filter bar + Constellation canvas (overlays suppressed)
 *   right → ConstellationSidebar (action items list)
 *
 * RBAC:
 *   RM         → sees only their own accounts (authScope)
 *   Manager    → sees full team by default; team-member dropdown narrows scope
 *   Admin/Exec → sees all accounts; no team filter shown
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, useUser } from "@/lib/auth/AuthContext";
import { DEMO_ACCOUNTS, DEMO_RMS } from "@/fixtures/demo_characters";
import { DEMO_TIER_JUMP_EVENTS } from "@/fixtures/demo_tier_jump_events";
import {
  composeCapacityImbalance,
} from "./composers/rm_capacity_composer";
import { composeEscalationTierJumps } from "./composers/escalation_tier_jump_composer";
import { DEMO_PATTERNS } from "./demo_patterns";
import { Constellation } from "./Constellation";
import { ConstellationSidebar } from "./ConstellationSidebar";

export function ConstellationPage() {
  const user = useUser();
  const { accountScope: authScope } = useAuth();
  const navigate = useNavigate();

  // Manager team-member filter (null = all team members)
  const [selectedRmId, setSelectedRmId] = useState<string | null>(null);
  // Account expansion for talent drill-down (controlled from dropdown + graph clicks)
  const [expandedAccountId, setExpandedAccountId] = useState<string | null>(null);

  // Team members available to a manager for the filter dropdown
  const teamRMs = useMemo(() => {
    if (user.role !== "manager") return [];
    // user.managerId is the manager's own slug in DEMO_MANAGERS/DEMO_RMS.
    return DEMO_RMS.filter((rm) => rm.managerId === user.managerId);
  }, [user]);

  // When an RM is selected, narrow the account scope to that RM's accounts only
  const filteredScope = useMemo((): string[] | undefined => {
    if (!selectedRmId) return authScope as string[] | undefined;
    const rmAccountIds = DEMO_ACCOUNTS
      .filter((a) => a.rmId === selectedRmId)
      .map((a) => a.id);
    return authScope
      ? rmAccountIds.filter((id) => (authScope as string[]).includes(id))
      : rmAccountIds;
  }, [selectedRmId, authScope]);

  // Accounts visible in the current scope (for the account filter dropdown)
  const scopedAccounts = useMemo(
    () =>
      filteredScope === undefined
        ? [...DEMO_ACCOUNTS]
        : DEMO_ACCOUNTS.filter((a) => filteredScope.includes(a.id)),
    [filteredScope],
  );

  // Alert data — same pure composers as Constellation.tsx uses internally
  const capacityCards = useMemo(
    () => composeCapacityImbalance(DEMO_ACCOUNTS, DEMO_RMS, filteredScope),
    [filteredScope],
  );
  const escalationCards = useMemo(
    () => composeEscalationTierJumps(DEMO_TIER_JUMP_EVENTS, filteredScope),
    [filteredScope],
  );
  const scopedPatterns = useMemo(
    () =>
      filteredScope
        ? DEMO_PATTERNS.filter((p) =>
            p.support_account_ids.every((id) => filteredScope.includes(id)),
          )
        : DEMO_PATTERNS,
    [filteredScope],
  );

  function handleRmChange(rmId: string) {
    setSelectedRmId(rmId || null);
    setExpandedAccountId(null); // collapse talent when scope changes
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* ── Canvas column ─────────────────────────────────────────── */}
      <div className="relative min-w-0 flex-1">
        {/* Filter bar — floats over the top-left of the canvas */}
        <div className="absolute left-4 top-4 z-20 flex flex-wrap items-center gap-2">
          {/* Manager team-member filter */}
          {user.role === "manager" && teamRMs.length > 0 && (
            <FilterSelect
              value={selectedRmId ?? ""}
              onChange={handleRmChange}
              placeholder="All team members"
              options={teamRMs.map((rm) => ({ value: rm.id, label: rm.name }))}
            />
          )}
          {/* Account filter — expands talent for the selected account */}
          <FilterSelect
            value={expandedAccountId ?? ""}
            onChange={(v) => setExpandedAccountId(v || null)}
            placeholder="All accounts"
            options={scopedAccounts.map((a) => ({ value: a.id, label: a.name }))}
          />
        </div>

        <Constellation
          accountScope={filteredScope}
          expandedAccountId={expandedAccountId}
          onExpandedChange={setExpandedAccountId}
          hideOverlays
        />
      </div>

      {/* ── Action-items sidebar ───────────────────────────────────── */}
      <aside className="w-80 shrink-0 overflow-y-auto border-l border-line-subtle bg-surface-sidebar-soft">
        <ConstellationSidebar
          patterns={scopedPatterns}
          capacityCards={capacityCards}
          escalationCards={escalationCards}
          onInvestigatePattern={(p) =>
            navigate(`/actions?pattern=${encodeURIComponent(p.id)}`)
          }
          onInvestigateCapacity={(c) =>
            navigate(`/actions?rm=${encodeURIComponent(c.topLoadedRmId)}`)
          }
          onInvestigateEscalation={(c) =>
            navigate(`/accounts/${encodeURIComponent(c.accountId)}`)
          }
        />
      </aside>
    </div>
  );
}

// ── Shared filter select ───────────────────────────────────────────────────────

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-line-strong bg-surface-card/90 px-3 py-1.5 text-xs text-ink-primary shadow-sm backdrop-blur-sm focus:outline-none focus:ring-1 focus:ring-brand"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

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
import { DEMO_ACCOUNTS, DEMO_RMS, DEMO_USERS, managerSfUserIds } from "@/fixtures/demo_characters";

// SF user IDs of all known RMs — used to filter constellation to RM-owned accounts only.
const ALL_RM_SF_IDS = DEMO_RMS
  .flatMap((rm) => {
    const u = DEMO_USERS.find((u) => u.id === rm.id);
    return u?.sfUserId ? [u.sfUserId] : [];
  })
  .join(",");
import { DEMO_TIER_JUMP_EVENTS } from "@/fixtures/demo_tier_jump_events";
import { useAccounts } from "@/features/account/hooks";
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
  // Constellation-specific filters
  const [filterTier, setFilterTier] = useState("");
  const [filterRisk, setFilterRisk] = useState("");
  const [filterSegment, setFilterSegment] = useState("");

  // Team members available to a manager for the filter dropdown
  const teamRMs = useMemo(() => {
    if (user.role !== "manager") return [];
    return DEMO_RMS.filter((rm) => rm.managerId === user.managerId);
  }, [user]);

  // Compute API filter scoped by role (RBAC):
  //   RM         → their own accounts only ({ rm_id })
  //   Manager    → their team's accounts ({ rm_ids }); team-member dropdown narrows to one RM
  //   Admin/Exec → the whole constellation (all RM-owned accounts)
  const apiFilter = useMemo(() => {
    let rmScope: { rm_id?: string; rm_ids?: string };
    if (selectedRmId) {
      const sfId = DEMO_USERS.find((u) => u.id === selectedRmId)?.sfUserId;
      rmScope = sfId ? { rm_id: sfId } : { rm_ids: ALL_RM_SF_IDS };
    } else if (user.role === "rm") {
      rmScope = { rm_id: user.sfUserId ?? user.id };
    } else if (user.role === "manager") {
      const ids = managerSfUserIds(user.id);
      rmScope = ids.length ? { rm_ids: ids.join(",") } : { rm_ids: ALL_RM_SF_IDS };
    } else {
      rmScope = { rm_ids: ALL_RM_SF_IDS }; // admin / executive
    }
    return {
      ...rmScope,
      active_only: true as const,
      ...(filterTier ? { tier: filterTier } : {}),
      ...(filterRisk ? { risk: filterRisk } : {}),
      ...(filterSegment ? { segment: filterSegment } : {}),
    };
  }, [selectedRmId, user, filterTier, filterRisk, filterSegment]);

  // Fetch real accounts (all pages at once — max 1000)
  const { data: accountsData, isLoading: accountsLoading } = useAccounts({
    ...apiFilter,
    page_size: 1000,
  });

  const realAccounts = accountsData?.accounts ?? [];

  // Accounts visible in the current scope (for the account filter dropdown)
  const scopedAccounts = realAccounts;

  // Legacy fixture scope kept for sidebar composers (still fixture-based)
  const filteredScope = useMemo((): string[] | undefined => {
    if (!selectedRmId) return authScope as string[] | undefined;
    const rmAccountIds = DEMO_ACCOUNTS
      .filter((a) => a.rmId === selectedRmId)
      .map((a) => a.id);
    return authScope
      ? rmAccountIds.filter((id) => (authScope as string[]).includes(id))
      : rmAccountIds;
  }, [selectedRmId, authScope]);

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
          {/* Tier filter */}
          <FilterSelect
            value={filterTier}
            onChange={setFilterTier}
            placeholder="All tiers"
            options={[
              { value: "Strategic", label: "Strategic" },
              { value: "Growth", label: "Growth" },
              { value: "Core", label: "Core" },
            ]}
          />
          {/* Risk filter */}
          <FilterSelect
            value={filterRisk}
            onChange={setFilterRisk}
            placeholder="All risk levels"
            options={[
              { value: "Low", label: "Low risk" },
              { value: "Medium", label: "Medium risk" },
              { value: "High", label: "High risk" },
            ]}
          />
          {/* Segment filter */}
          <FilterSelect
            value={filterSegment}
            onChange={setFilterSegment}
            placeholder="All segments"
            options={[
              { value: "ENT", label: "Enterprise" },
              { value: "MID-MKT", label: "Mid-Market" },
              { value: "SMB", label: "SMB" },
            ]}
          />
          {/* Account filter — expands talent for the selected account */}
          <FilterSelect
            value={expandedAccountId ?? ""}
            onChange={(v) => setExpandedAccountId(v || null)}
            placeholder="All accounts"
            options={scopedAccounts.map((a) => ({ value: a.account_id, label: a.name }))}
          />
        </div>

        <Constellation
          accounts={realAccounts}
          accountsLoading={accountsLoading}
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

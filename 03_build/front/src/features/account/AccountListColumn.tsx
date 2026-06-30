/*
 * SPEC-037 — left-rail account list with client-side search and filter chips.
 *
 * Scope filtering is server-side (rm_id / rm_ids). Search + risk/tier chips
 * filter the already-loaded list locally for instant response.
 */
import { useState, useMemo } from "react";
import { CalendarDays, Search, X } from "lucide-react";
import { RiskBadge } from "@/components/RiskBadge";
import { buildAccountFilter, formatARR } from "@/fixtures/demo_characters";
import { useUser } from "@/lib/auth/AuthContext";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { cn } from "@/lib/utils";
import { useAccounts } from "./hooks";
import { useAccountMatrices } from "@/features/analysis/hooks";
import { PriorityDot, priorityRank } from "@/features/analysis/PriorityDot";
import type { AccountSummaryDTO } from "@/lib/api";

type RiskLevel = AccountSummaryDTO["risk"] | "All";
type TierLevel = "All" | "Core" | "Growth" | "Strategic";

const RISK_OPTIONS: RiskLevel[] = ["All", "Low", "Medium", "High"];
const TIER_OPTIONS: TierLevel[] = ["All", "Core", "Growth", "Strategic"];

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full px-2.5 py-0.5 text-xs font-medium transition",
        active
          ? "bg-brand text-white"
          : "bg-white/70 text-ink-secondary hover:bg-white hover:text-ink-primary",
      )}
    >
      {label}
    </button>
  );
}

export function AccountListColumn() {
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();
  const user = useUser();

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel>("All");
  const [tierFilter, setTierFilter] = useState<TierLevel>("All");

  // RM → their own accounts; Manager → their accounts + team's; Exec/Admin → all.
  const { data, isLoading } = useAccounts(buildAccountFilter(user));
  const accounts = data?.accounts ?? [];
  const { data: matrices } = useAccountMatrices();

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = accounts.filter((a) => {
      if (q && !a.name.toLowerCase().includes(q)) return false;
      if (riskFilter !== "All" && a.risk !== riskFilter) return false;
      if (tierFilter !== "All" && a.tier !== tierFilter) return false;
      return true;
    });
    // Sort by analysis-agent priority (critical first); ties keep API order.
    return [...rows].sort(
      (a, b) =>
        priorityRank(matrices?.get(a.account_id)?.priority) -
        priorityRank(matrices?.get(b.account_id)?.priority),
    );
  }, [accounts, search, riskFilter, tierFilter, matrices]);

  const hasActiveFilter = search.trim() || riskFilter !== "All" || tierFilter !== "All";

  function clearAll() {
    setSearch("");
    setRiskFilter("All");
    setTierFilter("All");
  }

  return (
    <aside className="col-span-12 flex flex-col border-b border-line-subtle bg-surface-sidebar p-5 lg:col-span-3 lg:border-b-0 lg:border-r">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Accounts
        </h2>
        <span className="text-xs text-ink-muted">
          {hasActiveFilter ? `${filtered.length} of ${data?.total ?? 0}` : (data?.total ?? "")}
        </span>
      </div>

      {/* Search */}
      <div className="relative mb-2">
        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" />
        <input
          type="text"
          placeholder="Search accounts…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl border border-line-subtle bg-white/70 py-1.5 pl-8 pr-8 text-sm text-ink-primary placeholder:text-ink-muted focus:border-brand-soft focus:outline-none focus:ring-0"
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink-primary"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Filter chips */}
      <div className="mb-3 space-y-1.5">
        <div className="flex flex-wrap gap-1">
          {RISK_OPTIONS.map((r) => (
            <FilterChip
              key={r}
              label={r === "All" ? "Risk: All" : r}
              active={riskFilter === r}
              onClick={() => setRiskFilter(r)}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {TIER_OPTIONS.map((t) => (
            <FilterChip
              key={t}
              label={t === "All" ? "Tier: All" : t}
              active={tierFilter === t}
              onClick={() => setTierFilter(t)}
            />
          ))}
        </div>
        {hasActiveFilter && (
          <button
            type="button"
            onClick={clearAll}
            className="flex items-center gap-1 text-xs text-ink-muted hover:text-ink-primary"
          >
            <X className="h-3 w-3" /> Clear all
          </button>
        )}
      </div>

      {/* Account list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-3xl bg-white/50" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="mt-6 text-center text-sm text-ink-muted">No accounts match.</p>
      ) : (
        <div className="flex-1 space-y-3 overflow-y-auto" style={{ maxHeight: "calc(100vh - 20rem)" }}>
          {filtered.map((account) => {
            const active = account.account_id === selectedAccountId;
            const matrix = matrices?.get(account.account_id);
            return (
              <button
                key={account.account_id}
                type="button"
                aria-current={active}
                onClick={() => setSelectedAccountId(account.account_id)}
                className={cn(
                  "w-full rounded-3xl border p-4 text-left transition",
                  active
                    ? "border-line-brand bg-surface-card shadow-lg shadow-slate-200"
                    : "border-transparent bg-white/70 hover:border-brand-soft hover:bg-surface-card",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 font-semibold tracking-tight text-ink-primary">
                      {matrix && (
                        <PriorityDot color={matrix.priority_color} priority={matrix.priority} />
                      )}
                      {account.name}
                    </div>
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-ink-secondary">
                      <CalendarDays className="h-3.5 w-3.5" /> {account.meeting}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <RiskBadge level={account.risk} />
                    <span className="font-mono text-xs text-ink-muted">
                      {formatARR(account.arr_usd)}
                    </span>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs">
                  <span className="text-ink-secondary">Composite health</span>
                  <span className="font-semibold text-ink-primary">{account.composite_health}/10</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-surface-track">
                  <div
                    className="h-2 rounded-full bg-brand"
                    style={{ width: `${account.composite_health * 10}%` }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </aside>
  );
}

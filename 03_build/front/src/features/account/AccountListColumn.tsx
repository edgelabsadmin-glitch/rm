/*
 * SPEC-037 — left-rail account list (Tier-0 §8.12 + §9.3 left column). Scrollable
 * selectable cards: name, risk badge, next-key-event subtitle, composite-health bar.
 * Click writes selectedAccountId (the context spec 036 added); active card highlighted
 * (white-on-tinted-rail, purple-edged border, slate shadow).
 *
 * Data: real SFDC accounts via GET /accounts. Falls back to demo fixtures in DEV when
 * the FastAPI backend is unreachable (same pattern as listActions).
 */
import { useEffect } from "react";
import { CalendarDays } from "lucide-react";
import { RiskBadge } from "@/components/RiskBadge";
import { formatARR } from "@/fixtures/demo_characters";
import { DEFAULT_ACCOUNT_ID, useSelectedAccount } from "@/session/SelectedAccountProvider";
import { cn } from "@/lib/utils";
import { useAccounts } from "./hooks";

export function AccountListColumn() {
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();
  const { data, isLoading } = useAccounts();
  const accounts = data?.accounts ?? [];

  // Auto-select the first real SF account once the list loads.
  useEffect(() => {
    if (accounts.length > 0 && selectedAccountId === DEFAULT_ACCOUNT_ID) {
      setSelectedAccountId(accounts[0].account_id);
    }
  }, [accounts, selectedAccountId, setSelectedAccountId]);

  return (
    <aside className="col-span-12 border-b border-line-subtle bg-surface-sidebar p-5 lg:col-span-3 lg:border-b-0 lg:border-r">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Accounts
        </h2>
        {data && (
          <span className="text-xs text-ink-muted">{data.total}</span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-3xl bg-white/50" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {accounts.map((account) => {
            const active = account.account_id === selectedAccountId;
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
                    <div className="font-semibold tracking-tight text-ink-primary">
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

/*
 * SPEC-035/038/042 — Action Queue list. Cards from GET /actions (10s polling via useActions),
 * scoped to the caller's role (spec 042 Step-5) then refined by UX filters: Status (Active/
 * Approved/All) + Time (All time/Today/This week) + Tier chips + URL ?rm=. The dead My-Queue/
 * Overall toggle was removed (role scope is authoritative). Selections persisted in localStorage.
 *
 * Per-account mode (customerId prop): used in the AccountWorkspace right rail. When set,
 * filter is scoped to that account and the Status/Time/Tier chips are hidden.
 */
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { cn } from "@/lib/utils";
import { useActions } from "./hooks";
import { QueueCard } from "./QueueCard";
import {
  applyStatusFilter,
  applyTimeFilter,
  scopeAndRefineCards,
  type StatusFilter,
  type TimeFilter,
} from "./queue_scope";
import type { QueueFilters } from "./types";

const STATUS_OPTS: { id: StatusFilter; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "approved", label: "Approved" },
  { id: "all", label: "All" },
];
const TIME_OPTS: { id: TimeFilter; label: string }[] = [
  { id: "all-time", label: "All time" },
  { id: "today", label: "Today" },
  { id: "this-week", label: "This week" },
];
// EDGE white-label segment names (display) → spec-031 policy tier_class keys (API).
const TIERS: { label: string; key: string }[] = [
  { label: "Core", key: "SMB" },
  { label: "Growth", key: "Mid-Market" },
  { label: "Strategic", key: "Enterprise" },
];

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium transition",
        active
          ? "border-brand-edge bg-brand-muted text-brand"
          : "border-line-strong bg-surface-card text-ink-secondary hover:bg-brand-ghost hover:text-brand",
      )}
    >
      {children}
    </button>
  );
}

interface Props {
  /** When set, shows only this account's actions (per-account right-rail mode). */
  customerId?: string;
  accountName?: string;
}

export function QueueList({ customerId, accountName }: Props = {}) {
  const { user } = useAuth();
  const reduce = useReducedMotion();
  const [tier, setTier] = useLocalStorage<string | null>("pulse.queue.tier", null);
  const [statusFilter, setStatusFilter] = useLocalStorage<StatusFilter>(
    "pulse.queue.status",
    "active",
  );
  const [timeFilter, setTimeFilter] = useLocalStorage<TimeFilter>("pulse.queue.time", "all-time");

  // SPEC-041 routing: Constellation RM clicks deep-link here with ?rm= (refines within scope).
  const [sp] = useSearchParams();
  const rmParam = sp.get("rm");
  const managerParam = sp.get("manager");
  const constellationFilter = rmParam || managerParam;

  const isPerAccount = !!customerId;

  // API fetch: per-account mode scopes to that account; global mode uses RBAC role scope.
  const filters: QueueFilters = useMemo(() => {
    if (isPerAccount) return { customer_id: customerId };
    return { rm_id: user.role === "rm" ? user.id : undefined, tier: tier ?? undefined };
  }, [isPerAccount, customerId, user.role, user.id, tier]);

  const { data, isLoading, isError, error } = useActions(filters);
  const fetched = data?.actions ?? [];

  // Cumulative: role scope (security) → URL ?rm= (UX) → Status (UX) → Time (UX).
  // Per-account mode skips the scope/refine pipeline — filter was already applied server-side.
  const actions = useMemo(() => {
    if (isPerAccount) return fetched;
    const scoped = scopeAndRefineCards(fetched, user.role, user.id, rmParam);
    return applyTimeFilter(applyStatusFilter(scoped, statusFilter), timeFilter);
  }, [isPerAccount, fetched, user.role, user.id, rmParam, statusFilter, timeFilter]);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold uppercase tracking-[0.18em] text-ink-secondary">
            Action Queue
          </h1>
          {isPerAccount && accountName && (
            <p className="mt-0.5 text-xs text-ink-muted truncate max-w-[200px]">{accountName}</p>
          )}
        </div>
        <span className="text-xs text-ink-secondary">{actions.length} shown</span>
      </div>

      {!isPerAccount && constellationFilter && (
        <div className="mb-4 flex items-center justify-between rounded-2xl bg-brand-muted px-3 py-2 text-xs text-brand">
          <span>
            From the constellation —{" "}
            {rmParam ? (
              <>filtered to RM <span className="font-mono">{rmParam}</span></>
            ) : (
              <>
                showing <span className="font-mono">{managerParam}</span>'s team{" "}
                <span className="text-ink-muted">(manager scoping wires in Week 4)</span>
              </>
            )}
          </span>
          <Link to="/actions" className="font-medium underline">
            Clear
          </Link>
        </div>
      )}

      {/* Filter rows (Option A): Status · Time on top, Tier below. Hidden in per-account mode. */}
      {!isPerAccount && (
        <div className="mb-4 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {STATUS_OPTS.map((s) => (
              <Chip key={s.id} active={statusFilter === s.id} onClick={() => setStatusFilter(s.id)}>
                {s.label}
              </Chip>
            ))}
            <span className="mx-1 h-4 w-px bg-line-strong" />
            {TIME_OPTS.map((t) => (
              <Chip key={t.id} active={timeFilter === t.id} onClick={() => setTimeFilter(t.id)}>
                {t.label}
              </Chip>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {TIERS.map((t) => (
              <Chip
                key={t.key}
                active={tier === t.key}
                onClick={() => setTier(tier === t.key ? null : t.key)}
              >
                {t.label}
              </Chip>
            ))}
          </div>
        </div>
      )}

      {isLoading && <p className="text-sm text-ink-secondary">Loading queue…</p>}
      {isError && (
        <p className="text-sm text-risk-high-fg">
          Couldn't load the queue: {(error as Error)?.message ?? "unknown error"}
        </p>
      )}
      {!isLoading && !isError && actions.length === 0 && (
        <div className="flex items-center gap-2 rounded-3xl bg-surface-tinted-row p-4 text-sm text-ink-secondary">
          <Sparkles className="h-4 w-4 text-brand" />
          All clear — Pulse will surface new actions here.
        </div>
      )}

      <div className="space-y-3">
        <AnimatePresence initial={false}>
          {actions.map((a) => (
            <motion.div
              key={a.action_id}
              layout
              initial={reduce ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              <QueueCard action={a} isAdmin={user.role === "admin"} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

/*
 * SPEC-035/038 — Action Queue list. Ranked pending cards from GET /actions (10s
 * polling via useActions). Bucket selector (Design 03 §"Left-rail navigation"):
 * My Queue / Overall (pending) + Approved / Dispatched. Tier filter chips. Selections
 * persisted in localStorage (Q36). Fade-and-lift entrance + AnimatePresence exit.
 *
 * Buckets note (option-b, spec 038 req 4): GET /actions is pending-only, so the
 * Approved/Dispatched buckets render a flagged empty state — wiring them needs a
 * `status` filter param on the spec-031 API (Week-4 follow-up). My Queue/Overall
 * work today.
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
import { scopeAndRefineCards } from "./queue_scope";
import type { QueueFilters } from "./types";

type View = "mine" | "overall" | "approved" | "dispatched";
const VIEWS: { id: View; label: string }[] = [
  { id: "mine", label: "My Queue" },
  { id: "overall", label: "Overall" },
  { id: "approved", label: "Approved" },
  { id: "dispatched", label: "Dispatched" },
];
const PENDING_VIEWS: View[] = ["mine", "overall"];
// EDGE white-label segment names (display) → spec-031 policy tier_class keys (API).
// The display sweep does NOT touch Design-04 policy keys (per ruling: out of scope).
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

export function QueueList() {
  const { user } = useAuth();
  const reduce = useReducedMotion();
  const [view, setView] = useLocalStorage<View>("pulse.queue.view", "mine");
  const [tier, setTier] = useLocalStorage<string | null>("pulse.queue.tier", null);

  // SPEC-041 routing: Constellation RM/manager clicks deep-link here with ?rm= / ?manager=.
  // Present params override the local view; absent → existing My-Queue/Overall behavior.
  const [sp] = useSearchParams();
  const rmParam = sp.get("rm");
  const managerParam = sp.get("manager");
  const constellationFilter = rmParam || managerParam;
  const isPendingView = constellationFilter ? true : PENDING_VIEWS.includes(view);

  // API fetch is scoped by the caller's role (demo_actions / backend Caller). The URL ?rm=
  // refinement is applied CLIENT-SIDE on top of the authoritative role scope below — so a
  // crafted ?rm= can never widen what the caller sees (spec 042 Step-5).
  const filters: QueueFilters = useMemo(
    () => ({ rm_id: user.role === "rm" ? user.id : undefined, tier: tier ?? undefined }),
    [user.role, user.id, tier],
  );

  const { data, isLoading, isError, error } = useActions(filters);
  const fetched = data?.actions ?? [];

  // Authoritative role scope (security) then URL ?rm= refinement (UX) — see queue_scope.ts.
  const actions = useMemo(
    () => scopeAndRefineCards(fetched, user.role, user.id, rmParam),
    [fetched, user.role, user.id, rmParam],
  );

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Action Queue
        </h1>
        {isPendingView && <span className="text-xs text-ink-secondary">{actions.length} pending</span>}
      </div>

      {constellationFilter && (
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

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {VIEWS.map((v) => (
          <Chip key={v.id} active={view === v.id} onClick={() => setView(v.id)}>
            {v.label}
          </Chip>
        ))}
        {isPendingView && (
          <>
            <span className="mx-1 h-4 w-px bg-line-strong" />
            {TIERS.map((t) => (
              <Chip
                key={t.key}
                active={tier === t.key}
                onClick={() => setTier(tier === t.key ? null : t.key)}
              >
                {t.label}
              </Chip>
            ))}
          </>
        )}
      </div>

      {/* Approved/Dispatched buckets: API status filter is a Week-4 follow-up. */}
      {!isPendingView && (
        <p className="text-sm leading-6 text-ink-secondary">
          {view === "approved" ? "Approved" : "Dispatched"} history wires in Week 4 — it needs a{" "}
          <span className="font-mono">status</span> filter on{" "}
          <span className="font-mono">GET /actions</span> (currently pending-only).
        </p>
      )}

      {isPendingView && (
        <>
          {isLoading && <p className="text-sm text-ink-secondary">Loading queue…</p>}
          {isError && (
            <p className="text-sm text-risk-high-fg">
              Couldn’t load the queue: {(error as Error)?.message ?? "unknown error"}
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
        </>
      )}
    </div>
  );
}

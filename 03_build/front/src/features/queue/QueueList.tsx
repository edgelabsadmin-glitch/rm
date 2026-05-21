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
import { useSession } from "@/session/useSession";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { cn } from "@/lib/utils";
import { useActions } from "./hooks";
import { QueueCard } from "./QueueCard";
import type { QueueFilters } from "./types";

type View = "mine" | "overall" | "approved" | "dispatched";
const VIEWS: { id: View; label: string }[] = [
  { id: "mine", label: "My Queue" },
  { id: "overall", label: "Overall" },
  { id: "approved", label: "Approved" },
  { id: "dispatched", label: "Dispatched" },
];
const PENDING_VIEWS: View[] = ["mine", "overall"];
const TIERS = ["SMB", "Mid-Market", "Enterprise"] as const;

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
  const session = useSession();
  const reduce = useReducedMotion();
  const [view, setView] = useLocalStorage<View>("pulse.queue.view", "mine");
  const [tier, setTier] = useLocalStorage<string | null>("pulse.queue.tier", null);
  const isPendingView = PENDING_VIEWS.includes(view);

  const filters: QueueFilters = useMemo(
    () => ({
      rm_id: view === "mine" ? session.id : undefined,
      tier: tier ?? undefined,
    }),
    [view, tier, session.id],
  );

  const { data, isLoading, isError, error } = useActions(filters);
  const actions = data?.actions ?? [];

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Action Queue
        </h1>
        {isPendingView && <span className="text-xs text-ink-secondary">{actions.length} pending</span>}
      </div>

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
              <Chip key={t} active={tier === t} onClick={() => setTier(tier === t ? null : t)}>
                {t}
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
                  <QueueCard action={a} isAdmin={session.role === "admin"} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </>
      )}
    </div>
  );
}

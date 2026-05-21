/*
 * SPEC-035 — Action Queue list. Ranked cards from GET /actions (server ranks by
 * the Design-03 composite score; we render in returned order). Scope + tier filter
 * chips (persisted in localStorage, Q36). Fade-and-lift entrance + AnimatePresence
 * exit so a decided card animates out (Tier-0 §7; first surface to need exit motion).
 *
 * Scope note: GET /actions is pending-only, so "Approved"/"Dispatched" buckets from
 * Design 03 need a status filter on the spec-031 API (flagged) — Phase-1 ships the
 * My-Queue/Overall scope + tier filter that the API supports today.
 */
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";
import { useSession } from "@/session/useSession";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { cn } from "@/lib/utils";
import { useActions } from "./hooks";
import { QueueCard } from "./QueueCard";
import type { QueueFilters } from "./types";

type Scope = "mine" | "overall";
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
  const [scope, setScope] = useLocalStorage<Scope>("pulse.queue.scope", "mine");
  const [tier, setTier] = useLocalStorage<string | null>("pulse.queue.tier", null);

  const filters: QueueFilters = useMemo(
    () => ({
      rm_id: scope === "mine" ? session.id : undefined,
      tier: tier ?? undefined,
    }),
    [scope, tier, session.id],
  );

  const { data, isLoading, isError, error } = useActions(filters);
  const actions = data?.actions ?? [];

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold uppercase tracking-[0.18em] text-ink-secondary">
          Action Queue
        </h1>
        <span className="text-xs text-ink-secondary">{actions.length} pending</span>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Chip active={scope === "mine"} onClick={() => setScope("mine")}>
          My Queue
        </Chip>
        <Chip active={scope === "overall"} onClick={() => setScope("overall")}>
          Overall
        </Chip>
        <span className="mx-1 h-4 w-px bg-line-strong" />
        {TIERS.map((t) => (
          <Chip key={t} active={tier === t} onClick={() => setTier(tier === t ? null : t)}>
            {t}
          </Chip>
        ))}
      </div>

      {isLoading && <p className="text-sm text-ink-secondary">Loading queue…</p>}
      {isError && (
        <p className="text-sm text-risk-high-fg">
          Couldn’t load the queue: {(error as Error)?.message ?? "unknown error"}
        </p>
      )}
      {!isLoading && !isError && actions.length === 0 && (
        <p className="text-sm text-ink-secondary">
          Nothing waiting on you. Pulse will surface actions here as signals land.
        </p>
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
    </div>
  );
}

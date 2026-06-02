/*
 * SPEC-041 Step-8 — Constellation defensive states (loading / error / empty). Presentational,
 * centered in the viewport. Phase-1 derivation is synchronous so loading/error rarely surface,
 * but the components exist for the Phase-2 async pulse-api fetch (no silent failure, §6 #14).
 * Empty state covers a scope that resolves to zero accounts (RBAC scope-empty, spec 042).
 */
import { AlertTriangle, Radar } from "lucide-react";

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute inset-0 z-10 grid place-items-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-3 rounded-lg bg-surface-card p-6 text-center shadow-lg">
        {children}
      </div>
    </div>
  );
}

/** Brief brand-disc skeleton while graph data loads (Phase-2 async). */
export function ConstellationLoading() {
  return (
    <div className="absolute inset-0 z-10 grid place-items-center">
      <div className="flex flex-col items-center gap-3">
        <div
          className="h-16 w-16 animate-pulse rounded-full"
          style={{ background: "var(--color-brand-primary)" }}
        />
        <div className="text-xs text-ink-muted">Loading constellation…</div>
      </div>
    </div>
  );
}

/** Honest failure surface with a retry affordance. */
export function ConstellationError({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <Centered>
      <span
        className="grid h-9 w-9 place-items-center rounded-md"
        style={{ background: "var(--color-chip-risk-bg)", color: "var(--color-chip-risk-text)" }}
      >
        <AlertTriangle className="h-5 w-5" />
      </span>
      <div className="text-sm font-semibold text-ink-primary">Couldn't load constellation</div>
      <div className="text-xs text-ink-secondary">API error · {message ?? "unknown error"}</div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-md px-3 py-1.5 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
          style={{ border: "0.5px solid var(--color-line-strong)" }}
        >
          Retry
        </button>
      )}
    </Centered>
  );
}

/** Scope resolved to zero accounts (filter or RBAC scope empty). */
export function ConstellationEmpty({ onResetFilter }: { onResetFilter?: () => void }) {
  return (
    <Centered>
      <Radar className="h-8 w-8 text-ink-muted" />
      <div className="text-sm font-semibold text-ink-primary">No accounts in your view</div>
      <div className="text-xs text-ink-secondary">Check your filter or scope settings</div>
      {onResetFilter && (
        <button
          type="button"
          onClick={onResetFilter}
          className="mt-1 rounded-md px-3 py-1.5 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
          style={{ border: "0.5px solid var(--color-line-strong)" }}
        >
          Reset filter
        </button>
      )}
    </Centered>
  );
}

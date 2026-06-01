/*
 * SPEC-041 Step-6 — RM capacity-imbalance overlay (the second agentic overlay). Where the
 * cluster-pattern overlay (Step 5) shows cross-ACCOUNT patterns, this shows cross-RM load:
 * one RM carries more risk-weighted work than a teammate. Severity uses chip-WARNING tokens
 * (operational concern, not customer-facing churn). All numbers are composer-derived from
 * the canonical fixture; copy is generalized template language with no claims about cause —
 * the human interprets via Investigate (→ that RM's Action Queue).
 */
import { Scale } from "lucide-react";
import type { CapacityImbalanceCard } from "../composers/rm_capacity_composer";

export function RmCapacityImbalanceOverlay({
  card,
  x,
  y,
  onInvestigate,
}: {
  card: CapacityImbalanceCard;
  x: number;
  y: number;
  onInvestigate: (card: CapacityImbalanceCard) => void;
}) {
  return (
    <div
      className="pointer-events-auto absolute z-20 w-[280px] rounded-lg bg-surface-card p-3 shadow-lg"
      style={{
        left: x,
        top: y,
        transform: "translate(-50%, calc(-100% - 12px))",
        border: "0.5px solid var(--color-line-strong)",
      }}
      role="region"
      aria-label={`Capacity imbalance: ${card.topLoadedRmName} carrying significant book risk. Risk-weighted score ${card.topLoadedScore.toFixed(1)} vs ${card.comparisonRmName} at ${card.comparisonScore.toFixed(1)}, manager ${card.managerName}.`}
    >
      {/* Header: warning severity icon + CAPACITY IMBALANCE label. */}
      <div className="flex items-center gap-2">
        <span
          className="grid h-7 w-7 place-items-center rounded-md"
          style={{
            background: "var(--color-chip-warning-bg)",
            color: "var(--color-chip-warning-text)",
          }}
        >
          <Scale className="h-4 w-4" />
        </span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
          Capacity Imbalance
        </span>
      </div>

      {/* Body: title + summary + meta — all derived numbers, generalized phrasing. */}
      <div className="mt-2 text-[13px] font-medium leading-5 text-ink-primary">
        {card.topLoadedRmName} carrying significant book risk
      </div>
      <p className="mt-1 text-xs leading-5 text-ink-secondary">
        {card.topLoadedRmName} owns {card.topLoadedAccountCount} accounts with{" "}
        {card.topLoadedChurnExposureCount} in churn-state — risk-weighted score{" "}
        {card.topLoadedScore.toFixed(1)} vs team median.
      </p>
      <div className="mt-2 text-[11px] text-ink-muted">
        Compare: {card.comparisonRmName} at score {card.comparisonScore.toFixed(1)} · Manager:{" "}
        {card.managerName}
      </div>

      {/* Footer: outlined Investigate button → top-loaded RM's Action Queue. */}
      <button
        type="button"
        onClick={() => onInvestigate(card)}
        className="mt-3 rounded-md px-2.5 py-1 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
        style={{ border: "0.5px solid var(--color-line-strong)" }}
      >
        Investigate
      </button>
    </div>
  );
}

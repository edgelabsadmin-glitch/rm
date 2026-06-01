/*
 * ConstellationSidebar — action-items panel for the Constellation page.
 * Replaces the floating canvas overlays with a scrollable sidebar list,
 * following the same layout pattern as the Accounts QueueList sidebar.
 */
import { AlertTriangle, ArrowUpToLine, Scale, Radar } from "lucide-react";
import type { PatternCard } from "./demo_patterns";
import type { CapacityImbalanceCard } from "./composers/rm_capacity_composer";
import type { EscalationTierJumpCard } from "./composers/escalation_tier_jump_composer";

function AlertBadge({ n }: { n: number }) {
  if (!n) return null;
  return (
    <span className="ml-2 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-brand px-1.5 text-[10px] font-bold text-white">
      {n}
    </span>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="px-5 pb-1 pt-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-muted">{label}</p>
    </div>
  );
}

function InvestigateBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-3 rounded-md px-2.5 py-1 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
      style={{ border: "0.5px solid var(--color-line-strong)" }}
    >
      Investigate
    </button>
  );
}

// ── Pattern alert card ────────────────────────────────────────────────────────

function PatternItem({
  pattern,
  onInvestigate,
}: {
  pattern: PatternCard;
  onInvestigate: (p: PatternCard) => void;
}) {
  return (
    <div className="border-b border-line-subtle px-5 py-4 last:border-0">
      <div className="flex items-center gap-2">
        <span
          className="grid h-6 w-6 shrink-0 place-items-center rounded-md"
          style={{ background: "var(--color-chip-risk-bg)", color: "var(--color-chip-risk-text)" }}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
          Pattern Alert
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-ink-primary">{pattern.title}</p>
      <p className="mt-1 text-xs leading-5 text-ink-secondary">{pattern.summary}</p>
      <p className="mt-1 text-[11px] text-ink-muted">
        {pattern.support_account_ids.length} accounts affected
      </p>
      <InvestigateBtn onClick={() => onInvestigate(pattern)} />
    </div>
  );
}

// ── Capacity imbalance card ───────────────────────────────────────────────────

function CapacityItem({
  card,
  onInvestigate,
}: {
  card: CapacityImbalanceCard;
  onInvestigate: (c: CapacityImbalanceCard) => void;
}) {
  return (
    <div className="border-b border-line-subtle px-5 py-4 last:border-0">
      <div className="flex items-center gap-2">
        <span
          className="grid h-6 w-6 shrink-0 place-items-center rounded-md"
          style={{
            background: "var(--color-chip-warning-bg)",
            color: "var(--color-chip-warning-text)",
          }}
        >
          <Scale className="h-3.5 w-3.5" />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
          Capacity Imbalance
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-ink-primary">
        {card.topLoadedRmName} carrying significant book risk
      </p>
      <p className="mt-1 text-xs leading-5 text-ink-secondary">
        {card.topLoadedAccountCount} accounts · {card.topLoadedChurnExposureCount} in churn-state ·
        score {card.topLoadedScore.toFixed(1)}
      </p>
      <p className="mt-1 text-[11px] text-ink-muted">
        vs {card.comparisonRmName} at {card.comparisonScore.toFixed(1)} · Mgr: {card.managerName}
      </p>
      <InvestigateBtn onClick={() => onInvestigate(card)} />
    </div>
  );
}

// ── Escalation tier-jump card ─────────────────────────────────────────────────

function EscalationItem({
  card,
  onInvestigate,
}: {
  card: EscalationTierJumpCard;
  onInvestigate: (c: EscalationTierJumpCard) => void;
}) {
  const sev =
    card.newTier === "watch"
      ? { bg: "var(--color-chip-warning-bg)", text: "var(--color-chip-warning-text)" }
      : { bg: "var(--color-chip-risk-bg)", text: "var(--color-chip-risk-text)" };
  return (
    <div className="border-b border-line-subtle px-5 py-4 last:border-0">
      <div className="flex items-center gap-2">
        <span
          className="grid h-6 w-6 shrink-0 place-items-center rounded-md"
          style={{ background: sev.bg, color: sev.text }}
        >
          <ArrowUpToLine className="h-3.5 w-3.5" />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
          Tier Escalation
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-ink-primary">
        {card.accountName} → {card.newTier}
      </p>
      <p className="mt-1 text-xs leading-5 text-ink-secondary">
        {card.previousTier} → {card.newTier} · {card.reason}
      </p>
      <p className="mt-1 text-[11px] text-ink-muted">
        {card.hoursAgo}h ago · RM: {card.owningRmName}
      </p>
      <InvestigateBtn onClick={() => onInvestigate(card)} />
    </div>
  );
}

// ── Main sidebar ──────────────────────────────────────────────────────────────

export function ConstellationSidebar({
  patterns,
  capacityCards,
  escalationCards,
  onInvestigatePattern,
  onInvestigateCapacity,
  onInvestigateEscalation,
}: {
  patterns: PatternCard[];
  capacityCards: CapacityImbalanceCard[];
  escalationCards: EscalationTierJumpCard[];
  onInvestigatePattern: (p: PatternCard) => void;
  onInvestigateCapacity: (c: CapacityImbalanceCard) => void;
  onInvestigateEscalation: (c: EscalationTierJumpCard) => void;
}) {
  const total = patterns.length + capacityCards.length + escalationCards.length;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center border-b border-line-subtle px-5 py-4">
        <h2 className="text-sm font-semibold text-ink-primary">Action Items</h2>
        <AlertBadge n={total} />
      </div>

      {/* Scrollable content */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {total === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <Radar className="h-8 w-8 text-ink-muted" />
            <p className="text-sm text-ink-muted">No active alerts in this view</p>
          </div>
        )}

        {patterns.length > 0 && (
          <>
            <SectionHeader label="Patterns" />
            {patterns.map((p) => (
              <PatternItem key={p.id} pattern={p} onInvestigate={onInvestigatePattern} />
            ))}
          </>
        )}

        {capacityCards.length > 0 && (
          <>
            <SectionHeader label="Capacity" />
            {capacityCards.map((c) => (
              <CapacityItem key={c.id} card={c} onInvestigate={onInvestigateCapacity} />
            ))}
          </>
        )}

        {escalationCards.length > 0 && (
          <>
            <SectionHeader label="Escalations" />
            {escalationCards.map((c) => (
              <EscalationItem key={c.id} card={c} onInvestigate={onInvestigateEscalation} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

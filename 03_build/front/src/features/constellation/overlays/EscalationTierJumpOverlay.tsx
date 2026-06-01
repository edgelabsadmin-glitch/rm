/*
 * SPEC-041 Step-7 — escalation tier-jump overlay (the third agentic overlay). Per-ACCOUNT
 * temporal change: an account's composite health tier just jumped. Anchored directly at the
 * account node (the node IS the centroid). Severity color tracks the new tier (at-risk /
 * escalated → chip-risk; watch → chip-warning). On first render it pulses once (scale
 * 1→1.05→1, ~600ms) — the "a decision just happened" signal — then sits static, only
 * repositioning on zoom/pan. All copy is generalized + derived (real-data principle).
 */
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpToLine } from "lucide-react";
import type { EscalationTierJumpCard } from "../composers/escalation_tier_jump_composer";

function severityTokens(newTier: EscalationTierJumpCard["newTier"]) {
  // watch is the milder operational state; at-risk/escalated are customer-risk.
  if (newTier === "watch") {
    return { bg: "var(--color-chip-warning-bg)", text: "var(--color-chip-warning-text)" };
  }
  return { bg: "var(--color-chip-risk-bg)", text: "var(--color-chip-risk-text)" };
}

export function EscalationTierJumpOverlay({
  card,
  x,
  y,
  onInvestigate,
}: {
  card: EscalationTierJumpCard;
  x: number;
  y: number;
  onInvestigate: (card: EscalationTierJumpCard) => void;
}) {
  const reduce = useReducedMotion();
  const sev = severityTokens(card.newTier);
  return (
    <div
      className="pointer-events-none absolute z-20"
      style={{ left: x, top: y, transform: "translate(-50%, calc(-100% - 12px))" }}
    >
      <motion.div
        className="pointer-events-auto w-[260px] rounded-lg bg-surface-card p-3 shadow-lg"
        style={{ border: "0.5px solid var(--color-line-strong)", transformOrigin: "center bottom" }}
        // One-shot attention pulse on mount (skipped under reduced-motion).
        initial={reduce ? false : { scale: 1 }}
        animate={reduce ? {} : { scale: [1, 1.05, 1] }}
        transition={{ duration: 0.6, ease: "easeOut", times: [0, 0.5, 1] }}
        role="region"
        aria-label={`Tier escalation: ${card.accountName} escalated to ${card.newTier}. Moved from ${card.previousTier} to ${card.newTier}, ${card.hoursAgo} hours ago, owning RM ${card.owningRmName}.`}
      >
        {/* Header: tier-up severity icon + TIER ESCALATION eyebrow. */}
        <div className="flex items-center gap-2">
          <span
            className="grid h-7 w-7 place-items-center rounded-md"
            style={{ background: sev.bg, color: sev.text }}
          >
            <ArrowUpToLine className="h-4 w-4" />
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            Tier Escalation
          </span>
        </div>

        {/* Body: title + summary + meta — all derived. */}
        <div className="mt-2 text-[13px] font-medium leading-5 text-ink-primary">
          {card.accountName} escalated to {card.newTier}
        </div>
        <p className="mt-1 text-xs leading-5 text-ink-secondary">
          Health tier moved from {card.previousTier} → {card.newTier} · {card.reason}
        </p>
        <div className="mt-2 text-[11px] text-ink-muted">
          {card.hoursAgo}h ago · Owning RM: {card.owningRmName}
        </div>

        {/* Footer: outlined Investigate → Per-Account view. */}
        <button
          type="button"
          onClick={() => onInvestigate(card)}
          className="mt-3 rounded-md px-2.5 py-1 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
          style={{ border: "0.5px solid var(--color-line-strong)" }}
        >
          Investigate
        </button>
      </motion.div>
    </div>
  );
}

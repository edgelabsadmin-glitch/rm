/*
 * SPEC-041 Step-5 / SPEC-027 — first agentic overlay on the Constellation. An HTML card
 * absolutely positioned over the canvas at the centroid of an affected account cluster
 * (the parent computes screen coords via fgRef.graph2ScreenCoords and repositions on
 * tick/zoom/pan). Severity uses the chip-risk tokens; body sits on surface-card. The
 * "Investigate" button deep-links to the Action Queue filtered by pattern id (Step-7
 * wires the filter; QueueList ignores the unknown param gracefully for now).
 */
import { AlertTriangle } from "lucide-react";
import { DEMO_RMS } from "@/fixtures/demo_characters";
import type { PatternCard } from "../demo_patterns";

const rmName = (id: string) => DEMO_RMS.find((r) => r.id === id)?.name ?? id;

export function ClusterPatternOverlay({
  pattern,
  x,
  y,
  onInvestigate,
}: {
  pattern: PatternCard;
  x: number;
  y: number;
  onInvestigate: (pattern: PatternCard) => void;
}) {
  const accounts = pattern.support_account_ids.length;
  const owner = rmName(pattern.owning_rm_id);
  return (
    <div
      className="pointer-events-auto absolute z-20 w-[240px] rounded-lg bg-surface-card p-3 shadow-lg"
      style={{
        left: x,
        top: y,
        // Anchor the card above the cluster centroid.
        transform: "translate(-50%, calc(-100% - 12px))",
        border: "0.5px solid var(--color-line-strong)",
      }}
      role="region"
      aria-label={`Pattern alert: ${pattern.title}. Affects ${accounts} accounts, owning RM ${owner}.`}
    >
      {/* Header: severity icon (chip-risk tokens) + PATTERN ALERT label. */}
      <div className="flex items-center gap-2">
        <span
          className="grid h-7 w-7 place-items-center rounded-md"
          style={{
            background: "var(--color-chip-risk-bg)",
            color: "var(--color-chip-risk-text)",
          }}
        >
          <AlertTriangle className="h-4 w-4" />
        </span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
          Pattern Alert
        </span>
      </div>

      {/* Body: title + summary + meta. */}
      <div className="mt-2 text-[13px] font-medium leading-5 text-ink-primary">{pattern.title}</div>
      <p className="mt-1 text-xs leading-5 text-ink-secondary">{pattern.summary}</p>
      <div className="mt-2 text-[11px] text-ink-muted">
        Affects {accounts} accounts · Owning RM: {owner}
      </div>

      {/* Footer: outlined Investigate button. */}
      <button
        type="button"
        onClick={() => onInvestigate(pattern)}
        className="mt-3 rounded-md px-2.5 py-1 text-xs font-medium text-ink-secondary hover:bg-brand-ghost hover:text-brand"
        style={{ border: "0.5px solid var(--color-line-strong)" }}
      >
        Investigate
      </button>
    </div>
  );
}

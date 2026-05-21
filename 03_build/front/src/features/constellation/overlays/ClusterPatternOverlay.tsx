/*
 * SPEC-041 Step-5 / SPEC-027 — first agentic overlay on the Constellation. An HTML card
 * absolutely positioned over the canvas at the centroid of an affected account cluster
 * (the parent computes screen coords via fgRef.graph2ScreenCoords and repositions on
 * zoom/pan). Severity uses the chip-risk tokens; "Investigate" deep-links to the Action
 * Queue filtered by pattern id (Step-7 wires the filter; QueueList ignores it gracefully).
 */
import { AlertTriangle } from "lucide-react";
import { DEMO_RMS } from "@/fixtures/demo_characters";
import type { DemoPattern } from "../demo_patterns";

const rmNames = (ids: string[]) =>
  ids.map((id) => DEMO_RMS.find((r) => r.id === id)?.name ?? id).join(", ");

export function ClusterPatternOverlay({
  pattern,
  x,
  y,
  onInvestigate,
}: {
  pattern: DemoPattern;
  x: number;
  y: number;
  onInvestigate: (pattern: DemoPattern) => void;
}) {
  const accounts = pattern.support_account_ids.length;
  return (
    <div
      className="pointer-events-auto absolute z-20 w-[240px] rounded-lg border bg-surface-card p-3 shadow-lg"
      style={{
        left: x,
        top: y,
        // Anchor the card above the cluster centroid.
        transform: "translate(-50%, calc(-100% - 12px))",
        borderColor: "var(--color-line-strong)",
        borderWidth: "0.5px",
      }}
      role="status"
    >
      <div className="flex items-center gap-1.5">
        <span
          className="grid h-5 w-5 place-items-center rounded"
          style={{
            background: "var(--color-chip-risk-bg)",
            color: "var(--color-chip-risk-text)",
          }}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
        </span>
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: "var(--color-chip-risk-text)" }}
        >
          Pattern Alert
        </span>
      </div>

      <p className="mt-2 text-[13px] leading-5 text-ink-primary">{pattern.summary}</p>

      <div className="mt-2 text-xs text-ink-secondary">
        {accounts} accounts · {rmNames(pattern.owning_rm_ids)}
      </div>

      <button
        type="button"
        onClick={() => onInvestigate(pattern)}
        className="mt-2 text-xs font-medium text-ink-secondary underline-offset-2 hover:text-brand hover:underline"
      >
        Investigate →
      </button>
    </div>
  );
}

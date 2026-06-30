/*
 * MatrixPanel — the analysis-agent signal matrix for an account: priority,
 * fired signals (with severity + cited evidence), the LLM narrative, and a
 * priority-score-over-time sparkline from the dated history. Read-only.
 */
import { CollapsibleSection } from "@/features/account/CollapsibleSection";
import { useAccountMatrix, useAccountMatrixHistory } from "./hooks";
import { PriorityDot } from "./PriorityDot";
import type { FiredSignal, MatrixHistoryPoint } from "./types";

const SEV_STYLE: Record<string, string> = {
  high: "bg-rose-100 text-rose-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-sky-100 text-sky-700",
};

function SeverityTag({ severity }: { severity: FiredSignal["severity"] }) {
  const s = severity ?? "low";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${SEV_STYLE[s]}`}>
      {s}
    </span>
  );
}

function Sparkline({ points }: { points: MatrixHistoryPoint[] }) {
  if (points.length < 2) return null;
  // History comes newest-first; chart left→right oldest→newest.
  const series = [...points].reverse();
  const max = Math.max(...series.map((p) => p.priority_score), 1);
  const w = 120;
  const h = 28;
  const step = w / (series.length - 1);
  const d = series
    .map((p, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${(h - (p.priority_score / max) * h).toFixed(1)}`)
    .join(" ");
  return (
    <svg width={w} height={h} className="text-brand" aria-label="Priority over time">
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.5} />
    </svg>
  );
}

export function MatrixPanel({ accountId }: { accountId: string | null }) {
  const { data: matrix } = useAccountMatrix(accountId);
  const { data: history } = useAccountMatrixHistory(accountId);

  if (!matrix) return null;
  const fired = matrix.fired_signals.filter((s) => s.fired);

  return (
    <CollapsibleSection title="Signal matrix" defaultOpen>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <PriorityDot color={matrix.priority_color} priority={matrix.priority} showLabel />
          <div className="flex items-center gap-3">
            {history && history.length > 1 && <Sparkline points={history} />}
            <span className="text-xs text-ink-muted">
              {new Date(matrix.analyzed_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {matrix.state === "needs_review" && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Flagged for review — the analysis did not pass the evidence gate.
          </p>
        )}

        {fired.length === 0 ? (
          <p className="text-sm text-ink-secondary">No signals firing — account looks healthy.</p>
        ) : (
          <ul className="space-y-2">
            {fired.map((s) => (
              <li key={s.signal_id} className="flex items-start justify-between gap-2 text-sm">
                <span className="text-ink-primary">{s.signal_id}</span>
                <SeverityTag severity={s.severity} />
              </li>
            ))}
          </ul>
        )}

        {matrix.narrative && (
          <p className="border-t border-line-subtle pt-3 text-sm leading-relaxed text-ink-secondary">
            {matrix.narrative}
          </p>
        )}
      </div>
    </CollapsibleSection>
  );
}

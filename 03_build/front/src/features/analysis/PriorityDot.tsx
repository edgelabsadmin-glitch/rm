/*
 * PriorityDot — the analysis-agent priority color (red = highest, green = healthy)
 * as a small status dot. Self-contained color tokens so it reads consistently in
 * the account list and the constellation without depending on risk tokens.
 */
import { cn } from "@/lib/utils";
import type { Priority, PriorityColor } from "./types";

const DOT: Record<PriorityColor, string> = {
  red: "bg-rose-500",
  orange: "bg-orange-500",
  amber: "bg-amber-400",
  blue: "bg-sky-400",
  green: "bg-emerald-500",
};

const LABEL: Record<Priority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  healthy: "Healthy",
};

export function PriorityDot({
  color,
  priority,
  className,
  showLabel = false,
}: {
  color: PriorityColor;
  priority?: Priority;
  className?: string;
  showLabel?: boolean;
}) {
  const title = priority ? `Priority: ${LABEL[priority]}` : "Priority";
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} title={title}>
      <span className={cn("h-2.5 w-2.5 rounded-full", DOT[color] ?? DOT.green)} />
      {showLabel && priority && (
        <span className="text-xs font-medium text-ink-secondary">{LABEL[priority]}</span>
      )}
    </span>
  );
}

/** Rank for sorting — critical first, healthy last, unknown after healthy. */
export function priorityRank(p?: Priority | null): number {
  const order: Record<Priority, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
    healthy: 4,
  };
  return p ? order[p] : 5;
}

/*
 * SPEC-035 — RiskBadge (Tier-0 §8.2). Tier-colored status chip (High/Medium/Low),
 * heavier than a Pill (font-semibold) — a RiskBadge is a status, a Pill is a label.
 */
import { cn } from "@/lib/utils";

export type RiskLevel = "High" | "Medium" | "Low";

const STYLES: Record<RiskLevel, string> = {
  High: "bg-risk-high-bg text-risk-high-fg border-risk-high-border",
  Medium: "bg-risk-medium-bg text-risk-medium-fg border-risk-medium-border",
  Low: "bg-risk-low-bg text-risk-low-fg border-risk-low-border",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        STYLES[level],
      )}
    >
      {level}
    </span>
  );
}

/** Map an urgency string to a risk level for the card badge. */
export function urgencyToRisk(urgency: string | null): RiskLevel {
  if (urgency === "high" || urgency === "medium-high") return "High";
  if (urgency === "medium") return "Medium";
  return "Low";
}

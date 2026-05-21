/*
 * SPEC-037 — Signal vector (Tier-0 §8.9). 4 stacked bars: brand fill on a
 * surface-track rail. Axes from the per-account multi-axis sentiment vector (Q51).
 */
import { CollapsibleSection } from "./CollapsibleSection";
import type { SignalAxis } from "@/features/hero/fixtures";

export function SignalVectorPanel({ vector }: { vector: SignalAxis[] }) {
  return (
    <CollapsibleSection title="Signal vector">
      <div className="space-y-4">
        {vector.map((axis) => (
          <div key={axis.label}>
            <div className="mb-1 flex justify-between text-xs text-ink-secondary">
              <span>{axis.label}</span>
              <span>{axis.pct}%</span>
            </div>
            <div className="h-2 rounded-full bg-surface-track">
              <div className="h-2 rounded-full bg-brand" style={{ width: `${axis.pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}

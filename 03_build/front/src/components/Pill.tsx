/*
 * SPEC-035 — Pill (Tier-0 §8.1). Tiny status chip. Active (purple-tinted) or
 * neutral. Queue cards use the neutral variant for the owner state.
 */
import { cn } from "@/lib/utils";

export function Pill({
  children,
  active = false,
  className,
}: {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
        active
          ? "border-brand-edge bg-brand-muted text-brand"
          : "border-line-strong bg-surface-card text-ink-secondary",
        className,
      )}
    >
      {children}
    </span>
  );
}

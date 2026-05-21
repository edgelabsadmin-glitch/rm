/*
 * SPEC-040 — Trust-layer callout (Tier-0 §8.13). White card, brand-soft border,
 * ShieldCheck in brand, calm secondary body. Used for the CEO View "What I'd ask
 * of you" section (Design 08) and the Action Queue footer (Design 03).
 */
import { ShieldCheck } from "lucide-react";

export function TrustLayerCallout({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-brand-soft bg-surface-card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
        <ShieldCheck className="h-4 w-4 text-brand" />
        {title}
      </div>
      <div className="mt-2 text-xs leading-5 text-ink-secondary">{children}</div>
    </div>
  );
}

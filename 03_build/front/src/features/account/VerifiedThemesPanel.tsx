/*
 * SPEC-037 — Verified themes (Tier-0 §8.10). Tinted-row list with a brand check
 * icon. Theme strings may carry inline-tag voice (§10), so render via the renderer.
 */
import { CheckCircle2 } from "lucide-react";
import { InlineTags } from "@/lib/inline_tags";
import { CollapsibleSection } from "./CollapsibleSection";

export function VerifiedThemesPanel({ themes }: { themes: string[] }) {
  return (
    <CollapsibleSection title="Verified themes">
      <div className="space-y-3">
        {themes.map((theme) => (
          <div
            key={theme}
            className="flex items-start gap-3 rounded-2xl bg-surface-tinted-row p-3"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
            <div className="text-sm leading-5 text-ink-primary">
              <InlineTags text={theme} />
            </div>
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}

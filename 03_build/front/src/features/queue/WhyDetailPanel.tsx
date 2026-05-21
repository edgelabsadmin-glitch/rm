/*
 * SPEC-035 — the expanded "why" (Design 03 §"Per-item explainability"). Presentational:
 * full inline-tag reasoning (Tier-0 §10), provenance episodes (clickable), and the
 * firing skill (admin-only — hidden from non-admins per the white-label distinction).
 * The Approve/Modify/Reject controls live in QueueCard, not here.
 */
import { FileText, Sparkles } from "lucide-react";
import { InlineTags } from "@/lib/inline_tags";
import type { ActionDTO } from "./types";

export function WhyDetailPanel({ action, isAdmin }: { action: ActionDTO; isAdmin: boolean }) {
  return (
    <div className="mt-3 space-y-4 border-t border-line-subtle pt-3">
      {action.why_detail && (
        <div className="text-sm leading-6 text-ink-primary">
          <InlineTags text={action.why_detail} />
        </div>
      )}

      {action.source_episodes.length > 0 && (
        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-ink-secondary">
            <FileText className="h-3.5 w-3.5" /> Provenance
          </div>
          <ul className="space-y-1">
            {action.source_episodes.map((ep) => (
              <li key={ep} className="truncate font-mono text-xs text-ink-secondary">
                {ep}
              </li>
            ))}
          </ul>
        </div>
      )}

      {isAdmin && action.skill_id && (
        <div className="flex items-center gap-1.5 text-xs text-ink-muted">
          <Sparkles className="h-3.5 w-3.5" />
          Skill: <span className="font-mono">{action.skill_id}</span>
        </div>
      )}
    </div>
  );
}

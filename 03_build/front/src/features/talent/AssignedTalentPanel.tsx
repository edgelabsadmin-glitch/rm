/* Assigned talent for an account — a list of associates with their analysis
 * priority color. Clicking a talent opens the detail drawer. */
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { CollapsibleSection } from "@/features/account/CollapsibleSection";
import { PriorityDot } from "@/features/analysis/PriorityDot";
import { useAccountTalent } from "./hooks";
import { TalentDetailDrawer } from "./TalentDetailDrawer";

export function AssignedTalentPanel({ accountId }: { accountId: string | null }) {
  const { data: talent, isLoading } = useAccountTalent(accountId);
  const [openId, setOpenId] = useState<string | null>(null);

  const rows = talent ?? [];
  const activeCount = rows.filter((t) => t.stage === "Active").length;

  return (
    <CollapsibleSection title={`Assigned talent${rows.length ? ` (${activeCount} active)` : ""}`}>
      {isLoading ? (
        <p className="text-sm text-ink-muted">Loading talent…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-muted">No talent assigned to this account.</p>
      ) : (
        <ul className="divide-y divide-line-subtle">
          {rows.map((t) => (
            <li key={t.associate_id}>
              <button
                onClick={() => setOpenId(t.associate_id)}
                className="flex w-full items-center justify-between gap-3 py-2.5 text-left first:pt-0"
              >
                <div className="flex min-w-0 items-center gap-2">
                  {t.priority_color ? (
                    <PriorityDot color={t.priority_color} priority={t.priority ?? undefined} />
                  ) : (
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-surface-track" />
                  )}
                  <span className="truncate text-sm font-medium text-ink-primary">
                    {t.name ?? t.associate_id}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-xs text-ink-muted">{t.stage ?? "—"}</span>
                  <ChevronRight className="h-4 w-4 text-ink-muted" />
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      <TalentDetailDrawer talentId={openId} onClose={() => setOpenId(null)} />
    </CollapsibleSection>
  );
}

/* Slide-over drawer for a single talent: profile + analysis signals + their
 * emails + the account's recent meetings (talent-level meetings aren't tracked,
 * so the account meetings are shown as context). */
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { InlineTags } from "@/lib/inline_tags";
import { PriorityDot } from "@/features/analysis/PriorityDot";
import { useTalentMatrix } from "@/features/analysis/hooks";
import { useMeetings } from "@/features/account/hooks";
import { useTalent, useTalentEmails } from "./hooks";
import { EmailList } from "./EmailList";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line-subtle px-5 py-4">
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-ink-secondary">
        {title}
      </h4>
      {children}
    </div>
  );
}

export function TalentDetailDrawer({
  talentId,
  onClose,
}: {
  talentId: string | null;
  onClose: () => void;
}) {
  const { data: talent } = useTalent(talentId);
  const { data: matrix } = useTalentMatrix(talentId);
  const { data: emails } = useTalentEmails(talentId);
  const { data: meetings } = useMeetings(talent?.account_id ?? null);

  if (!talentId) return null;
  const fired = (matrix?.fired_signals ?? []).filter((s) => s.fired);

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* backdrop */}
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
      />
      <aside className="relative flex h-full w-full max-w-md flex-col overflow-y-auto bg-surface-card shadow-2xl">
        <div className="flex items-start justify-between gap-3 px-5 pb-4 pt-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {talent?.priority_color && (
                <PriorityDot color={talent.priority_color} priority={talent.priority ?? undefined} />
              )}
              <h3 className="truncate text-lg font-semibold text-ink-primary">
                {talent?.name ?? "Talent"}
              </h3>
            </div>
            <p className="mt-1 text-xs text-ink-secondary">
              {talent?.stage ?? "—"}
              {talent?.account_name ? ` · ${talent.account_name}` : ""}
              {talent?.tier ? ` · ${talent.tier}` : ""}
            </p>
            {talent?.email && <p className="mt-0.5 text-xs text-ink-muted">{talent.email}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-ink-muted hover:bg-surface-track hover:text-ink-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <Section title="Signals">
          {fired.length === 0 ? (
            <p className="text-sm text-ink-secondary">No signals firing — looks healthy.</p>
          ) : (
            <ul className="space-y-2">
              {fired.map((s) => (
                <li key={s.signal_id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 break-words font-mono text-xs text-ink-primary">
                    {s.signal_id}
                  </span>
                  <span className="shrink-0 rounded-full bg-surface-track px-2 py-0.5 text-[10px] font-semibold uppercase text-ink-secondary">
                    {s.severity ?? "—"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {matrix?.narrative && (
            <div className="mt-3 overflow-hidden break-words text-sm leading-relaxed text-ink-secondary">
              <InlineTags text={matrix.narrative} />
            </div>
          )}
        </Section>

        <Section title="Emails">
          <EmailList
            empty="No emails from this talent."
            emails={(emails ?? []).map((e) => ({
              id: e.email_id,
              subject: e.subject,
              body: e.body,
              received_at: e.received_at,
            }))}
          />
        </Section>

        <Section title="Account meetings">
          {(meetings ?? []).length === 0 ? (
            <p className="text-sm text-ink-muted">No meetings on record for the account.</p>
          ) : (
            <ul className="space-y-2">
              {(meetings ?? []).slice(0, 6).map((m) => (
                <li key={m.episode_id} className="text-sm">
                  <span className="text-ink-primary">{m.subject ?? "Untitled meeting"}</span>
                  <span className="ml-2 text-xs capitalize text-ink-muted">{m.source}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </aside>
    </div>,
    document.body,
  );
}

/* Reusable expandable email list — used by the account emails dropdown and the
 * talent detail drawer. Click a row to read the full body. */
import { useState } from "react";
import { CalendarDays, ChevronDown, ChevronUp, Mail } from "lucide-react";

export interface EmailRow {
  id: string;
  subject: string | null;
  body: string | null;
  received_at: string | null;
  from?: string | null;
  kind?: string | null; // 'client' | 'talent'
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function EmailList({ emails, empty }: { emails: EmailRow[]; empty?: string }) {
  const [openId, setOpenId] = useState<string | null>(null);
  if (emails.length === 0) {
    return <p className="text-sm text-ink-muted">{empty ?? "No emails on record."}</p>;
  }
  return (
    <ul className="divide-y divide-line-subtle">
      {emails.map((e) => {
        const open = openId === e.id;
        return (
          <li key={e.id} className="py-3 first:pt-0 last:pb-0">
            <button
              onClick={() => setOpenId(open ? null : e.id)}
              className="flex w-full items-start justify-between gap-3 text-left"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <Mail className="h-3 w-3 shrink-0 text-brand" />
                  <p className="truncate text-sm font-medium text-ink-primary">
                    {e.subject || "(no subject)"}
                  </p>
                  {e.kind && (
                    <span className="rounded-full bg-surface-track px-1.5 py-0.5 text-[10px] font-medium capitalize text-ink-secondary">
                      {e.kind}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-ink-muted">
                  {e.from && <span className="truncate">{e.from}</span>}
                  <span className="flex items-center gap-1">
                    <CalendarDays className="h-3 w-3" />
                    {fmtDate(e.received_at)}
                  </span>
                </div>
              </div>
              {open ? (
                <ChevronUp className="h-4 w-4 shrink-0 text-ink-muted" />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0 text-ink-muted" />
              )}
            </button>
            {open && (
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink-secondary">
                {e.body || "(empty body)"}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

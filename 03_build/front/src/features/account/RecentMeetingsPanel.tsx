/*
 * Meeting history for the selected account — Chorus + Zoom.
 * Fetches from GET /accounts/{id}/meetings and renders a source-tagged timeline.
 */
import { CalendarDays, Clock, ExternalLink, Mic, Video } from "lucide-react";
import { CollapsibleSection } from "./CollapsibleSection";
import { useMeetings } from "./hooks";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";

function fmtDate(iso: string | null): string {
  if (!iso) return "Unknown date";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function fmtDuration(mins: number | null): string | null {
  if (!mins) return null;
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function RecentMeetingsPanel() {
  const { selectedAccountId } = useSelectedAccount();
  const { data: meetings, isLoading } = useMeetings(selectedAccountId);

  return (
    <CollapsibleSection title="Recent meetings">
      {isLoading && <p className="text-sm text-ink-muted">Loading meetings…</p>}
      {!isLoading && (!meetings || meetings.length === 0) && (
        <p className="text-sm text-ink-muted">No meetings on record for this account.</p>
      )}
      {!isLoading && meetings && meetings.length > 0 && (
        <ul className="divide-y divide-line-subtle">
          {meetings.map((m) => (
            <li key={m.episode_id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    {m.source === "zoom" ? (
                      <Video className="h-3 w-3 shrink-0 text-blue-500" />
                    ) : (
                      <Mic className="h-3 w-3 shrink-0 text-brand" />
                    )}
                    <p className="truncate text-sm font-medium text-ink-primary">
                      {m.subject ?? "Untitled meeting"}
                    </p>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-ink-muted">
                    <span className="flex items-center gap-1">
                      <CalendarDays className="h-3 w-3" />
                      {fmtDate(m.source_timestamp)}
                    </span>
                    {fmtDuration(m.duration_mins) && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {fmtDuration(m.duration_mins)}
                      </span>
                    )}
                    <span className="capitalize text-ink-muted/60">{m.source}</span>
                  </div>
                </div>
                {m.source_url && (
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 text-ink-muted hover:text-brand"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </CollapsibleSection>
  );
}

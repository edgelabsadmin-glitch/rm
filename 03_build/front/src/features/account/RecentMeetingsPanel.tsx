/*
 * Meeting history for the selected account — Chorus + Zoom.
 * Fetches from GET /accounts/{id}/meetings and renders a source-tagged timeline.
 * Click a row to expand transcript and recording link.
 */
import { useState } from "react";
import { CalendarDays, ChevronDown, ChevronUp, Clock, ExternalLink, Mic, Video } from "lucide-react";
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
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <CollapsibleSection title="Recent meetings">
      {isLoading && <p className="text-sm text-ink-muted">Loading meetings…</p>}
      {!isLoading && (!meetings || meetings.length === 0) && (
        <p className="text-sm text-ink-muted">No meetings on record for this account.</p>
      )}
      {!isLoading && meetings && meetings.length > 0 && (
        <ul className="divide-y divide-line-subtle">
          {meetings.map((m) => {
            const isExpanded = expandedId === m.episode_id;
            return (
              <li key={m.episode_id} className="py-3 first:pt-0 last:pb-0">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : m.episode_id)}
                  className="flex w-full items-start justify-between gap-3 text-left"
                >
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
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 shrink-0 text-ink-muted" />
                  ) : (
                    <ChevronDown className="h-4 w-4 shrink-0 text-ink-muted" />
                  )}
                </button>

                {isExpanded && (
                  <div className="mt-3 space-y-3">
                    {m.source_url && (
                      <a
                        href={m.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-md bg-brand/10 px-3 py-1.5 text-sm font-medium text-brand hover:bg-brand/20"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        Watch Recording
                      </a>
                    )}
                    <div className="rounded-md border border-line-subtle bg-surface-subtle p-3">
                      {m.transcript ? (
                        <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap font-sans text-xs leading-relaxed text-ink-secondary">
                          {m.transcript}
                        </pre>
                      ) : (
                        <p className="text-xs text-ink-muted">No transcript available for this meeting.</p>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </CollapsibleSection>
  );
}

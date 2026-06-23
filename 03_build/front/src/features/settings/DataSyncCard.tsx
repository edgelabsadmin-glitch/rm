import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api, type SyncStatusDTO } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";

const SYNC_KEY = ["admin", "sync-status"] as const;

/**
 * Admin-only card: a "Sync now" button that triggers the full data refresh (the
 * same Salesforce / Chorus / Zoom syncs the 12-hour loops run) and shows live
 * progress as a percentage. Polls the status endpoint every ~1.2s while running.
 */
export function DataSyncCard() {
  const user = useUser();
  const qc = useQueryClient();

  const { data: status } = useQuery({
    queryKey: SYNC_KEY,
    queryFn: () => api.getSyncStatus(user) as Promise<SyncStatusDTO>,
    refetchInterval: (query) =>
      query.state.data?.state === "running" ? 1200 : false,
  });

  const start = useMutation({
    mutationFn: () => api.startSync(user),
    onSuccess: (s) => {
      qc.setQueryData(SYNC_KEY, s);
      qc.invalidateQueries({ queryKey: SYNC_KEY });
    },
  });

  const running = status?.state === "running" || start.isPending;
  const percent = running ? (status?.percent ?? 0) : status?.state ? 100 : 0;
  const showBar = running || status?.state === "done" || status?.state === "error";

  const statusLine = (() => {
    if (start.isPending && !status) return "Starting…";
    if (running) return status?.phase ? `${status.phase}…` : "Syncing…";
    if (status?.state === "done") return "Last sync completed successfully.";
    if (status?.state === "error") return "Last sync finished with errors.";
    return "Pulls the latest Salesforce accounts & contacts, Chorus and Zoom meetings.";
  })();

  return (
    <div className="rounded-2xl border border-line-subtle bg-surface-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
            Data sync
          </h2>
          <p className="mt-1 text-xs text-ink-secondary">{statusLine}</p>
        </div>
        <button
          type="button"
          onClick={() => start.mutate()}
          disabled={running}
          className="flex items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />
          {running ? "Syncing…" : "Sync now"}
        </button>
      </div>

      {showBar && (
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between text-xs text-ink-secondary">
            <span>{running ? status?.phase ?? "Working…" : status?.phase ?? ""}</span>
            <span className="font-mono">{percent}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-tinted-row">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                status?.state === "error" ? "bg-risk-high-fg" : "bg-brand"
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
          {status?.state === "error" && status.detail && (
            <p className="mt-2 text-[11px] leading-4 text-risk-high-fg">{status.detail}</p>
          )}
        </div>
      )}
    </div>
  );
}

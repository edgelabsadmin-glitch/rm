/*
 * SPEC-038 — headless controller that drives the Pulse Bar from live queue state.
 * Mounted once in the shell so the bar reflects agent activity on EVERY route
 * (§8.14 "lives on every screen"). Polls the caller's My-Queue every 10s:
 *   - sets `processing` while a fetch is in flight,
 *   - keeps the header badge count live,
 *   - fires a heartbeat when new action_ids appear (id-diff vs the previous poll).
 */
import { useEffect, useRef } from "react";
import { usePulseState } from "@/components/PulseStateProvider";
import { useActions } from "@/features/queue/hooks";
import { useAuth } from "@/lib/auth/AuthContext";

export function PulseBarController() {
  const { user } = useAuth();
  const { setQueueCount, setProcessing, notifyNewActions } = usePulseState();
  const { data, isFetching } = useActions({ rm_id: user.id });
  const prevIds = useRef<Set<string> | null>(null);

  useEffect(() => {
    setProcessing(isFetching);
  }, [isFetching, setProcessing]);

  useEffect(() => {
    if (!data) return;
    const ids = new Set(data.actions.map((a) => a.action_id));
    setQueueCount(ids.size);
    if (prevIds.current !== null) {
      let added = 0;
      ids.forEach((id) => {
        if (!prevIds.current!.has(id)) added += 1;
      });
      if (added > 0) notifyNewActions(added); // one heartbeat per poll-batch with arrivals
    }
    prevIds.current = ids;
  }, [data, setQueueCount, notifyNewActions]);

  return null;
}

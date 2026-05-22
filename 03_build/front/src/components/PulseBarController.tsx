/*
 * SPEC-038 — headless controller that drives the Pulse Bar from live queue state.
 * Mounted once in the shell so the bar reflects agent activity on EVERY route
 * (§8.14 "lives on every screen"). Polls the caller's My-Queue every 10s:
 *   - sets `processing` while a fetch is in flight,
 *   - keeps the header badge count live,
 *   - fires a heartbeat when new action_ids appear (id-diff vs the previous poll).
 */
import { useEffect, useMemo, useRef } from "react";
import { usePulseState } from "@/components/PulseStateProvider";
import { useActions } from "@/features/queue/hooks";
import { applyStatusFilter, scopeAndRefineCards } from "@/features/queue/queue_scope";
import { useAuth } from "@/lib/auth/AuthContext";

export function PulseBarController() {
  const { user } = useAuth();
  const { setQueueCount, setProcessing, notifyNewActions } = usePulseState();
  // SPEC-042 Step-5 follow-up (Q2): the header badge reflects the caller's ROLE SCOPE, not
  // just their own rm_id — so a Manager sees their team total. Fetch the role book (no rm_id
  // filter), narrow to scope, then count only PENDING (actionable) cards — approved cards
  // shouldn't inflate the "queue" badge.
  const { data, isFetching } = useActions({});
  const prevIds = useRef<Set<string> | null>(null);

  const scoped = useMemo(
    () => applyStatusFilter(scopeAndRefineCards(data?.actions ?? [], user.role, user.id), "active"),
    [data, user.role, user.id],
  );

  useEffect(() => {
    setProcessing(isFetching);
  }, [isFetching, setProcessing]);

  useEffect(() => {
    if (!data) return;
    const ids = new Set(scoped.map((a) => a.action_id));
    setQueueCount(ids.size);
    if (prevIds.current !== null) {
      let added = 0;
      ids.forEach((id) => {
        if (!prevIds.current!.has(id)) added += 1;
      });
      if (added > 0) notifyNewActions(added); // one heartbeat per poll-batch with arrivals
    }
    prevIds.current = ids;
  }, [data, scoped, setQueueCount, notifyNewActions]);

  return null;
}

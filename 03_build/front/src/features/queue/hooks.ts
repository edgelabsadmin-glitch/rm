/*
 * SPEC-035 — React Query hooks for the Action Queue. Server state only (audit D7).
 * Mutations invalidate the list so a decided card leaves the pending set; the
 * pending count is mirrored into PulseStateProvider so the header badge stays live
 * (Tier-0 §8.14 "badge count is live").
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useSession } from "@/session/useSession";
import type { ActionsResponse, QueueFilters } from "./types";

const QUEUE_KEY = ["actions"] as const;

// Phase-1 transport: 10s polling (SSE/WebSocket deferred to v1.5+ #23). The
// PulseBarController owns count + new-card detection off this same query.
export const POLL_MS = 10_000;

export function useActions(filters: QueueFilters = {}) {
  const session = useSession();
  return useQuery({
    queryKey: [...QUEUE_KEY, filters],
    queryFn: () => api.listActions(session, { ...filters, limit: 200 }),
    refetchInterval: POLL_MS,
  });
}

export function useActionDetail(id: string | null) {
  const session = useSession();
  return useQuery({
    queryKey: [...QUEUE_KEY, "detail", id],
    queryFn: () => api.getAction(session, id!),
    enabled: !!id,
  });
}

function useInvalidateQueue() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: QUEUE_KEY });
}

export function useApprove() {
  const session = useSession();
  const invalidate = useInvalidateQueue();
  return useMutation({
    mutationFn: (id: string) => api.approve(session, id),
    onSuccess: invalidate,
  });
}

export function useModify() {
  const session = useSession();
  const invalidate = useInvalidateQueue();
  return useMutation({
    mutationFn: ({ id, diff }: { id: string; diff: Record<string, unknown> }) =>
      api.modify(session, id, diff),
    onSuccess: invalidate,
  });
}

export function useReject() {
  const session = useSession();
  const invalidate = useInvalidateQueue();
  return useMutation({
    mutationFn: ({ id, reason, freeText }: { id: string; reason: string; freeText?: string }) =>
      api.reject(session, id, reason, freeText),
    onSuccess: invalidate,
  });
}

export type { ActionsResponse };

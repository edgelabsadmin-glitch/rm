import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";
import type { MatrixSummary } from "./types";

const ANALYSIS_KEY = ["analysis"] as const;

/** Latest priority per account, keyed by account_id — one call for the whole list. */
export function useAccountMatrices() {
  const user = useUser();
  return useQuery({
    queryKey: [...ANALYSIS_KEY, "account-matrices"],
    queryFn: async () => {
      const rows = await api.getAccountMatrices(user);
      const map = new Map<string, MatrixSummary>();
      for (const r of rows) map.set(r.entity_id, r);
      return map;
    },
    staleTime: 5 * 60_000,
  });
}

export function useAccountMatrix(accountId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...ANALYSIS_KEY, "account", accountId],
    queryFn: () => api.getAccountMatrix(user, accountId!),
    enabled: !!accountId,
    staleTime: 5 * 60_000,
  });
}

export function useAccountMatrixHistory(accountId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...ANALYSIS_KEY, "account", accountId, "history"],
    queryFn: () => api.getAccountMatrixHistory(user, accountId!),
    enabled: !!accountId,
    staleTime: 5 * 60_000,
  });
}

export function useTalentMatrix(talentId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...ANALYSIS_KEY, "talent", talentId],
    queryFn: () => api.getTalentMatrix(user, talentId!),
    enabled: !!talentId,
    staleTime: 5 * 60_000,
  });
}

export function useAnalysisStatus(enabled = true) {
  const user = useUser();
  return useQuery({
    queryKey: [...ANALYSIS_KEY, "status"],
    queryFn: () => api.getAnalysisStatus(user),
    enabled,
    refetchInterval: (query) =>
      query.state.data?.state === "running" ? 3_000 : false,
  });
}

export function useStartAnalysisBackfill() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.startAnalysisBackfill(user),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...ANALYSIS_KEY, "status"] }),
  });
}

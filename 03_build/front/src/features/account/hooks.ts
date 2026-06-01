import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useSession } from "@/session/useSession";

const ACCOUNTS_KEY = ["accounts"] as const;

export function useAccounts(params: { tier?: string; rm_id?: string } = {}) {
  const session = useSession();
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, params],
    queryFn: () => api.listAccounts(session, params),
    staleTime: 60_000,
  });
}

export function useAccountHealth(accountId: string | null) {
  const session = useSession();
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, "health", accountId],
    queryFn: () => api.getAccountHealth(session, accountId!),
    enabled: !!accountId,
    staleTime: 60_000,
  });
}

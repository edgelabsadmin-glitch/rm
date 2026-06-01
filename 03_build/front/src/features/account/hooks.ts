import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";

const ACCOUNTS_KEY = ["accounts"] as const;

export function useAccounts(params: { tier?: string; rm_id?: string; rm_ids?: string; page_size?: number } = {}) {
  const user = useUser();
  const merged = { page_size: 200, ...params };
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, merged],
    queryFn: () => api.listAccounts(user, merged),
    staleTime: 60_000,
  });
}

export function useAccountHealth(accountId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, "health", accountId],
    queryFn: () => api.getAccountHealth(user, accountId!),
    enabled: !!accountId,
    staleTime: 60_000,
  });
}

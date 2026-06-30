import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";

const TALENT_KEY = ["talent"] as const;

export function useAccountTalent(accountId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...TALENT_KEY, "account", accountId],
    queryFn: () => api.getAccountTalent(user, accountId!),
    enabled: !!accountId,
    staleTime: 60_000,
  });
}

export function useAccountEmails(accountId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...TALENT_KEY, "account-emails", accountId],
    queryFn: () => api.getAccountEmails(user, accountId!),
    enabled: !!accountId,
    staleTime: 60_000,
  });
}

export function useTalent(talentId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...TALENT_KEY, "detail", talentId],
    queryFn: () => api.getTalent(user, talentId!),
    enabled: !!talentId,
    staleTime: 60_000,
  });
}

export function useTalentEmails(talentId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...TALENT_KEY, "emails", talentId],
    queryFn: () => api.getTalentEmails(user, talentId!),
    enabled: !!talentId,
    staleTime: 60_000,
  });
}

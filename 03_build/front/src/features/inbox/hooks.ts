import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";
import type { InboxListDTO, InboxEmailDetailDTO, ReplyTone } from "./types";

const INBOX_KEY = ["inbox"] as const;

export function useInbox() {
  const user = useUser();
  return useQuery({
    queryKey: [...INBOX_KEY, "list"],
    queryFn: () => api.listInbox(user) as Promise<InboxListDTO>,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useInboxEmail(emailId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...INBOX_KEY, "detail", emailId],
    queryFn: () => api.getInboxEmail(user, emailId!) as Promise<InboxEmailDetailDTO>,
    enabled: !!emailId,
    staleTime: 0,
  });
}

export function useSaveDraft() {
  const user = useUser();
  return useMutation({
    mutationFn: ({ emailId, text }: { emailId: string; text: string }) =>
      api.saveInboxDraft(user, emailId, text),
  });
}

export function useRegenerate() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ emailId, tone }: { emailId: string; tone?: ReplyTone }) =>
      api.regenerateInboxReply(user, emailId, tone),
    onSuccess: (_d, vars) =>
      qc.invalidateQueries({ queryKey: [...INBOX_KEY, "detail", vars.emailId] }),
  });
}

export function useSendReply() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ emailId, text }: { emailId: string; text: string }) =>
      api.sendInboxReply(user, emailId, text),
    onSuccess: () => qc.invalidateQueries({ queryKey: INBOX_KEY }),
  });
}

export function useDismiss() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (emailId: string) => api.dismissInboxEmail(user, emailId),
    onSuccess: () => qc.invalidateQueries({ queryKey: INBOX_KEY }),
  });
}

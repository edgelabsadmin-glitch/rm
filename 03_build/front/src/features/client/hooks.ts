import { useQuery, useQueryClient } from "@tanstack/react-query";
import { clientApi, type ClientConversation, type ClientMessage } from "@/lib/client-api";

export function useClientConversations() {
  return useQuery({
    queryKey: ["client", "conversations"],
    queryFn: () => clientApi.listConversations(),
    staleTime: 0,
  });
}

export function useClientMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ["client", "messages", conversationId],
    queryFn: () => clientApi.getMessages(conversationId!),
    enabled: !!conversationId,
    staleTime: 0,
  });
}

export function useInvalidateClientConversations() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["client", "conversations"] });
}

export type { ClientConversation, ClientMessage };

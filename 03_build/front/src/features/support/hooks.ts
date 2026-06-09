import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";

export interface ConversationItem {
  conversation_id: string;
  title: string;
  updated_at: string;
}

export interface SupportMessageItem {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls: Record<string, unknown>[] | null;
  created_at: string;
}

export function useConversations() {
  const user = useUser();
  return useQuery({
    queryKey: ["support", "conversations"],
    queryFn: () => api.listConversations(user) as Promise<ConversationItem[]>,
    staleTime: 0,
  });
}

export function useMessages(conversationId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: ["support", "messages", conversationId],
    queryFn: () =>
      api.getConversationMessages(user, conversationId!) as Promise<SupportMessageItem[]>,
    enabled: !!conversationId,
    staleTime: 0,
  });
}

export function useInvalidateConversations() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["support", "conversations"] });
}

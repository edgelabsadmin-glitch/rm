import { useState, useRef, useEffect, useCallback } from "react";
import { Navigate } from "react-router-dom";
import {
  Send,
  Bot,
  User,
  Loader2,
  Plus,
  Trash2,
  Sparkles,
  LogOut,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { clientApi, getClientSession, type ClientConversation } from "@/lib/client-api";
import { useClientAuth } from "./ClientAuthContext";
import {
  useClientConversations,
  useClientMessages,
  useInvalidateClientConversations,
} from "./hooks";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
}

let _idCounter = 0;
function nextId() {
  return String(++_idCounter);
}

function ConversationRow({
  conv,
  active,
  onSelect,
  onDelete,
}: {
  conv: ClientConversation;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition",
        active
          ? "bg-brand/10 text-brand"
          : "text-ink-secondary hover:bg-surface-sidebar hover:text-ink-primary",
      )}
      onClick={onSelect}
    >
      <span className="flex-1 truncate">{conv.title}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="ml-1 shrink-0 text-ink-muted opacity-0 transition hover:text-red-500 group-hover:opacity-100"
        aria-label="Delete conversation"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function ClientChatPage() {
  const { me, loading, logout } = useClientAuth();
  const qc = useQueryClient();
  const invalidateConversations = useInvalidateClientConversations();

  const { data: conversations = [] } = useClientConversations();
  const [activeId, setActiveId] = useState<string | null>(null);
  const { data: dbMessages } = useClientMessages(activeId);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand" />
      </div>
    );
  }

  if (!me) {
    return <Navigate to="/client/login" replace />;
  }

  // Auto-select most recent conversation on mount
  useEffect(() => {
    if (!activeId && conversations.length > 0) {
      setActiveId(conversations[0].conversation_id);
    }
  }, [conversations, activeId]);

  // Load DB messages when active conversation changes
  useEffect(() => {
    if (!dbMessages) return;
    setMessages(
      dbMessages.map((m, i) => ({
        id: m.message_id ?? String(i),
        role: m.role,
        text: m.content,
      })),
    );
  }, [dbMessages]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = useCallback(async () => {
    const conv = await clientApi.createConversation();
    await invalidateConversations();
    setActiveId(conv.conversation_id);
    setMessages([]);
  }, [invalidateConversations]);

  const handleSelectConversation = useCallback((id: string) => {
    setActiveId(id);
    setMessages([]);
  }, []);

  const handleDeleteConversation = useCallback(
    async (conversationId: string) => {
      await clientApi.deleteConversation(conversationId);
      await invalidateConversations();
      if (activeId === conversationId) {
        const remaining = conversations.filter(
          (c) => c.conversation_id !== conversationId,
        );
        setActiveId(remaining[0]?.conversation_id ?? null);
        setMessages([]);
      }
    },
    [invalidateConversations, activeId, conversations],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || streaming || !activeId) return;

      const userMsg: Message = { id: nextId(), role: "user", text: text.trim() };
      const pendingId = nextId();
      const pendingMsg: Message = {
        id: pendingId,
        role: "assistant",
        text: "",
        pending: true,
      };

      setMessages((prev) => [...prev, userMsg, pendingMsg]);
      setInput("");
      setStreaming(true);

      try {
        const resp = await fetch(`${BASE}/client/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Client-Session": getClientSession() ?? "",
          },
          body: JSON.stringify({ conversation_id: activeId, message: text.trim() }),
        });

        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

        const assistantId = nextId();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { id: assistantId, role: "assistant", text: "" }
              : m,
          ),
        );

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "text") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, text: m.text + (event.text as string) }
                      : m,
                  ),
                );
              } else if (event.type === "title") {
                qc.setQueryData<ClientConversation[]>(
                  ["client", "conversations"],
                  (old = []) =>
                    old.map((c) =>
                      c.conversation_id === activeId
                        ? { ...c, title: event.title as string }
                        : c,
                    ),
                );
              }
            } catch { /* ignore malformed SSE lines */ }
          }
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.pending
              ? { ...m, pending: false, text: "Sorry, something went wrong. Please try again." }
              : m,
          ),
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, activeId, qc],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-line-subtle bg-surface-sidebar">
        <div className="p-3">
          <button
            onClick={handleNewChat}
            className="flex w-full items-center gap-2 rounded-lg border border-line-subtle bg-white px-3 py-2 text-sm font-medium text-ink-primary transition hover:border-brand/30 hover:bg-brand-ghost hover:text-brand"
          >
            <Plus className="h-4 w-4" />
            New chat
          </button>
        </div>
        <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {conversations.map((conv) => (
            <ConversationRow
              key={conv.conversation_id}
              conv={conv}
              active={activeId === conv.conversation_id}
              onSelect={() => handleSelectConversation(conv.conversation_id)}
              onDelete={() => handleDeleteConversation(conv.conversation_id)}
            />
          ))}
        </div>
        {/* Footer */}
        <div className="border-t border-line-subtle p-3">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-ink-primary">{me.client_name}</p>
              <p className="truncate text-xs text-ink-muted">{me.account_name}</p>
            </div>
            <button
              onClick={logout}
              className="ml-2 shrink-0 text-ink-muted transition hover:text-red-500"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Chat area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-line-subtle px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-brand text-ink-on-brand shadow-xl-brand">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-ink-primary">
                Your EDGE Relationship Manager — {me.rm_name}
              </h1>
              <p className="text-xs text-ink-muted">
                Ask anything about your account, placements, or staffing needs.
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand/10">
                <Bot className="h-8 w-8 text-brand" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-ink-primary">
                  Hi {me.client_name}, I&apos;m {me.rm_name}
                </p>
                <p className="mt-1 text-xs text-ink-muted">
                  {activeId
                    ? "How can I help you today?"
                    : "Create a new chat or select a conversation to get started."}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "flex gap-3",
                    m.role === "user" ? "flex-row-reverse" : "flex-row",
                  )}
                >
                  <div
                    className={cn(
                      "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      m.role === "user"
                        ? "bg-ink-primary text-white"
                        : "bg-brand text-ink-on-brand shadow-xl-brand",
                    )}
                  >
                    {m.role === "user" ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "max-w-[75%]",
                      m.role === "user" ? "items-end" : "items-start",
                    )}
                  >
                    {m.pending ? (
                      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-surface-sidebar px-4 py-3 text-sm text-ink-secondary">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Thinking…
                      </div>
                    ) : (
                      <div
                        className={cn(
                          "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                          m.role === "user"
                            ? "rounded-tr-sm bg-brand text-ink-on-brand"
                            : "rounded-tl-sm bg-surface-sidebar text-ink-primary",
                        )}
                      >
                        {m.text.split("\n").map((line, j) => (
                          <span key={j}>
                            {line}
                            {j < m.text.split("\n").length - 1 && <br />}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-line-subtle px-6 py-4">
          <div className="flex items-end gap-3 rounded-2xl border border-line-strong bg-white px-4 py-3 focus-within:border-brand/40 focus-within:ring-2 focus-within:ring-brand/10">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                activeId
                  ? "Ask about your account, placements, open roles…"
                  : "Select or create a conversation to start"
              }
              rows={1}
              disabled={streaming || !activeId}
              className="flex-1 resize-none bg-transparent text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none disabled:opacity-60"
              style={{ maxHeight: "120px" }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || streaming || !activeId}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand text-ink-on-brand shadow-xl-brand transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {streaming ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-ink-muted">
            Powered by EDGE Pulse · Press Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Database, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

interface TextPart {
  type: "text";
  text: string;
}

interface ToolPart {
  type: "tool";
  name: string;
  input: Record<string, unknown>;
}

type MessagePart = TextPart | ToolPart;

interface Message {
  id: string;
  role: Role;
  parts: MessagePart[];
  pending?: boolean;
}

interface HistoryItem {
  role: Role;
  content: string;
}

// ── Suggested starters ─────────────────────────────────────────────────────

const SUGGESTIONS = [
  "How many active associates are there across all accounts?",
  "Which accounts have the highest churn probability?",
  "Show me accounts with no outreach in the last 30 days.",
  "How many open opportunities are closing this quarter?",
  "What are the top 5 accounts by active associate count?",
  "Which Strategic-tier accounts are at churn risk?",
];

// ── Components ─────────────────────────────────────────────────────────────

function ToolCallChip({ name, input }: { name: string; input: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const soql = typeof input.soql === "string" ? input.soql : JSON.stringify(input);
  return (
    <div className="mt-1.5 inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full bg-brand-muted px-2.5 py-1 text-xs font-medium text-brand transition hover:bg-brand/10"
      >
        <Database className="h-3 w-3" />
        {name}
        <span className="text-brand/60">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <pre className="mt-1.5 w-full max-w-lg overflow-x-auto rounded-xl bg-surface-sidebar p-3 text-xs text-ink-secondary">
          {soql}
        </pre>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ink-primary text-ink-on-brand" : "bg-brand text-ink-on-brand shadow-xl-brand",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className={cn("flex max-w-[75%] flex-col gap-1", isUser ? "items-end" : "items-start")}>
        {message.pending ? (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-surface-sidebar px-4 py-3 text-sm text-ink-secondary">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Thinking…
          </div>
        ) : (
          message.parts.map((part, i) => {
            if (part.type === "tool") {
              return (
                <ToolCallChip key={i} name={part.name} input={part.input} />
              );
            }
            if (!part.text.trim()) return null;
            return (
              <div
                key={i}
                className={cn(
                  "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  isUser
                    ? "rounded-tr-sm bg-brand text-ink-on-brand"
                    : "rounded-tl-sm bg-surface-sidebar text-ink-primary",
                )}
              >
                {part.text.split("\n").map((line, j) => (
                  <span key={j}>
                    {line}
                    {j < part.text.split("\n").length - 1 && <br />}
                  </span>
                ))}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export function SupportPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const idCounter = useRef(0);

  const nextId = () => String(++idCounter.current);

  // Build history for the API (only text parts, fully resolved messages)
  const buildHistory = useCallback((msgs: Message[]): HistoryItem[] => {
    return msgs
      .filter((m) => !m.pending)
      .map((m) => ({
        role: m.role,
        content: m.parts
          .filter((p): p is TextPart => p.type === "text")
          .map((p) => p.text)
          .join("\n")
          .trim(),
      }))
      .filter((m) => m.content.length > 0);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || streaming) return;

      const userMsg: Message = {
        id: nextId(),
        role: "user",
        parts: [{ type: "text", text: text.trim() }],
      };

      const pendingId = nextId();
      const pendingMsg: Message = {
        id: pendingId,
        role: "assistant",
        parts: [],
        pending: true,
      };

      setMessages((prev) => {
        const next = [...prev, userMsg, pendingMsg];
        // send with the history BEFORE adding this message
        return next;
      });
      setInput("");
      setStreaming(true);

      try {
        const history = buildHistory(messages);

        const resp = await fetch("http://localhost:8000/support/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim(), history }),
        });

        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        // Replace pending bubble with real accumulating message
        const assistantId = nextId();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { id: assistantId, role: "assistant", parts: [], pending: false }
              : m,
          ),
        );

        const appendPart = (part: MessagePart) => {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const last = m.parts[m.parts.length - 1];
              if (part.type === "text" && last?.type === "text") {
                // Merge consecutive text parts
                return {
                  ...m,
                  parts: [
                    ...m.parts.slice(0, -1),
                    { type: "text", text: last.text + part.text },
                  ],
                };
              }
              return { ...m, parts: [...m.parts, part] };
            }),
          );
        };

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
                appendPart({ type: "text", text: event.text });
              } else if (event.type === "tool") {
                appendPart({ type: "tool", name: event.name, input: event.input });
              }
              // "done" → just stop reading
            } catch {
              // ignore malformed SSE lines
            }
          }
        }
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId || m.pending
              ? {
                  ...m,
                  pending: false,
                  parts: [
                    {
                      type: "text",
                      text: "Sorry, something went wrong. Make sure the API server is running.",
                    },
                  ],
                }
              : m,
          ),
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, messages, buildHistory],
  );

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col">
      {/* Header */}
      <div className="border-b border-line-subtle px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-ink-primary">Edge Pulse Support AI</h1>
            <p className="text-xs text-ink-muted">
              Ask anything about Edge accounts, associates, outreach, or opportunities — live Salesforce data.
            </p>
          </div>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {empty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6">
            <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand/10">
              <Bot className="h-8 w-8 text-brand" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-ink-primary">Ask me anything about Edge data</p>
              <p className="mt-1 text-xs text-ink-muted">I have live read-only access to the Edge Salesforce org.</p>
            </div>
            <div className="grid max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="rounded-2xl border border-line-subtle bg-white px-4 py-3 text-left text-xs text-ink-secondary transition hover:border-brand/30 hover:bg-brand-ghost hover:text-brand"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-line-subtle px-6 py-4">
        <div className="flex items-end gap-3 rounded-2xl border border-line-strong bg-white px-4 py-3 focus-within:border-brand/40 focus-within:ring-2 focus-within:ring-brand/10">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about accounts, associates, churn risk, opportunities…"
            rows={1}
            disabled={streaming}
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
            disabled={!input.trim() || streaming}
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
          Powered by Claude · Read-only Salesforce access · Press Enter to send
        </p>
      </div>
    </div>
  );
}

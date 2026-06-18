import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, Send, RefreshCw, X } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError } from "@/lib/api";
import { useAccountHealth } from "@/features/account/hooks";
import {
  useInbox,
  useInboxEmail,
  useSaveDraft,
  useRegenerate,
  useSendReply,
  useDismiss,
} from "./hooks";
import type { InboxEmailDTO, ReplyTone } from "./types";

const RISK_ACCENT: Record<string, string> = {
  High: "border-l-risk-high-fg",
  Medium: "border-l-amber-500",
  Low: "border-l-line-strong",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 60) return `${Math.max(mins, 1)}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function initials(name: string | null, email: string): string {
  const src = (name || email).trim();
  const parts = src.split(/\s+/);
  return (
    ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() ||
    email[0]?.toUpperCase() ||
    "?"
  );
}

export function InboxPage() {
  const { data, isLoading } = useInbox();
  const emails = useMemo(() => data?.emails ?? [], [data]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && emails.length) setSelectedId(emails[0].email_id);
    if (selectedId && !emails.some((e) => e.email_id === selectedId)) {
      setSelectedId(emails[0]?.email_id ?? null);
    }
  }, [emails, selectedId]);

  return (
    <div className="grid h-[calc(100vh-64px)] grid-cols-12 overflow-hidden">
      <aside className="col-span-12 overflow-y-auto border-r border-line-subtle lg:col-span-4">
        <div className="flex items-center justify-between p-6 pb-3">
          <h1 className="text-lg font-semibold uppercase tracking-[0.18em]">Inbox</h1>
          <span className="text-xs text-ink-secondary">{emails.length} to reply</span>
        </div>
        {isLoading && <p className="px-6 text-sm text-ink-secondary">Loading…</p>}
        {!isLoading && emails.length === 0 && (
          <div className="mx-6 flex items-center gap-2 rounded-3xl bg-surface-tinted-row p-4 text-sm">
            <Sparkles className="h-4 w-4 text-brand" />
            You&apos;re all caught up — new client emails will appear here.
          </div>
        )}
        <div className="space-y-1 px-3 pb-6">
          <AnimatePresence initial={false}>
            {emails.map((e) => (
              <motion.button
                key={e.email_id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onClick={() => setSelectedId(e.email_id)}
                className={`flex w-full gap-3 rounded-2xl border-l-2 ${
                  RISK_ACCENT[e.risk ?? "Low"]
                } p-3 text-left transition ${
                  selectedId === e.email_id ? "bg-brand-muted" : "hover:bg-brand-ghost"
                }`}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-card text-xs font-semibold text-ink-secondary">
                  {initials(e.from_name, e.from_email)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">
                      {e.from_name ?? e.from_email}
                    </span>
                    <span className="shrink-0 text-[10px] text-ink-secondary">
                      {relativeTime(e.received_at)}
                    </span>
                  </span>
                  <span className="block truncate text-xs font-medium text-ink-primary">
                    {e.subject ?? "(no subject)"}
                  </span>
                  <span className="block truncate text-xs text-ink-secondary">{e.snippet}</span>
                  {e.has_draft && (
                    <span className="mt-1 inline-block rounded-full bg-brand-ghost px-2 py-0.5 text-[10px] text-brand">
                      AI reply ready
                    </span>
                  )}
                </span>
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      </aside>

      <section className="col-span-12 overflow-y-auto lg:col-span-8">
        {selectedId ? (
          <EmailDetail
            key={selectedId}
            emailId={selectedId}
            summary={emails.find((e) => e.email_id === selectedId)}
          />
        ) : (
          <p className="p-6 text-sm text-ink-secondary">Select an email to view.</p>
        )}
      </section>
    </div>
  );
}

function AccountContextCard({ accountId }: { accountId: string | null }) {
  const { data } = useAccountHealth(accountId);
  if (!accountId || !data) return null;
  return (
    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl bg-surface-tinted-row p-4 text-xs">
      <span className="text-sm font-semibold">{data.name}</span>
      <span className="rounded-full bg-surface-card px-2 py-0.5">{data.tier}</span>
      <span
        className={`rounded-full px-2 py-0.5 ${
          data.risk === "High" ? "bg-risk-high-bg text-risk-high-fg" : "bg-surface-card"
        }`}
      >
        {data.risk} risk
      </span>
      <span className="text-ink-secondary">Health {Math.round(data.composite_health)}/10</span>
      <span className="text-ink-secondary">${(data.arr_usd / 1000).toFixed(0)}k ARR</span>
      <Link to="/accounts" className="ml-auto text-brand hover:underline">
        View account →
      </Link>
    </div>
  );
}

function EmailDetail({ emailId, summary }: { emailId: string; summary?: InboxEmailDTO }) {
  const { data: email, isLoading } = useInboxEmail(emailId);
  const saveDraft = useSaveDraft();
  const regenerate = useRegenerate();
  const sendReply = useSendReply();
  const dismiss = useDismiss();

  const [text, setText] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [reconnect, setReconnect] = useState(false);

  useEffect(() => {
    if (email) setText(email.draft_reply ?? email.suggested_reply ?? "");
  }, [email]);

  if (isLoading || !email) return <p className="p-6 text-sm text-ink-secondary">Loading…</p>;

  const onBlurSave = () => {
    if (text && text !== (email.draft_reply ?? email.suggested_reply ?? "")) {
      saveDraft.mutate({ emailId, text });
    }
  };

  const onRegenerate = (tone?: ReplyTone) =>
    regenerate.mutate({ emailId, tone }, { onSuccess: (d) => setText(d.reply) });

  const onSend = () => {
    setReconnect(false);
    sendReply.mutate(
      { emailId, text },
      {
        onSuccess: () => setToast(`Reply sent to ${summary?.from_name ?? email.from_email}`),
        onError: (err) => {
          if (err instanceof ApiError && err.status === 403) setReconnect(true);
          else setToast("Send failed — try again.");
        },
      },
    );
  };

  return (
    <div className="p-6">
      <AccountContextCard accountId={email.account_id} />

      <div className="mb-4">
        <h2 className="text-base font-semibold">{email.subject ?? "(no subject)"}</h2>
        <p className="text-xs text-ink-secondary">
          From {email.from_name ?? email.from_email} &lt;{email.from_email}&gt;
        </p>
      </div>

      <div className="mb-6 whitespace-pre-wrap rounded-2xl border border-line-subtle bg-surface-card p-4 text-sm leading-relaxed">
        {email.body}
      </div>

      <div className="rounded-2xl border border-line-strong bg-surface-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            Re: {email.subject ?? ""} · To: {email.from_email}
          </span>
          <div className="flex gap-1">
            {(["formal", "shorter", "warmer"] as ReplyTone[]).map((t) => (
              <button
                key={t}
                onClick={() => onRegenerate(t)}
                disabled={regenerate.isPending}
                className="rounded-full bg-brand-ghost px-2 py-0.5 text-[11px] capitalize text-brand hover:bg-brand-muted disabled:opacity-50"
              >
                {t}
              </button>
            ))}
            <button
              onClick={() => onRegenerate()}
              disabled={regenerate.isPending}
              className="flex items-center gap-1 rounded-full bg-brand-ghost px-2 py-0.5 text-[11px] text-brand hover:bg-brand-muted disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${regenerate.isPending ? "animate-spin" : ""}`} />
              Regenerate
            </button>
          </div>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={onBlurSave}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onSend();
          }}
          rows={8}
          placeholder={regenerate.isPending ? "Drafting…" : "Write your reply…"}
          className="w-full resize-none rounded-xl border border-line-subtle bg-surface-base p-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
        />

        {email.reply_rationale && (
          <p className="mt-2 text-[11px] italic text-ink-secondary">
            Why this draft: {email.reply_rationale}
          </p>
        )}

        <div className="mt-3 flex items-center gap-2">
          {reconnect ? (
            <button
              onClick={() => {
                const apiBase = import.meta.env.VITE_API_BASE ?? "/api";
                window.location.href = `${apiBase}/auth/google/start`;
              }}
              className="rounded-full bg-brand px-4 py-1.5 text-sm font-medium text-white"
            >
              Reconnect Google to send
            </button>
          ) : (
            <button
              onClick={onSend}
              disabled={sendReply.isPending || !text.trim()}
              className="flex items-center gap-2 rounded-full bg-brand px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {sendReply.isPending ? "Sending…" : "Send"}
            </button>
          )}
          <button
            onClick={() => dismiss.mutate(emailId)}
            disabled={dismiss.isPending}
            className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm text-ink-secondary hover:bg-brand-ghost"
          >
            <X className="h-4 w-4" />
            Dismiss
          </button>
          <span className="ml-auto text-[11px] text-ink-secondary">⌘/Ctrl+Enter to send</span>
        </div>
      </div>

      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded-xl bg-surface-tinted-row p-3 text-sm text-ink-primary"
        >
          {toast}
        </motion.div>
      )}
    </div>
  );
}

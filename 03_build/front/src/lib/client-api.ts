/**
 * HTTP client for the /client/* API routes.
 * Uses X-Client-Session header (stored in localStorage) instead of Google OAuth.
 * Completely separate from the RM-facing api.ts.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "/api";
const SESSION_KEY = "client_session_id";

export function getClientSession(): string | null {
  return localStorage.getItem(SESSION_KEY);
}

export function setClientSession(id: string): void {
  localStorage.setItem(SESSION_KEY, id);
}

export function clearClientSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

function clientHeaders(): Record<string, string> {
  const session = getClientSession();
  return session ? { "X-Client-Session": session } : {};
}

async function clientRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...clientHeaders(),
      ...((init.headers as Record<string, string>) ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch { /* non-JSON body */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as T;
}

export interface ClientMe {
  client_name: string;
  account_name: string;
  rm_name: string;
  contact_email: string;
}

export interface ClientConversation {
  conversation_id: string;
  title: string;
  updated_at: string;
}

export interface ClientMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export const clientApi = {
  requestOtp: (email: string) =>
    clientRequest<{ sent: boolean }>("/client/auth/request-otp", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifyOtp: (email: string, otp: string) =>
    clientRequest<{ session_id: string }>("/client/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({ email, otp }),
    }),

  logout: () =>
    clientRequest<void>("/client/auth/logout", { method: "POST" }),

  me: () =>
    clientRequest<ClientMe>("/client/me"),

  listConversations: () =>
    clientRequest<ClientConversation[]>("/client/conversations"),

  createConversation: () =>
    clientRequest<ClientConversation>("/client/conversations", { method: "POST" }),

  deleteConversation: (id: string) =>
    clientRequest<void>(`/client/conversations/${id}`, { method: "DELETE" }),

  getMessages: (id: string) =>
    clientRequest<ClientMessage[]>(`/client/conversations/${id}/messages`),
};

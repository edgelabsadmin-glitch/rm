/*
 * SPEC-035 — typed fetch client for the Pulse API. Dev proxies /api → FastAPI
 * (vite.config). Auth is the spec-031 placeholder header guard (X-User-Id /
 * X-User-Role / X-Report-Ids) sourced from the stubbed session; spec 043 replaces
 * these with a real bearer token at the same chokepoint.
 */
import type { Session } from "@/session/useSession";

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

function authHeaders(session: Session): Record<string, string> {
  return {
    "X-User-Id": session.id,
    "X-User-Role": session.role,
  };
}

async function request<T>(
  path: string,
  session: Session,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(session),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  listActions: async (
    session: Session,
    params: Record<string, string | number | undefined> = {},
  ) => {
    type ActionsResponse = import("@/features/queue/types").ActionsResponse;
    try {
      return await request<ActionsResponse>(`/actions${qs(params)}`, session);
    } catch (err) {
      // DEV-only: with no FastAPI behind the /api proxy, serve the Phase-1 demo
      // fixture so the queue renders. Prod surfaces the error (Week-4 live wiring).
      if (import.meta.env.DEV) {
        const { filterDemoActions } = await import("@/features/queue/demo_actions");
        return filterDemoActions({
          rm_id: params.rm_id as string | undefined,
          tier: params.tier as string | undefined,
          customer_id: params.customer_id as string | undefined,
        });
      }
      throw err;
    }
  },

  getAction: (session: Session, id: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}`, session),

  approve: (session: Session, id: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/approve`, session, {
      method: "POST",
    }),

  modify: (session: Session, id: string, diff: Record<string, unknown>) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/modify`, session, {
      method: "POST",
      body: JSON.stringify({ diff }),
    }),

  reject: (session: Session, id: string, reason_picker: string, free_text?: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/reject`, session, {
      method: "POST",
      body: JSON.stringify({ reason_picker, free_text: free_text ?? null }),
    }),
};

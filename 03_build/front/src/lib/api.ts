/*
 * SPEC-035 — typed fetch client for the Pulse API. Dev proxies /api → FastAPI
 * (vite.config). Auth is the spec-031 placeholder header guard (X-User-Id /
 * X-User-Role / X-Report-Ids) sourced from the stubbed session; spec 043 replaces
 * these with a real bearer token at the same chokepoint.
 */
import type { UserRole } from "@/lib/rbac/types";

const BASE = "/api";

/**
 * Minimal identity the API client sends to pulse-api (spec 042 A3 — replaces the old
 * `Session` type). `DemoUser` from AuthContext satisfies this structurally, so consumers
 * pass `useAuth().user` directly. Mirrors the backend `Caller` model (api/actions.py);
 * spec 043 OAuth swaps the source of `id`/`role` without changing this contract.
 */
export interface ApiCaller {
  id: string;
  role: UserRole;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

export function authHeaders(caller: ApiCaller): Record<string, string> {
  return {
    "X-User-Id": caller.id,
    "X-User-Role": caller.role,
  };
}

async function request<T>(
  path: string,
  caller: ApiCaller,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(caller),
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
    caller: ApiCaller,
    params: Record<string, string | number | undefined> = {},
  ) => {
    type ActionsResponse = import("@/features/queue/types").ActionsResponse;
    try {
      return await request<ActionsResponse>(`/actions${qs(params)}`, caller);
    } catch (err) {
      // DEV-only: with no FastAPI behind the /api proxy, serve the Phase-1 demo
      // fixture so the queue renders. Prod surfaces the error (Week-4 live wiring).
      if (import.meta.env.DEV) {
        const { filterDemoActions } = await import("@/features/queue/demo_actions");
        return filterDemoActions(
          {
            rm_id: params.rm_id as string | undefined,
            tier: params.tier as string | undefined,
            customer_id: params.customer_id as string | undefined,
          },
          caller.role,
        );
      }
      throw err;
    }
  },

  getAction: (caller: ApiCaller, id: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}`, caller),

  approve: (caller: ApiCaller, id: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/approve`, caller, {
      method: "POST",
    }),

  modify: (caller: ApiCaller, id: string, diff: Record<string, unknown>) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/modify`, caller, {
      method: "POST",
      body: JSON.stringify({ diff }),
    }),

  reject: (caller: ApiCaller, id: string, reason_picker: string, free_text?: string) =>
    request<import("@/features/queue/types").ActionDTO>(`/actions/${id}/reject`, caller, {
      method: "POST",
      body: JSON.stringify({ reason_picker, free_text: free_text ?? null }),
    }),
};

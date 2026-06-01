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

export interface AccountSummaryDTO {
  account_id: string;
  name: string;
  composite_health: number;
  risk: "Low" | "Medium" | "High";
  meeting: string;
  tier: string;
  rm_name: string;
  active_talent: number;
  arr_usd: number;
}

export interface AccountHealthDTO extends AccountSummaryDTO {
  positioning: string;
  signal_vector: { label: string; pct: number }[];
  themes: string[];
  churn_probability: number | null;
  last_ebr: string | null;
}

export interface AccountListDTO {
  accounts: AccountSummaryDTO[];
  total: number;
  page: number;
  page_size: number;
}

export const api = {
  listAccounts: async (
    caller: ApiCaller,
    params: { page?: number; page_size?: number; tier?: string; rm_id?: string; [key: string]: unknown } = {},
  ) => {
    try {
      return await request<AccountListDTO>(`/accounts${qs(params)}`, caller);
    } catch (err) {
      if (import.meta.env.DEV) {
        const { getAccountSummaries } = await import("@/features/hero/fixtures");
        const { accountARR } = await import("@/fixtures/demo_characters");
        const sums = getAccountSummaries();
        return {
          accounts: sums.map((a) => ({
            ...a,
            tier: "Core",
            rm_name: "",
            active_talent: 0,
            arr_usd: accountARR(a.account_id),
          })),
          total: sums.length,
          page: 1,
          page_size: 50,
        };
      }
      throw err;
    }
  },

  getAccountHealth: async (caller: ApiCaller, accountId: string) => {
    try {
      return await request<AccountHealthDTO>(`/accounts/${accountId}`, caller);
    } catch (err) {
      if (import.meta.env.DEV) {
        const { getAccountHealthFixture } = await import("@/features/hero/fixtures");
        const { accountARR } = await import("@/fixtures/demo_characters");
        const h = getAccountHealthFixture(accountId);
        return {
          ...h,
          rm_name: "",
          active_talent: 0,
          arr_usd: accountARR(h.account_id),
          churn_probability: null,
          last_ebr: null,
        };
      }
      throw err;
    }
  },

  getOpportunities: async (caller: ApiCaller, accountId: string) => {
    interface OppItem {
      opportunity_id: string;
      name: string;
      stage: string;
      close_date: string | null;
      amount: number | null;
    }
    try {
      return await request<OppItem[]>(`/submit/opportunities?account_id=${accountId}`, caller);
    } catch {
      return [] as OppItem[];
    }
  },

  createOutreach: async (caller: ApiCaller, body: Record<string, unknown>) =>
    request<{ record_id: string; message: string }>("/submit/outreach", caller, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listActions: async (
    caller: ApiCaller,
    params: Record<string, string | number | undefined> = {},
  ) => {
    type ActionsResponse = import("@/features/queue/types").ActionsResponse;
    const customerId = params.customer_id as string | undefined;

    try {
      const data = await request<ActionsResponse>(`/actions${qs(params)}`, caller);
      // DEV: if backend returns zero actions for a specific account, generate test data.
      if (import.meta.env.DEV && customerId && data.actions.length === 0) {
        const { generateAccountActions } = await import("@/features/queue/demo_actions");
        const generated = generateAccountActions(customerId);
        return { actions: generated, count: generated.length, limit: 200, offset: 0 };
      }
      return data;
    } catch (err) {
      if (import.meta.env.DEV) {
        const { filterDemoActions } = await import("@/features/queue/demo_actions");
        return filterDemoActions(
          {
            rm_id: params.rm_id as string | undefined,
            tier: params.tier as string | undefined,
            customer_id: customerId,
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

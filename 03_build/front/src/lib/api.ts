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
    session: Session,
    params: { page?: number; page_size?: number; tier?: string; rm_id?: string } = {},
  ) => {
    try {
      return await request<AccountListDTO>(`/accounts${qs(params)}`, session);
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

  getAccountHealth: async (session: Session, accountId: string) => {
    try {
      return await request<AccountHealthDTO>(`/accounts/${accountId}`, session);
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

  getOpportunities: async (session: Session, accountId: string) => {
    interface OppItem {
      opportunity_id: string;
      name: string;
      stage: string;
      close_date: string | null;
      amount: number | null;
    }
    try {
      return await request<OppItem[]>(`/submit/opportunities?account_id=${accountId}`, session);
    } catch {
      return [] as OppItem[];
    }
  },

  createOutreach: async (session: Session, body: Record<string, unknown>) =>
    request<{ record_id: string; message: string }>("/submit/outreach", session, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listActions: async (
    session: Session,
    params: Record<string, string | number | undefined> = {},
  ) => {
    type ActionsResponse = import("@/features/queue/types").ActionsResponse;
    const customerId = params.customer_id as string | undefined;

    const devFallback = async () => {
      const { filterDemoActions, generateAccountActions } = await import(
        "@/features/queue/demo_actions"
      );
      const result = filterDemoActions({
        rm_id: params.rm_id as string | undefined,
        tier: params.tier as string | undefined,
        customer_id: customerId,
      });
      if (customerId && result.actions.length === 0) {
        const generated = generateAccountActions(customerId);
        return { actions: generated, count: generated.length, limit: 200, offset: 0 };
      }
      return result;
    };

    try {
      const data = await request<ActionsResponse>(`/actions${qs(params)}`, session);
      // In DEV, if the backend returned zero actions for a specific account, show
      // generated test data so the queue is never empty during development.
      if (import.meta.env.DEV && customerId && data.actions.length === 0) {
        return devFallback();
      }
      return data;
    } catch (err) {
      if (import.meta.env.DEV) return devFallback();
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

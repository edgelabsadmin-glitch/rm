/*
 * SPEC-035 — Action Queue DTOs, mirroring the spec-031 API
 * (core/actions/queue.py ActionRecord.public_dict). why_detail is a STRING of
 * inline-tag prose (Tier-0 §10), not a dict. skill_id is present only for admins.
 */
export type ApprovalStatus =
  | "pending"
  | "approved"
  | "modified-approved"
  | "rejected"
  | "expired"
  | "dispatched";

export type Urgency = "low" | "medium-low" | "medium" | "medium-high" | "high";

export interface ActionDTO {
  action_id: string;
  customer_id: string | null;
  talent_id: string | null;
  rm_id: string | null;
  tier_class: string | null;
  urgency: Urgency | null;
  action_card: Record<string, unknown>;
  why_oneline: string;
  why_detail: string | null;
  modifiable_fields: string[];
  source_episodes: string[];
  proposed_at: string;
  status: ApprovalStatus;
  rank_score: number;
  skill_id?: string | null;
  // present only on GET /actions/{id}
  history?: Array<Record<string, unknown>>;
}

export interface ActionsResponse {
  actions: ActionDTO[];
  count: number;
  limit: number;
  offset: number;
}

export interface QueueFilters {
  tier?: string;
  customer_id?: string;
  skill_id?: string;
  rm_id?: string;
}

export const REJECT_REASONS = [
  "Wrong customer / context",
  "Wrong action type / tone",
  "Already done elsewhere",
  "Not now",
] as const;
export type RejectReason = (typeof REJECT_REASONS)[number];

/** Best-effort headline from the action_card, falling back to why_oneline. */
export function actionHeadline(a: ActionDTO): string {
  const card = a.action_card ?? {};
  const h = (card.headline ?? card.title ?? card.subject) as string | undefined;
  return h?.trim() || a.why_oneline || "Proposed action";
}

/** action_card.action_type → human label (best-effort). */
export function actionType(a: ActionDTO): string | null {
  const t = (a.action_card?.action_type ?? a.action_card?.channel) as string | undefined;
  return t ?? null;
}

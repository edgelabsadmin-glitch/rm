/*
 * SPEC-042 Step-5 — Action Queue scope helpers (pure; the security-critical filter that
 * QueueList applies to fetched cards). visibleRmIdsForCaller is the authoritative role scope;
 * scopeAndRefineCards applies it, then the URL ?rm= refinement ON TOP (UX, not a boundary —
 * so a crafted ?rm= can never widen what the caller sees).
 */
import { DEMO_RMS } from "@/fixtures/demo_characters";
import type { UserRole } from "@/lib/rbac/types";

/** rm_ids the caller may see. null = no filter (admin sees all). [] = none (executive). */
export function visibleRmIdsForCaller(role: UserRole, userId: string): string[] | null {
  if (role === "admin") return null;
  if (role === "rm") return [userId];
  if (role === "manager") return DEMO_RMS.filter((rm) => rm.managerId === userId).map((rm) => rm.id);
  return []; // executive — route-blocked from /actions; defensive empty
}

/** Scope filter (security) then URL ?rm= refinement (UX), in that order. */
export function scopeAndRefineCards<T extends { rm_id: string | null }>(
  cards: ReadonlyArray<T>,
  role: UserRole,
  userId: string,
  urlRm?: string | null,
): T[] {
  const visible = visibleRmIdsForCaller(role, userId);
  const scoped =
    visible === null ? [...cards] : cards.filter((c) => c.rm_id != null && visible.includes(c.rm_id));
  return urlRm ? scoped.filter((c) => c.rm_id === urlRm) : scoped;
}

// SPEC-042 Step-5 follow-up (Q3): Status + Time filters replace the dead My-Queue/Overall
// toggle. UX layer — applied AFTER the role-scope security filter. Pure + now-injectable.
export type StatusFilter = "active" | "approved" | "all";
export type TimeFilter = "all-time" | "today" | "this-week";

const DAY_MS = 24 * 60 * 60 * 1000;

/** "active" → pending only; "approved" → approved only; "all" → no filter. */
export function applyStatusFilter<T extends { status: string }>(
  cards: ReadonlyArray<T>,
  status: StatusFilter,
): T[] {
  if (status === "active") return cards.filter((c) => c.status === "pending");
  if (status === "approved") return cards.filter((c) => c.status === "approved");
  return [...cards];
}

/** "today" → proposed within 24h; "this-week" → within 7d; "all-time" → no filter. */
export function applyTimeFilter<T extends { proposed_at: string }>(
  cards: ReadonlyArray<T>,
  time: TimeFilter,
  now: number = Date.now(),
): T[] {
  if (time === "all-time") return [...cards];
  const cutoff = now - (time === "today" ? DAY_MS : 7 * DAY_MS);
  return cards.filter((c) => new Date(c.proposed_at).getTime() >= cutoff);
}

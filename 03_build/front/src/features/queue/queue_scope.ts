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

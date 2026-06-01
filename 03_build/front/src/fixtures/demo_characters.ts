/*
 * SPEC-041 — Demo character canonicalization: the SINGLE SOURCE OF TRUTH for the
 * demo's people + accounts. Operator-ratified (Session-19 rulings), sourced from
 * rm-intelligence-agent Phase-1 pipeline output (data/demo_curated_dataset.json +
 * the five .md files). Constellation, Executive View, per-account, and Action Queue
 * fixtures all consume from here. The fictional "Helix Labs" name is dropped entirely.
 *
 * healthState (locked ruling #4): Healthy→healthy; Neutral/50%→churn-signal;
 * At-Risk-Escalated/90%→churn-signal; "–" (no data)→at-risk (default-to-attention).
 *
 * Managers (operator ground truth, Session 19): Sarah Hooper manages Sajjal Shaheedi,
 * Sidra Zia, Yozeline Candia; Muhammad Ibrahim manages Ameer Ali, Mubeen Sohail, Akash
 * Tahir. Every RM has a real intermediate manager, so no VP-CS rollup is needed — Eddy
 * Chen stays VP-CS only (DEMO_VP_CS), NOT a manager. (SFDC User.ManagerId returned stale
 * data — Hira/Sarah/Eddy/null mix; the operator-verified .md files are canonical. SFDC
 * staleness = Watched Concern #16, post-demo cleanup, out of Pulse-build scope.)
 *
 * Talent: real Active-stage names, deduped to current placement (ruling #1), from
 * demo_talent_names.ts (auto-generated). 269 active across the 14 accounts. DHR
 * Clinics (76) + Mendota (42) carry all names here; the 30-cap (disposition D10) is
 * a UI-rendering concern in the Constellation drill-down, not a data limit.
 */
import { TALENT_NAMES } from "./demo_talent_names";
import type { UserRole } from "@/lib/rbac/types";

export const DEMO_CEO = { id: "iffi-wahla", name: "Iffi Wahla", role: "CEO" } as const;
export const DEMO_VP_CS = {
  id: "eddy-chen",
  name: "Eddy Chen",
  role: "VP of Client Success",
} as const;

export type DemoManager = { id: string; name: string };
export type DemoRM = { id: string; name: string; managerId: string };
export type DemoAccount = {
  id: string;
  name: string;
  tier: "Core" | "Growth" | "Strategic"; // EDGE white-label segments (was SMB/Mid/Enterprise)
  rmId: string;
  healthState: "healthy" | "at-risk" | "churn-signal";
};
export type DemoTalent = { id: string; name: string; accountId: string; stage: "Active" };
/** Account id (string). Alias so consumers can name the intent (e.g. tier-jump events). */
export type DemoAccountId = DemoAccount["id"];

export const DEMO_MANAGERS: ReadonlyArray<DemoManager> = [
  { id: "sarah-hooper", name: "Sarah Hooper" },
  { id: "muhammad-ibrahim", name: "Muhammad Ibrahim" },
];

export const DEMO_RMS: ReadonlyArray<DemoRM> = [
  // Sarah Hooper's team (7 RMs)
  { id: "sidra-zia", name: "Sidra Zia", managerId: "sarah-hooper" },
  { id: "sajjal-shaheedi", name: "Sajjal Shaheedi", managerId: "sarah-hooper" },
  { id: "michael-vasquez", name: "Michael Vasquez", managerId: "sarah-hooper" },
  { id: "yozeline-candia", name: "Yozeline Candia", managerId: "sarah-hooper" },
  { id: "tanveer-shoukat", name: "Tanveer Shoukat", managerId: "sarah-hooper" },
  { id: "muhammad-dawar", name: "Muhammad Dawar Khan", managerId: "sarah-hooper" },
  { id: "attiya-arooj", name: "Attiya Arooj", managerId: "sarah-hooper" },
  // Muhammad Ibrahim's team (9 RMs)
  { id: "ameer-ali", name: "Ameer Ali", managerId: "muhammad-ibrahim" },
  { id: "abbas-haider", name: "Abbas Haider", managerId: "muhammad-ibrahim" },
  { id: "zeeshan-hassan", name: "Zeeshan Hassan", managerId: "muhammad-ibrahim" },
  { id: "ghaeen-salam", name: "Ghaeen Us Salam", managerId: "muhammad-ibrahim" },
  { id: "akash-tahir", name: "Akash Tahir", managerId: "muhammad-ibrahim" },
  { id: "ammar-ashique", name: "Ammar Ashique", managerId: "muhammad-ibrahim" },
  { id: "amir-zaidi", name: "Amir Zaidi", managerId: "muhammad-ibrahim" },
  { id: "mubeen-sohail", name: "Mubeen Sohail", managerId: "muhammad-ibrahim" },
  { id: "sheryl-stephen", name: "Sheryl Stephen", managerId: "muhammad-ibrahim" },
];

export const DEMO_ACCOUNTS: ReadonlyArray<DemoAccount> = [
  // Strategic (was Enterprise)
  { id: "dhr-health-clinics", name: "DHR Health Clinics", tier: "Strategic", rmId: "sidra-zia", healthState: "churn-signal" },
  { id: "remindermedia", name: "ReminderMedia", tier: "Strategic", rmId: "ameer-ali", healthState: "healthy" },
  { id: "dhr-health-hospital", name: "DHR Health Hospital", tier: "Strategic", rmId: "sidra-zia", healthState: "healthy" },
  // Growth (was Mid-Market)
  { id: "mendota-insurance", name: "Mendota Insurance", tier: "Growth", rmId: "sajjal-shaheedi", healthState: "at-risk" },
  { id: "bayhealth", name: "Bayhealth, Inc", tier: "Growth", rmId: "ameer-ali", healthState: "healthy" },
  { id: "denver-wellness", name: "Denver Wellness Associates", tier: "Growth", rmId: "ameer-ali", healthState: "churn-signal" },
  { id: "dr-dental", name: "Dr. Dental", tier: "Growth", rmId: "ameer-ali", healthState: "healthy" },
  { id: "green-security", name: "Green Security LLC", tier: "Growth", rmId: "ameer-ali", healthState: "healthy" },
  { id: "palm-primary-care", name: "Palm Primary Care Texas", tier: "Growth", rmId: "sidra-zia", healthState: "healthy" },
  // Core (was SMB)
  { id: "navaderm", name: "NAVADERM", tier: "Core", rmId: "mubeen-sohail", healthState: "healthy" },
  { id: "dmv-allergy-asthma", name: "DMV Allergy & Asthma", tier: "Core", rmId: "sajjal-shaheedi", healthState: "healthy" },
  { id: "vegas-vascular", name: "Vegas Vascular Specialists", tier: "Core", rmId: "akash-tahir", healthState: "healthy" },
  { id: "manhattan-restorative", name: "Manhattan Restorative Health Sciences", tier: "Core", rmId: "yozeline-candia", healthState: "churn-signal" },
  // Tertiary (storyboard anchor; SFDC Account.Name "Cirventis", alias HelixVM)
  { id: "cirventis", name: "Cirventis", tier: "Growth", rmId: "sajjal-shaheedi", healthState: "at-risk" },
];

// Real Active talent, deduped to current placement (ruling #1) — names from the
// auto-generated module; ids/accountId derived here.
export const DEMO_TALENT: ReadonlyArray<DemoTalent> = DEMO_ACCOUNTS.flatMap((a) =>
  (TALENT_NAMES[a.id] ?? []).map((name, i) => ({
    id: `${a.id}-t${i + 1}`,
    name,
    accountId: a.id,
    stage: "Active" as const,
  })),
);

export const DEMO_ACTIVE_TALENT_TOTAL = DEMO_TALENT.length; // 269 across 14 accounts

/**
 * Phase-1 demo revenue heuristic: $10K per active placement seat. Replaces the real
 * Opportunity > Account ARR roll-up at the Week-4 pulse-api cutover. Single source of
 * truth — every surface consumes ARR via these helpers (PM_CONTEXT §6 #41).
 */
export const REVENUE_PER_SEAT_USD = 10_000;

function activeTalentCount(accountId: string): number {
  return DEMO_TALENT.reduce(
    (n, t) => (t.accountId === accountId && t.stage === "Active" ? n + 1 : n),
    0,
  );
}

export function accountARR(accountId: string): number {
  return activeTalentCount(accountId) * REVENUE_PER_SEAT_USD;
}

export function bookARR(): number {
  return DEMO_TALENT.filter((t) => t.stage === "Active").length * REVENUE_PER_SEAT_USD;
}

export function rmBookARR(rmId: string): number {
  return DEMO_ACCOUNTS.filter((a) => a.rmId === rmId).reduce((s, a) => s + accountARR(a.id), 0);
}

export function managerBookARR(managerId: string): number {
  return DEMO_RMS.filter((r) => r.managerId === managerId).reduce(
    (s, r) => s + rmBookARR(r.id),
    0,
  );
}

/** Sum of ARR across accounts in at-risk + churn-signal states. */
export function churnExposureARR(): number {
  return DEMO_ACCOUNTS.filter(
    (a) => a.healthState === "at-risk" || a.healthState === "churn-signal",
  ).reduce((s, a) => s + accountARR(a.id), 0);
}

/** Compact currency: $760K, $1.5M, $2.69M. Consistent across surfaces. */
export function formatARR(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(2).replace(/\.?0+$/, "")}M`;
  if (usd >= 1_000) return `$${Math.round(usd / 1_000)}K`;
  return `$${usd.toLocaleString()}`;
}

// ============================================================================
// DEMO_USERS — Phase 1A hardcoded role assignments per spec 042
// ============================================================================
// Email convention: {first}.{last}@onedge.co for everyone except Iffi Wahla
// on edgeonline.co (single executive on secondary domain per Session 19
// late-late stream extended operator confirmation).
// Pulse Admin = admin@onedge.co (functional alias, not a person).
// Spec 043 OAuth Week 4 requires Google Workspace multi-domain configuration.
// RM/Manager ids match canonical DEMO_RMS / DEMO_MANAGERS (verified).
export interface DemoUser {
  id: string;
  displayName: string;
  email: string;
  role: UserRole;
  rmId?: string; // for RM role; identifies which RM this user IS
  managerId?: string; // for Manager role; identifies which Manager this user IS
  avatarInitials: string;
  /** Real Salesforce User ID (15/18-char). Used as rm_id when filtering /accounts
   *  by owner_id — the DB stores SF IDs, not demo slugs. */
  sfUserId?: string;
}

export const DEMO_USERS: ReadonlyArray<DemoUser> = [
  // Executives
  { id: "iffi-wahla", displayName: "Iffi Wahla", email: "iffi.wahla@edgeonline.co", role: "executive", avatarInitials: "IW" },
  { id: "eddy-chen", displayName: "Eddy Chen", email: "eddy.chen@onedge.co", role: "executive", sfUserId: "005U1000005qMJJIA2", avatarInitials: "EC" },
  // Managers
  { id: "sarah-hooper", displayName: "Sarah Hooper", email: "sarah.hooper@onedge.co", role: "manager", managerId: "sarah-hooper", sfUserId: "005U1000000z4ujIAA", avatarInitials: "SH" },
  { id: "muhammad-ibrahim", displayName: "Muhammad Ibrahim", email: "muhammad.ibrahim@onedge.co", role: "manager", managerId: "muhammad-ibrahim", sfUserId: "005U10000075k1OIAQ", avatarInitials: "MI" },
  // RMs — Sarah Hooper's team
  { id: "sidra-zia", displayName: "Sidra Zia", email: "sidra.zia@onedge.co", role: "rm", rmId: "sidra-zia", sfUserId: "0056S00000F13rsQAB", avatarInitials: "SZ" },
  { id: "sajjal-shaheedi", displayName: "Sajjal Shaheedi", email: "sajjal.shaheedi@edgeonline.co", role: "rm", rmId: "sajjal-shaheedi", sfUserId: "0056S00000H7On5QAF", avatarInitials: "SS" },
  { id: "michael-vasquez", displayName: "Michael Vasquez", email: "michael.vasquez@onedge.co", role: "rm", rmId: "michael-vasquez", sfUserId: "005U10000032bOLIAY", avatarInitials: "MV" },
  { id: "yozeline-candia", displayName: "Yozeline Candia", email: "yozeline.candia@onedge.co", role: "rm", rmId: "yozeline-candia", sfUserId: "005U10000032bZdIAI", avatarInitials: "YC" },
  { id: "tanveer-shoukat", displayName: "Tanveer Shoukat", email: "tanveer.shoukat@onedge.co", role: "rm", rmId: "tanveer-shoukat", sfUserId: "005U100000BaAiTIAV", avatarInitials: "TS" },
  { id: "muhammad-dawar", displayName: "Muhammad Dawar Khan", email: "muhammad.dawar@onedge.co", role: "rm", rmId: "muhammad-dawar", sfUserId: "005U100000BaBHxIAN", avatarInitials: "MD" },
  { id: "attiya-arooj", displayName: "Attiya Arooj", email: "attiya.arooj@onedge.co", role: "rm", rmId: "attiya-arooj", sfUserId: "005U100000BlqxhIAB", avatarInitials: "AR" },
  // RMs — Muhammad Ibrahim's team
  { id: "ameer-ali", displayName: "Ameer Ali", email: "ameer.ali@onedge.co", role: "rm", rmId: "ameer-ali", sfUserId: "005U1000007UP09IAG", avatarInitials: "AA" },
  { id: "abbas-haider", displayName: "Abbas Haider", email: "abbas.haider@onedge.co", role: "rm", rmId: "abbas-haider", sfUserId: "005U1000007UPBRIA4", avatarInitials: "AH" },
  { id: "zeeshan-hassan", displayName: "Zeeshan Hassan", email: "zeeshan.hassan@onedge.co", role: "rm", rmId: "zeeshan-hassan", sfUserId: "005U1000007nCtdIAE", avatarInitials: "ZH" },
  { id: "ghaeen-salam", displayName: "Ghaeen Us Salam", email: "ghaeen.salam@onedge.co", role: "rm", rmId: "ghaeen-salam", sfUserId: "005U100000B4AGzIAN", avatarInitials: "GS" },
  { id: "akash-tahir", displayName: "Akash Tahir", email: "akash.tahir@onedge.co", role: "rm", rmId: "akash-tahir", sfUserId: "005U100000Ba9b7IAB", avatarInitials: "AT" },
  { id: "ammar-ashique", displayName: "Ammar Ashique", email: "ammar.ashique@onedge.co", role: "rm", rmId: "ammar-ashique", sfUserId: "005U100000BlpSLIAZ", avatarInitials: "AM" },
  { id: "amir-zaidi", displayName: "Amir Zaidi", email: "amir.zaidi@onedge.co", role: "rm", rmId: "amir-zaidi", sfUserId: "005U100000BlqfxIAB", avatarInitials: "AZ" },
  { id: "mubeen-sohail", displayName: "Mubeen Sohail", email: "mubeen.sohail@onedge.co", role: "rm", rmId: "mubeen-sohail", sfUserId: "005U100000Blr0vIAB", avatarInitials: "MS" },
  { id: "sheryl-stephen", displayName: "Sheryl Stephen", email: "sheryl.stephen@onedge.co", role: "rm", rmId: "sheryl-stephen", sfUserId: "005U100000Blr5lIAB", avatarInitials: "SR" },
  // Admin (functional alias)
  { id: "pulse-admin", displayName: "Pulse Admin", email: "admin@onedge.co", role: "admin", avatarInitials: "PA" },
];

/**
 * Returns the SF User IDs for a manager + all their direct reports.
 * Used to build the rm_ids filter so managers see their book + team's book.
 */
export function managerSfUserIds(managerId: string): string[] {
  const mgr = DEMO_USERS.find((u) => u.id === managerId);
  const teamSlugIds = DEMO_RMS.filter((r) => r.managerId === managerId).map((r) => r.id);
  const teamSfIds = DEMO_USERS
    .filter((u) => teamSlugIds.includes(u.id) && u.sfUserId)
    .map((u) => u.sfUserId!);
  const result: string[] = [];
  if (mgr?.sfUserId) result.push(mgr.sfUserId);
  result.push(...teamSfIds);
  return result;
}

/**
 * Builds the API filter params based on the current user's role:
 *   RM       → { rm_id: sfUserId }       their own accounts
 *   Manager  → { rm_ids: "id1,id2,..." } their accounts + team's accounts
 *   Exec/Admin → {}                       all accounts (no filter)
 */
export function buildAccountFilter(user: DemoUser): { rm_id?: string; rm_ids?: string } {
  if (user.role === "rm") return { rm_id: user.sfUserId ?? user.id };
  if (user.role === "manager") {
    const ids = managerSfUserIds(user.id);
    return ids.length ? { rm_ids: ids.join(",") } : {};
  }
  return {};
}

/*
 * SPEC-041 — Demo character canonicalization: the SINGLE SOURCE OF TRUTH for the
 * demo's people + accounts. Operator-ratified (Session-19 rulings), sourced from
 * rm-intelligence-agent Phase-1 pipeline output (data/demo_curated_dataset.json +
 * the five .md files). Constellation, CEO View, per-account, and Action Queue
 * fixtures all consume from here. The fictional "Helix Labs" name is dropped entirely.
 *
 * healthState (locked ruling #4): Healthy→healthy; Neutral/50%→churn-signal;
 * At-Risk-Escalated/90%→churn-signal; "–" (no data)→at-risk (default-to-attention).
 *
 * Managers (locked ruling): per SFDC — Sajjal Shaheedi→Hira Wahla, Sidra Zia→Sarah
 * Hooper; the 4 RMs with null ManagerId (Akash, Ameer, Mubeen, Yozeline) bucket under
 * VP-CS Eddy Chen as their effective manager. Eddy is dual-role (VP-CS recipient +
 * a manager node in the Constellation) — intentional, no conflict.
 * NOTE: this manager mapping follows the explicit ruling (SFDC SOQL + Eddy bucket);
 * it intentionally differs from the .md files' interim "Muhammad Ibrahim" mapping.
 *
 * Talent: real Active-stage names, deduped to current placement (ruling #1), from
 * demo_talent_names.ts (auto-generated). 269 active across the 14 accounts. DHR
 * Clinics (76) + Mendota (42) carry all names here; the 30-cap (disposition D10) is
 * a UI-rendering concern in the Constellation drill-down, not a data limit.
 */
import { TALENT_NAMES } from "./demo_talent_names";

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
  tier: "SMB" | "Mid" | "Enterprise";
  rmId: string;
  healthState: "healthy" | "at-risk" | "churn-signal";
};
export type DemoTalent = { id: string; name: string; accountId: string; stage: "Active" };

export const DEMO_MANAGERS: ReadonlyArray<DemoManager> = [
  { id: "hira-wahla", name: "Hira Wahla" },
  { id: "sarah-hooper", name: "Sarah Hooper" },
  { id: "eddy-chen", name: "Eddy Chen" }, // VP-CS, effective manager for the 4 unmanaged RMs
];

export const DEMO_RMS: ReadonlyArray<DemoRM> = [
  { id: "sajjal-shaheedi", name: "Sajjal Shaheedi", managerId: "hira-wahla" },
  { id: "sidra-zia", name: "Sidra Zia", managerId: "sarah-hooper" },
  { id: "akash-tahir", name: "Akash Tahir", managerId: "eddy-chen" },
  { id: "ameer-ali", name: "Ameer Ali", managerId: "eddy-chen" },
  { id: "mubeen-sohail", name: "Mubeen Sohail", managerId: "eddy-chen" },
  { id: "yozeline-candia", name: "Yozeline Candia", managerId: "eddy-chen" },
];

export const DEMO_ACCOUNTS: ReadonlyArray<DemoAccount> = [
  // Enterprise
  { id: "dhr-health-clinics", name: "DHR Health Clinics", tier: "Enterprise", rmId: "sidra-zia", healthState: "churn-signal" },
  { id: "remindermedia", name: "ReminderMedia", tier: "Enterprise", rmId: "ameer-ali", healthState: "healthy" },
  { id: "dhr-health-hospital", name: "DHR Health Hospital", tier: "Enterprise", rmId: "sidra-zia", healthState: "healthy" },
  // Mid-Market
  { id: "mendota-insurance", name: "Mendota Insurance", tier: "Mid", rmId: "sajjal-shaheedi", healthState: "at-risk" },
  { id: "bayhealth", name: "Bayhealth, Inc", tier: "Mid", rmId: "ameer-ali", healthState: "healthy" },
  { id: "denver-wellness", name: "Denver Wellness Associates", tier: "Mid", rmId: "ameer-ali", healthState: "churn-signal" },
  { id: "dr-dental", name: "Dr. Dental", tier: "Mid", rmId: "ameer-ali", healthState: "healthy" },
  { id: "green-security", name: "Green Security LLC", tier: "Mid", rmId: "ameer-ali", healthState: "healthy" },
  { id: "palm-primary-care", name: "Palm Primary Care Texas", tier: "Mid", rmId: "sidra-zia", healthState: "healthy" },
  // SMB
  { id: "navaderm", name: "NAVADERM", tier: "SMB", rmId: "mubeen-sohail", healthState: "healthy" },
  { id: "dmv-allergy-asthma", name: "DMV Allergy & Asthma", tier: "SMB", rmId: "sajjal-shaheedi", healthState: "healthy" },
  { id: "vegas-vascular", name: "Vegas Vascular Specialists", tier: "SMB", rmId: "akash-tahir", healthState: "healthy" },
  { id: "manhattan-restorative", name: "Manhattan Restorative Health Sciences", tier: "SMB", rmId: "yozeline-candia", healthState: "churn-signal" },
  // Tertiary (storyboard anchor; SFDC Account.Name "Cirventis", alias HelixVM)
  { id: "cirventis", name: "Cirventis", tier: "Mid", rmId: "sajjal-shaheedi", healthState: "at-risk" },
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

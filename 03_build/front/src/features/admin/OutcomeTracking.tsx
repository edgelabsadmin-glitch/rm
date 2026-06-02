/*
 * Admin — Outcome Tracking. Closed-loop view: did Pulse's proposed actions
 * lead to good business outcomes? Revenue protected, revenue added, approval
 * rate, and per-account outcome timeline. All demo data — live wiring Week 4.
 */
import { CheckCircle2, XCircle, Clock3, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Decision = "Approved" | "Modified" | "Rejected";
type Outcome  = "Renewal Won" | "Expansion Closed" | "Churn Prevented" | "Reference Done" | "Meeting Booked" | "Churned" | "In Progress";

interface OutcomeRow {
  id: string;
  account: string;
  tier: string;
  signal: string;
  proposedDate: string;
  decision: Decision;
  daysToDecide: number | null;
  outcome: Outcome;
  revenueImpact: number | null;   // positive = gain, negative = loss, null = TBD
}

const ROWS: OutcomeRow[] = [
  { id: "o1",  account: "DHR Health Clinics",        tier: "Strategic", signal: "Churn Risk Escalation",  proposedDate: "May 2",   decision: "Approved",  daysToDecide: 2,    outcome: "Renewal Won",      revenueImpact:  760_000 },
  { id: "o2",  account: "Cirventis",                 tier: "Strategic", signal: "Renewal Window Alert",   proposedDate: "May 5",   decision: "Approved",  daysToDecide: 3,    outcome: "Renewal Won",      revenueImpact:  480_000 },
  { id: "o3",  account: "Bayhealth",                 tier: "Growth",    signal: "Expansion Opportunity",  proposedDate: "May 8",   decision: "Approved",  daysToDecide: 1,    outcome: "In Progress",      revenueImpact:  null    },
  { id: "o4",  account: "NAVADERM",                  tier: "Core",      signal: "Reference Candidate",    proposedDate: "May 9",   decision: "Approved",  daysToDecide: 1,    outcome: "Reference Done",   revenueImpact:  0       },
  { id: "o5",  account: "Mendota Insurance",         tier: "Growth",    signal: "EBR Follow-up Needed",   proposedDate: "May 11",  decision: "Approved",  daysToDecide: 4,    outcome: "Meeting Booked",   revenueImpact:  null    },
  { id: "o6",  account: "Manhattan Restorative",     tier: "Growth",    signal: "Churn Risk Escalation",  proposedDate: "Apr 28",  decision: "Rejected",  daysToDecide: null, outcome: "Churned",          revenueImpact: -320_000 },
  { id: "o7",  account: "Helix Labs",                tier: "Strategic", signal: "Expansion Opportunity",  proposedDate: "May 12",  decision: "Modified",  daysToDecide: 5,    outcome: "In Progress",      revenueImpact:  null    },
  { id: "o8",  account: "BrightPath Therapy",        tier: "Core",      signal: "Renewal Window Alert",   proposedDate: "May 14",  decision: "Approved",  daysToDecide: 2,    outcome: "Churn Prevented",  revenueImpact:  210_000 },
  { id: "o9",  account: "Coastal Orthopedics",       tier: "Growth",    signal: "Silent Account",         proposedDate: "May 15",  decision: "Approved",  daysToDecide: 1,    outcome: "Meeting Booked",   revenueImpact:  null    },
  { id: "o10", account: "Skyline Medical Partners",  tier: "Strategic", signal: "Renewal Window Alert",   proposedDate: "May 16",  decision: "Approved",  daysToDecide: 3,    outcome: "In Progress",      revenueImpact:  null    },
];

const DECISION_STYLE: Record<Decision, string> = {
  Approved: "bg-green-50 text-green-700",
  Modified: "bg-amber-50 text-amber-700",
  Rejected: "bg-risk-high-bg text-risk-high-fg",
};

function OutcomeChip({ outcome }: { outcome: Outcome }) {
  const map: Record<Outcome, { cls: string; icon: React.ReactNode }> = {
    "Renewal Won":      { cls: "bg-green-50 text-green-700",        icon: <CheckCircle2 className="h-3 w-3" /> },
    "Churn Prevented":  { cls: "bg-green-50 text-green-700",        icon: <CheckCircle2 className="h-3 w-3" /> },
    "Expansion Closed": { cls: "bg-green-50 text-green-700",        icon: <ArrowUpRight className="h-3 w-3" /> },
    "Reference Done":   { cls: "bg-brand-muted text-brand",         icon: <CheckCircle2 className="h-3 w-3" /> },
    "Meeting Booked":   { cls: "bg-brand-muted text-brand",         icon: <CheckCircle2 className="h-3 w-3" /> },
    "Churned":          { cls: "bg-risk-high-bg text-risk-high-fg", icon: <XCircle      className="h-3 w-3" /> },
    "In Progress":      { cls: "bg-surface-sidebar text-ink-secondary", icon: <Clock3   className="h-3 w-3" /> },
  };
  const { cls, icon } = map[outcome];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", cls)}>
      {icon}{outcome}
    </span>
  );
}

function fmt(n: number | null): string {
  if (n === null) return "—";
  if (n === 0) return "$0";
  const abs = Math.abs(n);
  const s = abs >= 1_000_000 ? `$${(abs / 1_000_000).toFixed(1)}M` : `$${Math.round(abs / 1000)}K`;
  return n < 0 ? `-${s}` : `+${s}`;
}

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="rounded-2xl border border-line-subtle bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-ink-secondary">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold", accent ?? "text-ink-primary")}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-muted">{sub}</p>}
    </div>
  );
}

const totalProposed  = ROWS.length;
const approved       = ROWS.filter((r) => r.decision !== "Rejected").length;
const approvalRate   = Math.round((approved / totalProposed) * 100);
const revenueProtected = ROWS.filter((r) => (r.revenueImpact ?? 0) > 0).reduce((s, r) => s + r.revenueImpact!, 0);
const revenueLost      = ROWS.filter((r) => (r.revenueImpact ?? 0) < 0).reduce((s, r) => s + r.revenueImpact!, 0);

export function OutcomeTracking() {
  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Actions Proposed"  value={String(totalProposed)}             sub="last 30 days" />
        <StatCard label="RM Approval Rate"  value={`${approvalRate}%`}                sub={`${approved} approved or modified`} />
        <StatCard label="Revenue Protected" value={fmt(revenueProtected)}             sub="renewals won + churn prevented" accent="text-green-600" />
        <StatCard label="Revenue at Risk"   value={fmt(Math.abs(revenueLost))}        sub="from rejected / ignored signals" accent="text-risk-high-fg" />
      </div>

      {/* Timeline table */}
      <div className="overflow-hidden rounded-3xl border border-line-subtle bg-white">
        <div className="border-b border-line-subtle px-6 py-4">
          <h2 className="text-sm font-semibold text-ink-primary">Action outcomes</h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            Closed-loop tracking — revenue impact updated as outcomes resolve.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line-subtle bg-surface-sidebar text-left text-xs font-medium uppercase tracking-[0.12em] text-ink-secondary">
              <th className="px-6 py-3">Account</th>
              <th className="px-4 py-3">Tier</th>
              <th className="px-4 py-3">Signal</th>
              <th className="px-4 py-3">Proposed</th>
              <th className="px-4 py-3">Decision</th>
              <th className="px-4 py-3">Days</th>
              <th className="px-4 py-3">Outcome</th>
              <th className="px-4 py-3 text-right">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r, i) => (
              <tr key={r.id} className={cn("border-b border-line-subtle last:border-0 text-sm", i % 2 === 0 ? "" : "bg-surface-sidebar/40")}>
                <td className="px-6 py-3 font-medium text-ink-primary">{r.account}</td>
                <td className="px-4 py-3 text-xs text-ink-muted">{r.tier}</td>
                <td className="px-4 py-3 text-ink-secondary">{r.signal}</td>
                <td className="px-4 py-3 text-ink-muted">{r.proposedDate}</td>
                <td className="px-4 py-3">
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", DECISION_STYLE[r.decision])}>
                    {r.decision}
                  </span>
                </td>
                <td className="px-4 py-3 text-ink-muted font-mono text-xs">
                  {r.daysToDecide !== null ? `${r.daysToDecide}d` : "—"}
                </td>
                <td className="px-4 py-3"><OutcomeChip outcome={r.outcome} /></td>
                <td className={cn("px-4 py-3 text-right font-mono text-xs font-medium",
                  r.revenueImpact === null ? "text-ink-muted" :
                  r.revenueImpact > 0 ? "text-green-600" : "text-risk-high-fg"
                )}>
                  {fmt(r.revenueImpact)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

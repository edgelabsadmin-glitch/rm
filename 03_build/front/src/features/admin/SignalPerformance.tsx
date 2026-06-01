/*
 * Admin — Signal Performance. Shows how each AI signal type is performing:
 * fire rate, precision (% of signals that led to correct RM actions),
 * avg RM rating, and weekly trend. All demo data — live wiring in Week 4.
 */
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface Signal {
  id: string;
  name: string;
  type: "Risk" | "Renewal" | "Growth" | "Engagement";
  firesPerWeek: number;
  precision: number;      // 0–100
  rmRating: number;       // 0–5
  trend: "up" | "down" | "flat";
  lastFired: string;
  totalFires: number;
}

const SIGNALS: Signal[] = [
  { id: "s1", name: "Renewal Window Alert",       type: "Renewal",    firesPerWeek: 12, precision: 91, rmRating: 4.6, trend: "flat", lastFired: "Today",      totalFires: 284 },
  { id: "s2", name: "Reference Candidate",         type: "Growth",     firesPerWeek: 4,  precision: 94, rmRating: 4.7, trend: "up",   lastFired: "Yesterday",  totalFires: 97  },
  { id: "s3", name: "EBR Follow-up Needed",        type: "Engagement", firesPerWeek: 9,  precision: 88, rmRating: 4.4, trend: "flat", lastFired: "Today",      totalFires: 213 },
  { id: "s4", name: "Churn Risk Escalation",       type: "Risk",       firesPerWeek: 8,  precision: 82, rmRating: 4.2, trend: "up",   lastFired: "Today",      totalFires: 189 },
  { id: "s5", name: "Silent Account",              type: "Engagement", firesPerWeek: 6,  precision: 74, rmRating: 4.0, trend: "up",   lastFired: "2 days ago", totalFires: 156 },
  { id: "s6", name: "Talent Satisfaction Drop",    type: "Risk",       firesPerWeek: 3,  precision: 71, rmRating: 3.9, trend: "flat", lastFired: "3 days ago", totalFires: 88  },
  { id: "s7", name: "Expansion Opportunity",       type: "Growth",     firesPerWeek: 5,  precision: 67, rmRating: 3.8, trend: "down", lastFired: "Yesterday",  totalFires: 124 },
];

const TYPE_COLOR: Record<Signal["type"], string> = {
  Risk:       "bg-risk-high-bg text-risk-high-fg",
  Renewal:    "bg-brand-muted text-brand",
  Growth:     "bg-green-50 text-green-700",
  Engagement: "bg-amber-50 text-amber-700",
};

function PrecisionBar({ pct }: { pct: number }) {
  const color = pct >= 85 ? "bg-green-500" : pct >= 70 ? "bg-brand" : "bg-amber-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-surface-track">
        <div className={cn("h-1.5 rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-ink-primary">{pct}%</span>
    </div>
  );
}

function TrendIcon({ trend }: { trend: Signal["trend"] }) {
  if (trend === "up")   return <TrendingUp   className="h-4 w-4 text-green-500" />;
  if (trend === "down") return <TrendingDown className="h-4 w-4 text-risk-high-fg" />;
  return <Minus className="h-4 w-4 text-ink-muted" />;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line-subtle bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-ink-secondary">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink-primary">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-muted">{sub}</p>}
    </div>
  );
}

const avgPrecision = Math.round(SIGNALS.reduce((s, x) => s + x.precision, 0) / SIGNALS.length);
const highConf = SIGNALS.filter((s) => s.precision >= 80).length;
const totalFires = SIGNALS.reduce((s, x) => s + x.firesPerWeek, 0);

export function SignalPerformance() {
  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Active Signals"       value={String(SIGNALS.length)}  sub="across all skill types" />
        <StatCard label="Avg Precision"        value={`${avgPrecision}%`}       sub="signals → correct actions" />
        <StatCard label="High Confidence"      value={`${highConf} / ${SIGNALS.length}`} sub="precision ≥ 80%" />
        <StatCard label="Fires This Week"      value={String(totalFires)}       sub="total across all signals" />
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-3xl border border-line-subtle bg-white">
        <div className="border-b border-line-subtle px-6 py-4">
          <h2 className="text-sm font-semibold text-ink-primary">Signal breakdown</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Precision = proportion of fires rated correct or approved by RMs</p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line-subtle bg-surface-sidebar text-left text-xs font-medium uppercase tracking-[0.12em] text-ink-secondary">
              <th className="px-6 py-3">Signal</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Fires / wk</th>
              <th className="px-4 py-3">Precision</th>
              <th className="px-4 py-3">RM Rating</th>
              <th className="px-4 py-3">Trend</th>
              <th className="px-4 py-3">Last fired</th>
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {SIGNALS.map((s, i) => (
              <tr key={s.id} className={cn("border-b border-line-subtle last:border-0", i % 2 === 0 ? "" : "bg-surface-sidebar/40")}>
                <td className="px-6 py-3 font-medium text-ink-primary">{s.name}</td>
                <td className="px-4 py-3">
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", TYPE_COLOR[s.type])}>
                    {s.type}
                  </span>
                </td>
                <td className="px-4 py-3 text-ink-secondary">{s.firesPerWeek}</td>
                <td className="px-4 py-3"><PrecisionBar pct={s.precision} /></td>
                <td className="px-4 py-3">
                  <span className="font-medium text-ink-primary">{s.rmRating.toFixed(1)}</span>
                  <span className="text-ink-muted"> / 5</span>
                </td>
                <td className="px-4 py-3"><TrendIcon trend={s.trend} /></td>
                <td className="px-4 py-3 text-ink-secondary">{s.lastFired}</td>
                <td className="px-4 py-3 text-right font-mono text-xs text-ink-muted">{s.totalFires}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

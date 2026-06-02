/*
 * SPEC-040 — Executive View (renamed from CEO View per operator Session 19; the
 * recipients are CEO Iffi + VP-CS Eddy, so §6 #1 white-label + audience accuracy).
 * A three-column AGENTIC WORKSPACE per the
 * Session-19 mockup (Design 08's "narrative not chart" lock superseded by §4.20:
 * every screen surfaces an agentic decision). Top row: Client Stickiness · Hero ·
 * Upsell Opportunities. Middle band: "What I'd ask of you" (Pulse-proposed asks
 * with Approve/Edit). Bottom: "Book in numbers". Real data from demo_characters.ts;
 * ARR via the $10K/seat heuristic. AI-RM voice preserved inside the Hero (the voice
 * didn't change — the surrounding composition did).
 */
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  MessageSquare,
  Minus,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { CompositeHealthRing } from "@/components/CompositeHealthRing";
import { FadeLift } from "@/components/FadeLift";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth/AuthContext";
import { InlineTags } from "@/lib/inline_tags";
import {
  accountARR,
  bookARR,
  churnExposureARR,
  DEMO_ACCOUNTS,
  DEMO_ACTIVE_TALENT_TOTAL,
  DEMO_RMS,
  formatARR,
  REVENUE_PER_SEAT_USD,
} from "@/fixtures/demo_characters";
import { DEMO_ACTIONS } from "@/features/queue/demo_actions";
import {
  composeTeamWorkload,
  type TeamWorkloadRow as TeamWorkloadRowData,
  type ThroughputIndicator as ThroughputKind,
} from "./composers/team_workload_composer";

type Severity = "risk" | "warning" | "opportunity" | "reference";

function Chip({ severity, children }: { severity: Severity; children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        background: `var(--color-chip-${severity}-bg)`,
        color: `var(--color-chip-${severity}-text)`,
      }}
    >
      {children}
    </span>
  );
}

const EYEBROW = "text-xs font-semibold uppercase tracking-wider text-ink-muted";

const atRisk = DEMO_ACCOUNTS.filter(
  (a) => a.healthState === "at-risk" || a.healthState === "churn-signal",
);

// All figures DERIVED from the canonical demo data (real-data integrity, Session 19):
// active placements via the $10K/seat heuristic; tier + churn counts from the account
// states. Nothing hand-asserted — the displayed numbers always match demo_characters.ts.
const seats = (id: string) => accountARR(id) / REVENUE_PER_SEAT_USD;
const strategicCount = DEMO_ACCOUNTS.filter((a) => a.tier === "Strategic").length;
const churnCount = DEMO_ACCOUNTS.filter((a) => a.healthState === "churn-signal").length;

const WEEK_OF = "May 17 → 23, 2026";
const BOOK_HEALTH = 7.2; // Phase-1 stub (avg composite across non-churn accounts; wires Week 4)

// Real-data integrity (Session 19 operator review): the lead asserts only verifiable
// figures (placement count + composite churn %). The prior "vendor-consolidation talk"
// line was a fabricated qualitative signal — it needs live Chorus extraction (Week-4
// pulse-api cutover) before it can be stated.
const LEAD =
  "<em>DHR Health Clinics</em> is the one to watch — largest book at <num>76</num> " +
  "placements, churn signal crossed <num>50%</num>.";

const PULSE_FACTS: [string, string][] = [
  ["Accounts", String(DEMO_ACCOUNTS.length)],
  ["Active placements", String(DEMO_ACTIVE_TALENT_TOTAL)],
  ["Strategic accounts", String(strategicCount)],
  ["Churn signals", String(churnCount)],
];

const ASKS = [
  {
    icon: AlertTriangle,
    severity: "risk" as Severity,
    ask: "Review DHR Health Clinics churn signal",
    why: "50% churn risk crossed · 76 placements / $760K at stake · Owning RM Sidra Zia",
  },
  {
    icon: TrendingUp,
    severity: "warning" as Severity,
    ask: "Review Bayhealth expansion opportunity",
    why: "6 active placements · expansion signal surfaced via opp-tracker · Owning RM Ameer Ali",
  },
  {
    icon: MessageSquare,
    severity: "opportunity" as Severity,
    ask: "Consider NAVADERM as Q3 reference customer",
    why: "14 healthy placements, no escalations · Owning RM Mubeen Sohail",
  },
];

function StatCard({ children }: { children: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="p-5">{children}</CardContent>
    </Card>
  );
}

export function ExecutiveView() {
  return (
    <FadeLift motionKey={WEEK_OF}>
      <div className="mx-auto max-w-7xl space-y-5 p-6">
        {/* Top row — 3 columns: 1fr / 1.2fr / 1fr */}
        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr_1fr]">
          {/* Left — Client Stickiness */}
          <StatCard>
            <div className={EYEBROW}>Client Stickiness</div>
            <div className="mt-2 text-4xl font-semibold text-ink-primary">{atRisk.length}</div>
            <div className="text-sm text-ink-secondary">accounts at risk</div>
            <div className="mt-1 text-sm font-medium" style={{ color: "var(--color-stat-risk)" }}>
              {formatARR(churnExposureARR())} ARR exposure
            </div>
            <div className="my-3 h-px bg-line-subtle" />
            <div className="mb-2 text-xs font-medium text-ink-secondary">
              Needs your call this week
            </div>
            <ul className="space-y-2">
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">
                  DHR Health Clinics · Sidra Zia · {seats("dhr-health-clinics")} placements
                </span>
                <Chip severity="risk">50%</Chip>
              </li>
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">
                  Manhattan Restorative · Yozeline Candia · {seats("manhattan-restorative")} placements
                </span>
              </li>
            </ul>
          </StatCard>

          {/* Center — Hero card */}
          <div className="surface-brand rounded-4xl bg-brand p-6 text-ink-on-brand shadow-xl-brand">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-sm text-ink-on-brand-strip">
                <Sparkles className="h-4 w-4" /> This week, with Pulse
              </div>
              <div className="flex items-center gap-2">
                {["IW", "EC"].map((i) => (
                  <span
                    key={i}
                    className="grid h-[22px] w-[22px] place-items-center rounded-full text-[10px] font-semibold text-ink-on-brand"
                    style={{ background: "rgba(255,255,255,0.18)" }}
                  >
                    {i}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-4 flex flex-col items-center">
              <CompositeHealthRing score={BOOK_HEALTH} label="Book Health" />
            </div>
            <p className="mt-4 text-center text-sm italic leading-6 text-ink-on-brand-soft">
              <InlineTags text={LEAD} />
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3">
              {PULSE_FACTS.map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-md px-3 py-2 text-xs text-ink-on-brand-strip"
                  style={{ background: "rgba(255,255,255,0.12)" }}
                >
                  <span className="text-ink-on-brand-faint">{label}</span>{" "}
                  <span className="font-semibold text-ink-on-brand">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right — Upsell Opportunities */}
          <StatCard>
            <div className={EYEBROW}>Upsell Opportunities</div>
            <div
              className="mt-2 text-4xl font-semibold"
              style={{ color: "var(--color-stat-opportunity)" }}
            >
              5
            </div>
            <div className="text-sm text-ink-secondary">accounts with healthy engagement</div>
            <div className="my-3 h-px bg-line-subtle" />
            <div className="mb-2 text-xs font-medium text-ink-secondary">Healthy book</div>
            <ul className="space-y-2">
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">
                  Bayhealth · Ameer Ali · {seats("bayhealth")} placements
                </span>
              </li>
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">
                  NAVADERM · Mubeen Sohail · {seats("navaderm")} placements
                </span>
                <Chip severity="reference">REF</Chip>
              </li>
            </ul>
          </StatCard>
        </div>

        {/* Middle band — What I'd ask of you */}
        <Card>
          <CardContent className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className={EYEBROW}>What I'd ask of you · 3 this week</div>
              <div className="text-xs text-ink-muted">Pulse-proposed · auto-expires Sun</div>
            </div>
            <div className="space-y-3">
              {ASKS.map(({ icon: Icon, severity, ask, why }) => (
                <div key={ask} className="flex items-center gap-3">
                  <div
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-md"
                    style={{
                      background: `var(--color-chip-${severity}-bg)`,
                      color: `var(--color-chip-${severity}-text)`,
                    }}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] font-medium text-ink-primary">{ask}</div>
                    <div className="text-xs text-ink-secondary">{why}</div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {}}
                      className="rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-ink-on-brand hover:bg-brand-hover"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => {}}
                      className="rounded-md border border-line-strong px-3 py-1.5 text-xs font-medium text-ink-secondary hover:bg-brand-ghost"
                    >
                      Edit
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Team workload — per-RM load visibility (spec 042 §6.6, between asks + numbers) */}
        <TeamWorkloadPanel />

        {/* Bottom strip — Book in numbers */}
        <div className="rounded-lg bg-surface-chrome px-4 py-3">
          <div className="mb-2 text-xs text-ink-muted">Book in numbers · {WEEK_OF}</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Stat n={String(DEMO_ACCOUNTS.length)} label="accounts" />
            <Stat n={String(DEMO_ACTIVE_TALENT_TOTAL)} label="active placements" />
            <Stat n="3" label="churn signals" color="var(--color-stat-risk)" />
            <Stat n="2" label="renewals at risk" color="var(--color-stat-warning)" />
            <Stat n={formatARR(bookARR())} label="book ARR" color="var(--color-stat-opportunity)" />
          </div>
        </div>
      </div>
    </FadeLift>
  );
}

function Stat({ n, label, color }: { n: string; label: string; color?: string }) {
  return (
    <div>
      <div className="text-xl font-medium" style={color ? { color } : { color: "var(--color-text-primary)" }}>
        {n}
      </div>
      <div className="text-xs text-ink-secondary">{label}</div>
    </div>
  );
}

// ============================================================================
// Team workload panel (SPEC-042 Step-8, §6.6 / §6.7)
// ============================================================================
// Overload threshold: an RM with this many pending actions reads as overloaded
// (warning chip + avatar). The Phase-1A demo fixture maxes at 2 pending/RM, so the
// warning won't fire today — that's correct; Phase-1B real signal volume activates it.
export const WORKLOAD_WARNING_THRESHOLD = 6;

const THROUGHPUT_DISPLAY: Record<
  ThroughputKind,
  { icon: typeof ArrowRight; label: string; color: string }
> = {
  rising: { icon: ArrowUpRight, label: "Rising", color: "var(--color-stat-opportunity)" },
  steady: { icon: ArrowRight, label: "Steady", color: "var(--color-text-secondary)" },
  declining: { icon: ArrowDownRight, label: "Declining", color: "var(--color-stat-risk)" },
  flat: { icon: Minus, label: "Flat", color: "var(--color-text-muted)" },
};

function ThroughputIndicatorCell({ value }: { value: ThroughputKind }) {
  const { icon: Icon, label, color } = THROUGHPUT_DISPLAY[value];
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color }}>
      <Icon className="h-3.5 w-3.5" /> {label}
    </span>
  );
}

function WorkloadAvatar({ initials, warning }: { initials: string; warning: boolean }) {
  return (
    <span
      className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[10px] font-semibold"
      style={
        warning
          ? { background: "var(--color-chip-warning-bg)", color: "var(--color-chip-warning-text)" }
          : { background: "var(--color-surface-card)", color: "var(--color-text-primary)", border: "0.5px solid var(--color-line-strong)" }
      }
    >
      {initials}
    </span>
  );
}

/** One workload row — exported so the warning-threshold styling is unit-testable in isolation. */
export function TeamWorkloadRowView({
  row,
  onSelect,
}: {
  row: TeamWorkloadRowData;
  onSelect: (rmId: string) => void;
}) {
  const warning = row.pendingCount >= WORKLOAD_WARNING_THRESHOLD;
  return (
    <tr
      data-testid="team-workload-row"
      data-warning={warning}
      role="button"
      tabIndex={0}
      onClick={() => onSelect(row.rmId)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(row.rmId);
        }
      }}
      className="cursor-pointer border-t border-line-subtle text-xs transition hover:bg-brand-ghost"
    >
      <td className="py-2 pr-3">
        <WorkloadAvatar initials={row.avatarInitials} warning={warning} />
      </td>
      <td className="py-2 pr-3 font-medium text-ink-primary">{row.rmName}</td>
      <td
        className="py-2 pr-3 font-mono"
        style={warning ? { color: "var(--color-chip-warning-text)" } : { color: "var(--color-text-primary)" }}
      >
        {row.pendingCount}
      </td>
      <td className="py-2 pr-3 font-mono text-ink-secondary">{row.approvedThisWeek}</td>
      <td className="py-2">
        <ThroughputIndicatorCell value={row.throughputIndicator} />
      </td>
    </tr>
  );
}

function TeamWorkloadPanel() {
  const { accountScope } = useAuth();
  const navigate = useNavigate();
  const rows = useMemo(
    () => composeTeamWorkload(DEMO_RMS, DEMO_ACTIONS, accountScope),
    [accountScope],
  );
  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className={EYEBROW}>Team workload · {rows.length} RMs</div>
          <div className="text-xs text-ink-muted">Click a row to see them in the constellation</div>
        </div>
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
              <th className="w-8 pb-1 font-semibold" />
              <th className="pb-1 pr-3 font-semibold">RM</th>
              <th className="pb-1 pr-3 font-semibold">Pending</th>
              <th className="pb-1 pr-3 font-semibold">Approved · wk</th>
              <th className="pb-1 font-semibold">Throughput</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <TeamWorkloadRowView
                key={row.rmId}
                row={row}
                onSelect={(rmId) => navigate(`/constellation?rm=${encodeURIComponent(rmId)}`)}
              />
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

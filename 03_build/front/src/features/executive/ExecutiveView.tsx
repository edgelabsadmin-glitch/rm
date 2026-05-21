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
import { AlertTriangle, MessageSquare, Sparkles, TrendingUp } from "lucide-react";
import { CompositeHealthRing } from "@/components/CompositeHealthRing";
import { FadeLift } from "@/components/FadeLift";
import { Card, CardContent } from "@/components/ui/card";
import { InlineTags } from "@/lib/inline_tags";
import {
  bookARR,
  churnExposureARR,
  DEMO_ACCOUNTS,
  DEMO_ACTIVE_TALENT_TOTAL,
  formatARR,
} from "@/fixtures/demo_characters";

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

const WEEK_OF = "May 17 → 23, 2026";
const BOOK_HEALTH = 7.2; // Phase-1 stub (avg composite across non-churn accounts; wires Week 4)

const LEAD =
  "<em>DHR Health Clinics</em> is the one to watch — largest book, churn crossed " +
  "<num>50%</num>. Two of your accounts are seeing <bad>vendor-consolidation</bad> talk.";

const PULSE_FACTS: [string, string][] = [
  ["Accounts", String(DEMO_ACCOUNTS.length)],
  ["Active placements", String(DEMO_ACTIVE_TALENT_TOTAL)],
  ["Renewals 30d", "4"],
  ["Open opportunities", "7"],
];

const ASKS = [
  {
    icon: AlertTriangle,
    severity: "risk" as Severity,
    ask: "Escalate DHR Health Clinics renewal — Sidra needs air cover.",
    why: "Pulse will draft talking points + book Thursday slot · 76 placements / $760K at stake.",
  },
  {
    icon: TrendingUp,
    severity: "warning" as Severity,
    ask: "Route Bayhealth expansion to Eddy — 12 nurses identified.",
    why: "Ameer surfaced a 12-nurse need; ready for VP-CS framing.",
  },
  {
    icon: MessageSquare,
    severity: "opportunity" as Severity,
    ask: "Make NAVADERM the Q3 reference customer.",
    why: "14 healthy placements, no escalations — Mubeen's quiet win.",
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
                <span className="text-ink-primary">DHR Health Clinics · Sidra · 76 placements</span>
                <Chip severity="risk">50%</Chip>
              </li>
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">Manhattan Restorative · Yozeline · 10 placements</span>
                <Chip severity="risk">90%</Chip>
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
            <div className="text-sm text-ink-secondary">accounts with expansion signals</div>
            <div className="mt-1 text-sm text-ink-secondary">2 ready to push · 3 in early stage</div>
            <div className="my-3 h-px bg-line-subtle" />
            <div className="mb-2 text-xs font-medium text-ink-secondary">Ready to push</div>
            <ul className="space-y-2">
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">Bayhealth · Ameer · +12 nurses</span>
                <Chip severity="warning">+12</Chip>
              </li>
              <li className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-primary">NAVADERM · Mubeen · reference-ask</span>
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

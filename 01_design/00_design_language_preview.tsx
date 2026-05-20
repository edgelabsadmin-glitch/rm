import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Bell,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
  UsersRound,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const accounts = [
  {
    name: "Mendota Health",
    meeting: "EBR tomorrow, 10:30 AM",
    score: 7.8,
    risk: "Medium",
    trend: "+0.6 this month",
    signals: ["Burnout mentions easing", "Recognition gap still recurring", "2 open case themes"],
    talent: "18 active talent",
  },
  {
    name: "Helix Labs",
    meeting: "Renewal sync in 3 days",
    score: 6.4,
    risk: "High",
    trend: "-1.1 after AI rollout",
    signals: ["AI displacement concern", "Pay concern from senior talent", "Champion quiet for 21 days"],
    talent: "11 active talent",
  },
  {
    name: "Vertex Group",
    meeting: "No meeting scheduled",
    score: 8.9,
    risk: "Low",
    trend: "+0.3 stable",
    signals: ["Strong ambassador pool", "Positive performer feedback", "Adoption rising"],
    talent: "23 active talent",
  },
];

const actionItems = [
  {
    title: "Send renewal-risk note to Helix sponsor",
    detail: "References 3 verified signals from Chorus, RM outreach, and talent check-ins.",
    owner: "RM approval",
    tone: "Needs review",
  },
  {
    title: "Prep Mendota EBR talking points",
    detail: "Top issues, positive performers, and suggested stakeholder questions are ready.",
    owner: "Ready",
    tone: "Prepared",
  },
  {
    title: "Route coaching signal to Talent Dev",
    detail: "One talent profile shows long-term growth concern and manager-fit friction.",
    owner: "Suggested handoff",
    tone: "Care action",
  },
];

const pulseFacts = [
  "Temporal account memory",
  "Evidence-backed signals",
  "RM approval before action",
  "Customer + talent health",
];

function Pill({ children, active = false }) {
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-medium ${
        active
          ? "border-[#6B46C1]/25 bg-[#6B46C1]/10 text-[#6B46C1]"
          : "border-slate-200 bg-white text-slate-600"
      }`}
    >
      {children}
    </span>
  );
}

function RiskBadge({ risk }) {
  const styles = {
    High: "bg-rose-50 text-rose-700 border-rose-200",
    Medium: "bg-amber-50 text-amber-700 border-amber-200",
    Low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[risk]}`}>{risk}</span>;
}

export default function PulseRMDesign() {
  const [selected, setSelected] = useState(accounts[1]);

  const compositeAngle = useMemo(() => `${Math.round((selected.score / 10) * 270)}deg`, [selected]);

  return (
    <div className="min-h-screen bg-[#FAFAFA] p-6 text-slate-950">
      <div className="mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-slate-200 bg-[#F5F5F7] shadow-2xl shadow-slate-200/70">
        <header className="flex items-center justify-between border-b border-slate-100 px-7 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#6B46C1] text-white shadow-lg shadow-[#6B46C1]/20">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">Pulse</div>
              <div className="text-xs text-slate-500">Relationship intelligence for RMs</div>
            </div>
          </div>

          <div className="hidden flex-1 justify-center px-10 lg:flex">
            <div className="flex w-full max-w-xl items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-500">
              <Search className="h-4 w-4" />
              Ask: “Prep me for Helix renewal” or “Who raised pay concerns?”
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" className="rounded-full border-[#6B46C1]/25 text-[#6B46C1] hover:bg-[#6B46C1]/5">
              <Bell className="mr-2 h-4 w-4" /> Queue
            </Button>
            <div className="h-10 w-10 rounded-full bg-slate-900 text-center text-sm font-semibold leading-10 text-white">DZ</div>
          </div>
        </header>

        <main className="grid grid-cols-12 gap-0">
          <aside className="col-span-12 border-b border-slate-100 bg-slate-50/80 p-5 lg:col-span-3 lg:border-b-0 lg:border-r">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Accounts</h2>
              <Pill active>Today</Pill>
            </div>

            <div className="space-y-3">
              {accounts.map((account) => (
                <button
                  key={account.name}
                  onClick={() => setSelected(account)}
                  className={`w-full rounded-3xl border p-4 text-left transition ${
                    selected.name === account.name
                      ? "border-[#6B46C1]/35 bg-white shadow-lg shadow-slate-200"
                      : "border-transparent bg-white/70 hover:border-[#6B46C1]/15 hover:bg-white"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold tracking-tight">{account.name}</div>
                      <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                        <CalendarDays className="h-3.5 w-3.5" /> {account.meeting}
                      </div>
                    </div>
                    <RiskBadge risk={account.risk} />
                  </div>
                  <div className="mt-4 flex items-center justify-between text-xs">
                    <span className="text-slate-500">Composite health</span>
                    <span className="font-semibold text-slate-900">{account.score}/10</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-[#6B46C1]" style={{ width: `${account.score * 10}%` }} />
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="col-span-12 p-6 lg:col-span-6">
            <motion.div
              key={selected.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="space-y-5"
            >
              <div className="rounded-[2rem] bg-[#6B46C1] p-6 text-white shadow-xl shadow-[#6B46C1]/20">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="mb-2 flex items-center gap-2 text-sm text-white/80">
                      <Sparkles className="h-4 w-4" /> AI briefing, grounded in account memory
                    </div>
                    <h1 className="text-3xl font-semibold tracking-tight">{selected.name}</h1>
                    <p className="mt-2 max-w-xl text-sm leading-6 text-white/85">
                      Pulse is prioritizing evidence, next best action, and stakeholder context. No auto-send. Every customer-facing move waits for RM approval.
                    </p>
                  </div>
                  <div className="rounded-3xl bg-white/12 p-4 backdrop-blur">
                    <div
                      className="grid h-28 w-28 place-items-center rounded-full"
                      style={{ background: `conic-gradient(white ${compositeAngle}, rgba(255,255,255,.18) 0deg)` }}
                    >
                      <div className="grid h-20 w-20 place-items-center rounded-full bg-[#4B2E91]">
                        <div className="text-center">
                          <div className="text-2xl font-bold">{selected.score}</div>
                          <div className="text-[10px] uppercase tracking-widest text-white/65">Health</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 grid gap-3 md:grid-cols-4">
                  {pulseFacts.map((fact) => (
                    <div key={fact} className="rounded-2xl border border-white/15 bg-white/10 px-3 py-3 text-xs text-white/85">
                      {fact}
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <Card className="rounded-3xl border-slate-100 shadow-sm">
                  <CardContent className="p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="font-semibold">Signal vector</h3>
                      <Pill>{selected.trend}</Pill>
                    </div>
                    {["Engagement", "Satisfaction", "Retention safety", "Growth orientation"].map((label, index) => (
                      <div key={label} className="mb-4 last:mb-0">
                        <div className="mb-1 flex justify-between text-xs text-slate-500">
                          <span>{label}</span>
                          <span>{Math.max(54, Math.round(selected.score * 10 - index * 7))}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className="h-2 rounded-full bg-[#6B46C1]"
                            style={{ width: `${Math.max(54, Math.round(selected.score * 10 - index * 7))}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-slate-100 shadow-sm">
                  <CardContent className="p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="font-semibold">Verified themes</h3>
                      <ShieldCheck className="h-5 w-5 text-[#6B46C1]" />
                    </div>
                    <div className="space-y-3">
                      {selected.signals.map((signal) => (
                        <div key={signal} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-3">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 text-[#6B46C1]" />
                          <div className="text-sm leading-5 text-slate-700">{signal}</div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-3xl border-slate-100 shadow-sm">
                <CardContent className="p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-semibold">Meeting brief</h3>
                    <Button size="sm" className="rounded-full bg-[#6B46C1] hover:bg-[#5B35B1]">Generate brief</Button>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl bg-[#6B46C1]/7 p-4">
                      <FileText className="mb-3 h-5 w-5 text-[#6B46C1]" />
                      <div className="text-sm font-semibold">Top 3 issues</div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">Theme-ranked, with source snippets and timestamps.</p>
                    </div>
                    <div className="rounded-2xl bg-[#6B46C1]/7 p-4">
                      <UsersRound className="mb-3 h-5 w-5 text-[#6B46C1]" />
                      <div className="text-sm font-semibold">At-risk talent</div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">Talent-side context appears beside customer health.</p>
                    </div>
                    <div className="rounded-2xl bg-[#6B46C1]/7 p-4">
                      <MessageSquareText className="mb-3 h-5 w-5 text-[#6B46C1]" />
                      <div className="text-sm font-semibold">Talk tracks</div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">Suggested questions, not synthetic “AI voice”.</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </section>

          <aside className="col-span-12 border-t border-slate-100 bg-slate-50/70 p-5 lg:col-span-3 lg:border-l lg:border-t-0">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Action Queue</h2>
              <Pill active>3 pending</Pill>
            </div>

            <div className="space-y-3">
              {actionItems.map((item) => (
                <Card key={item.title} className="rounded-3xl border-slate-100 bg-white shadow-sm">
                  <CardContent className="p-4">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div className="rounded-2xl bg-[#6B46C1]/10 p-2 text-[#6B46C1]">
                        {item.tone === "Care action" ? <UserRoundCheck className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                    <div className="text-sm font-semibold leading-5">{item.title}</div>
                    <p className="mt-2 text-xs leading-5 text-slate-500">{item.detail}</p>
                    <div className="mt-4 flex items-center justify-between">
                      <Pill>{item.owner}</Pill>
                      <Button size="sm" variant="ghost" className="rounded-full text-[#6B46C1] hover:bg-[#6B46C1]/7">Review</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="mt-5 rounded-3xl border border-[#6B46C1]/15 bg-white p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <ShieldCheck className="h-4 w-4 text-[#6B46C1]" /> Trust layer
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Show the source, date, confidence, and owner for every insight. Keep the RM in control of outreach.
              </p>
            </div>
          </aside>
        </main>
      </div>
    </div>
  );
}

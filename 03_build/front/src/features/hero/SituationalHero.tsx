/*
 * SPEC-036 — Situational Hero card (Tier-0 §8.7). Accepts AccountHealthDTO from
 * AccountWorkspace (which owns the single useAccountHealth fetch). Falls back to a
 * loading skeleton while data is in flight.
 */
import { Sparkles } from "lucide-react";
import { CompositeHealthRing } from "@/components/CompositeHealthRing";
import { FadeLift } from "@/components/FadeLift";
import { formatARR } from "@/fixtures/demo_characters";
import type { AccountHealthDTO } from "@/lib/api";
import { PULSE_FACTS } from "./fixtures";

interface Props {
  account: AccountHealthDTO | undefined;
}

export function SituationalHero({ account }: Props) {
  if (!account) {
    return (
      <div className="animate-pulse rounded-4xl bg-brand/20 h-64" />
    );
  }

  return (
    <FadeLift motionKey={account.account_id}>
      <div className="surface-brand rounded-4xl bg-brand p-6 text-ink-on-brand shadow-xl-brand">
        {/* Top: AI briefing + account name + positioning. */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-ink-on-brand-strip">
            <Sparkles className="h-4 w-4" /> AI briefing, grounded in account memory
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">{account.name}</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ink-on-brand-soft">
            {account.positioning}
          </p>
        </div>

        {/* Middle-lower: centered composite-health donut. */}
        <div className="mt-6 flex justify-center">
          <div className="rounded-3xl border border-surface-glass-border bg-surface-glass-light p-4">
            <CompositeHealthRing score={account.composite_health} />
          </div>
        </div>

        {/* Bottom: 4 Pulse-fact pills + ARR pill. */}
        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          {PULSE_FACTS.map((fact) => (
            <div
              key={fact}
              className="rounded-2xl border border-surface-glass-border bg-surface-glass-light px-3 py-3 text-xs text-ink-on-brand-strip"
            >
              {fact}
            </div>
          ))}
          <div className="rounded-2xl border border-surface-glass-border bg-surface-glass-light px-3 py-3 text-xs text-ink-on-brand-strip">
            <span className="text-ink-on-brand-faint">Book value</span>{" "}
            <span className="font-mono font-semibold text-ink-on-brand">
              {formatARR(account.arr_usd)}
            </span>
          </div>
        </div>
      </div>
    </FadeLift>
  );
}

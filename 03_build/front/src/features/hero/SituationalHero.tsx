/*
 * SPEC-036 — Situational Hero card (Tier-0 §8.7, one of the two heroes per §6 #25).
 * Saturated Edge-Purple card, white type, the §6-#26 tinted-shadow signature, the
 * 270° Composite Health Ring inset in a glass tile, and the four static Pulse-Facts
 * pills. Binds to the selected account (Helix Labs by default). Fade-and-lift on
 * account switch (Tier-0 §7), keyed by account id.
 *
 * Mock data now (fixtures.ts); GET /accounts/{id}/health wires in Week 4 — see the
 * contract + normalization flag in fixtures.ts.
 */
import { Sparkles } from "lucide-react";
import { CompositeHealthRing } from "@/components/CompositeHealthRing";
import { FadeLift } from "@/components/FadeLift";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { getAccountHealthFixture, PULSE_FACTS } from "./fixtures";

export function SituationalHero() {
  const { selectedAccountId } = useSelectedAccount();
  const account = getAccountHealthFixture(selectedAccountId);

  return (
    <FadeLift motionKey={account.account_id}>
      <div className="surface-brand rounded-4xl bg-brand p-6 text-ink-on-brand shadow-xl-brand">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm text-ink-on-brand-strip">
              <Sparkles className="h-4 w-4" /> AI briefing, grounded in account memory
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">{account.name}</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-ink-on-brand-soft">
              {account.positioning}
            </p>
          </div>
          <div className="rounded-3xl border border-surface-glass-border bg-surface-glass-light p-4">
            <CompositeHealthRing score={account.composite_health} />
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-4">
          {PULSE_FACTS.map((fact) => (
            <div
              key={fact}
              className="rounded-2xl border border-surface-glass-border bg-surface-glass-light px-3 py-3 text-xs text-ink-on-brand-strip"
            >
              {fact}
            </div>
          ))}
        </div>
      </div>
    </FadeLift>
  );
}

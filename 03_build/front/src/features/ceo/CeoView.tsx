/*
 * SPEC-040 — CEO View (/ceo). Pulse's most-brand-moment surface (Design 08): a
 * weekly first-person narrative read for leadership, NOT a dashboard. Single column,
 * mobile-readable (Q92). Renders fixture data; the LLM composer + email + static-HTML
 * fallback land later. Voice + inline-tag rendering per Design 08 + Tier-0 §10.
 *
 * Composition per the spec-040 directive (req 3): purple header band → What's emerging
 * → Where talent matters → What I'd ask of you (trust-layer; skipped when no asks) →
 * footer attribution. (Flagged: Design 08 / storyboard also lock a health-pulse bar
 * chart + top-3-stories cards + numbers strip — folded out here per the directive.)
 */
import { Sparkles } from "lucide-react";
import { FadeLift } from "@/components/FadeLift";
import { TrustLayerCallout } from "@/components/TrustLayerCallout";
import { Card, CardContent } from "@/components/ui/card";
import { InlineTags } from "@/lib/inline_tags";
import { getCeoWeekly } from "./fixtures";

function initials(s: string): string {
  return s
    .replace(/[·.]/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function CeoView() {
  const w = getCeoWeekly();

  return (
    <FadeLift motionKey={w.week_of}>
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        {/* Header band — the purple hero (Tier-0 §8.7 treatment; tinted shadow). */}
        <div className="surface-brand rounded-4xl bg-brand p-6 text-ink-on-brand shadow-xl-brand">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-sm text-ink-on-brand-strip">
                <Sparkles className="h-4 w-4" /> This week, with Pulse
              </div>
              <div className="mt-1 text-2xl font-semibold tracking-tight">{w.week_of}</div>
            </div>
            <div className="flex items-center gap-2">
              {w.recipients.map((r) => (
                <div
                  key={r}
                  title={r}
                  className="grid h-9 w-9 place-items-center rounded-full border border-surface-glass-border bg-surface-glass-light text-xs font-semibold text-ink-on-brand"
                >
                  {initials(r)}
                </div>
              ))}
            </div>
          </div>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-ink-on-brand-soft">
            <InlineTags text={w.lead} />
          </p>
        </div>

        {/* What's emerging */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
            What's emerging
          </h2>
          <div className="space-y-3">
            {w.emerging.map((theme, i) => (
              <Card key={i}>
                <CardContent>
                  <p className="text-sm leading-6 text-ink-primary">
                    <InlineTags text={theme} />
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Where talent matters */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
            Where talent matters
          </h2>
          <div className="space-y-3">
            {w.talent_matters.map((p, i) => (
              <Card key={i}>
                <CardContent>
                  <div className="text-sm font-semibold text-ink-primary">
                    {p.talent} <span className="text-ink-muted">·</span>{" "}
                    <span className="text-ink-secondary">{p.account}</span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-ink-primary">
                    <InlineTags text={p.note} />
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* What I'd ask of you — only when warranted (Q94). */}
        {w.asks.length > 0 && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-ink-secondary">
              What I'd ask of you
            </h2>
            <TrustLayerCallout title="A couple of minutes, if you have them">
              <ul className="space-y-2">
                {w.asks.map((ask, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-brand">—</span>
                    <span>
                      <InlineTags text={ask} />
                    </span>
                  </li>
                ))}
              </ul>
            </TrustLayerCallout>
          </section>
        )}

        {/* Footer */}
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line-subtle pt-4 text-xs text-ink-muted">
          <span>
            Synthesized from <span className="font-mono">{w.signal_sources_count}</span> signal
            sources this week.
          </span>
          <span>Composed by Pulse</span>
        </footer>
      </div>
    </FadeLift>
  );
}

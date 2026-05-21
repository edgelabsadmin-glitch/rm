/*
 * SPEC-034 — a calm placeholder for routes whose feature UI lands in later specs.
 * Names the owning spec so the shell is navigable and self-documenting before the
 * surfaces exist. Replaced per-route as 035-041 land.
 */
import { FadeLift } from "@/components/FadeLift";
import { Card, CardContent } from "@/components/ui/card";

export function Placeholder({
  title,
  spec,
  blurb,
}: {
  title: string;
  spec: string;
  blurb: string;
}) {
  return (
    <FadeLift motionKey={title}>
      <div className="p-6">
        <Card>
          <CardContent>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-secondary">
              {spec}
            </div>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink-primary">{title}</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-ink-secondary">{blurb}</p>
          </CardContent>
        </Card>
      </div>
    </FadeLift>
  );
}

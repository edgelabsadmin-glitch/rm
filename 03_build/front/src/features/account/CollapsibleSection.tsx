/*
 * SPEC-037 — opt-in-depth section (Tier-0 §6 rule 20 / §22). Closed by default; the
 * header toggles. Body fades in (reduced-motion safe). The card itself is the Tier-0
 * §8.3 white card; the header is a full-width button for keyboard access.
 */
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { FadeLift } from "@/components/FadeLift";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between p-5 text-left"
      >
        <h3 className="text-lg font-semibold text-ink-primary">{title}</h3>
        <ChevronRight
          className={cn("h-4 w-4 text-ink-muted transition-transform", open && "rotate-90")}
        />
      </button>
      {open && (
        <div className="px-5 pb-5">
          <FadeLift>{children}</FadeLift>
        </div>
      )}
    </Card>
  );
}

/*
 * SPEC-037 — Meeting brief (preview middle column). Three brand-tinted blocks +
 * a primary "Generate brief" button. Brief generation itself is Skill 02 (spec 018);
 * here the button is the trigger affordance (wired to the skill in Week 4).
 */
import { FileText, MessageSquareText, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "./CollapsibleSection";

const BLOCKS = [
  { Icon: FileText, title: "Top 3 issues", body: "Theme-ranked, with source snippets and timestamps." },
  { Icon: UsersRound, title: "At-risk talent", body: "Talent-side context appears beside customer health." },
  { Icon: MessageSquareText, title: "Talk tracks", body: "Suggested questions, not synthetic “AI voice”." },
];

export function MeetingBriefPanel({ onGenerate }: { onGenerate?: () => void }) {
  return (
    <CollapsibleSection title="Meeting brief">
      <div className="mb-4 flex justify-end">
        <Button size="sm" onClick={onGenerate}>
          Generate brief
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {BLOCKS.map(({ Icon, title, body }) => (
          <div key={title} className="rounded-2xl bg-brand-ghost p-4">
            <Icon className="mb-3 h-5 w-5 text-brand" />
            <div className="text-sm font-semibold text-ink-primary">{title}</div>
            <p className="mt-1 text-xs leading-5 text-ink-secondary">{body}</p>
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}

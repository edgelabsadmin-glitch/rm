/*
 * SPEC-035 — Action Queue card (Design 03 + preview right-rail). Collapsed by
 * default: purple-tinted icon container, chevron, 1-line headline, 1-line why,
 * owner pill + tier-aware chip + Review ghost button. "Review" expands IN PLACE
 * (no modal) to the WhyDetailPanel + Approve/Modify/Reject controls.
 */
import { ChevronRight, Clock3, UserRoundCheck } from "lucide-react";
import { useState } from "react";
import { Pill } from "@/components/Pill";
import { RiskBadge, urgencyToRisk } from "@/components/RiskBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useApprove, useModify, useReject } from "./hooks";
import { ModifyEditor } from "./ModifyEditor";
import { RejectModal } from "./RejectModal";
import { WhyDetailPanel } from "./WhyDetailPanel";
import { actionHeadline, actionType, type ActionDTO, type RejectReason } from "./types";

type Mode = "view" | "modify" | "reject";

function TierChip({ tier }: { tier: string | null }) {
  // The API doesn't expose auto_approve_at, so this is the tier-aware TREATMENT,
  // not a live countdown (see spec-035 report: countdown needs auto_approve_at on
  // the spec-031 API). Enterprise = human-required; SMB = auto-approve window.
  if (tier === "Enterprise") return <Pill>Approval required</Pill>;
  if (tier === "SMB") return <Pill active>Auto-approve window</Pill>;
  return null;
}

export function QueueCard({ action, isAdmin }: { action: ActionDTO; isAdmin: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const [mode, setMode] = useState<Mode>("view");
  const approve = useApprove();
  const modify = useModify();
  const reject = useReject();

  const isCare = (actionType(action) ?? "").includes("care") || action.talent_id != null;
  const Icon = isCare ? UserRoundCheck : Clock3;
  const busy = approve.isPending || modify.isPending || reject.isPending;

  return (
    <Card className="p-0">
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-2xl bg-brand-muted text-brand">
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <RiskBadge level={urgencyToRisk(action.urgency)} />
            <ChevronRight
              className={cn(
                "h-4 w-4 text-ink-muted transition-transform",
                expanded && "rotate-90",
              )}
            />
          </div>
        </div>

        <div className="text-sm font-semibold leading-5 text-ink-primary">
          {actionHeadline(action)}
        </div>
        <p className="mt-2 text-xs leading-5 text-ink-secondary">{action.why_oneline}</p>

        <div className="mt-4 flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <Pill>{action.rm_id ? "RM approval" : "Pulse"}</Pill>
            <TierChip tier={action.tier_class} />
          </div>
          <Button
            size="sm"
            variant="ghost"
            aria-expanded={expanded}
            onClick={() => {
              setExpanded((v) => !v);
              setMode("view");
            }}
          >
            {expanded ? "Hide" : "Review"}
          </Button>
        </div>

        {expanded && (
          <>
            <WhyDetailPanel action={action} isAdmin={isAdmin} />

            {mode === "view" && (
              <div className="mt-3 flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => approve.mutate(action.action_id)}
                >
                  {approve.isPending ? "Approving…" : "Approve"}
                </Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => setMode("modify")}>
                  Modify
                </Button>
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => setMode("reject")}>
                  Reject
                </Button>
              </div>
            )}

            {mode === "modify" && (
              <div className="mt-3">
                <ModifyEditor
                  action={action}
                  saving={modify.isPending}
                  onSave={(diff) =>
                    modify.mutate({ id: action.action_id, diff }, { onSuccess: () => setMode("view") })
                  }
                  onCancel={() => setMode("view")}
                />
              </div>
            )}

            {mode === "reject" && (
              <div className="mt-3">
                <RejectModal
                  rejecting={reject.isPending}
                  onReject={(reason: RejectReason, freeText) =>
                    reject.mutate(
                      { id: action.action_id, reason, freeText },
                      { onSuccess: () => setMode("view") },
                    )
                  }
                  onCancel={() => setMode("view")}
                />
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

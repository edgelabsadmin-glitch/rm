/*
 * SPEC-035 — Reject reason picker (Design 03 §"Approval flow"). 4 fixed reasons +
 * optional free text, fed back into skill tuning. Inline (not a heavy modal) to
 * keep the surface fast; the whole point is quick triage.
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { REJECT_REASONS, type RejectReason } from "./types";

export function RejectModal({
  rejecting,
  onReject,
  onCancel,
}: {
  rejecting: boolean;
  onReject: (reason: RejectReason, freeText?: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState<RejectReason | null>(null);
  const [freeText, setFreeText] = useState("");

  return (
    <div className="space-y-3">
      <div className="text-xs font-medium text-ink-secondary">Why reject?</div>
      <div className="flex flex-wrap gap-2">
        {REJECT_REASONS.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setReason(r)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition",
              reason === r
                ? "border-brand-edge bg-brand-muted text-brand"
                : "border-line-strong bg-surface-card text-ink-secondary hover:bg-brand-ghost hover:text-brand",
            )}
          >
            {r}
          </button>
        ))}
      </div>
      <textarea
        value={freeText}
        onChange={(e) => setFreeText(e.target.value)}
        rows={2}
        placeholder="Add context (optional) — feeds skill tuning."
        className="w-full rounded-2xl border border-line-strong bg-surface-tinted-row px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brand-edge"
      />
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!reason || rejecting}
          onClick={() => reason && onReject(reason, freeText.trim() || undefined)}
        >
          {rejecting ? "Rejecting…" : "Confirm reject"}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

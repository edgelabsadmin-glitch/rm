/*
 * SPEC-035 — inline Modify editor. Renders one field per `modifiable_fields`
 * (current value from action_card), and on save emits a diff of ONLY changed
 * fields → POST /actions/{id}/modify (server rejects non-modifiable keys with 400).
 * react-hook-form per audit D7.
 */
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import type { ActionDTO } from "./types";

function asText(v: unknown): string {
  if (v == null) return "";
  return typeof v === "string" ? v : JSON.stringify(v, null, 2);
}

export function ModifyEditor({
  action,
  saving,
  onSave,
  onCancel,
}: {
  action: ActionDTO;
  saving: boolean;
  onSave: (diff: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const fields = action.modifiable_fields ?? [];
  const defaults: Record<string, string> = {};
  for (const f of fields) defaults[f] = asText(action.action_card?.[f]);

  const { register, handleSubmit, formState } = useForm<Record<string, string>>({
    defaultValues: defaults,
  });

  const submit = handleSubmit((values) => {
    const diff: Record<string, unknown> = {};
    for (const f of fields) {
      if (values[f] !== defaults[f]) diff[f] = values[f];
    }
    onSave(diff);
  });

  if (fields.length === 0) {
    return (
      <p className="text-xs leading-5 text-ink-secondary">
        This action exposes no editable fields. Approve or reject it as-is.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {fields.map((f) => (
        <label key={f} className="block">
          <span className="mb-1 block text-xs font-medium text-ink-secondary">{f}</span>
          <textarea
            {...register(f)}
            rows={defaults[f].length > 60 ? 4 : 2}
            className="w-full rounded-2xl border border-line-strong bg-surface-tinted-row px-3 py-2 text-sm text-ink-primary focus:outline-none focus:ring-2 focus:ring-brand-edge"
          />
        </label>
      ))}
      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" disabled={saving || !formState.isDirty}>
          {saving ? "Saving…" : "Save & approve"}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

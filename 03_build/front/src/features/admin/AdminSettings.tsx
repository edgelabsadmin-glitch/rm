/*
 * Admin — Settings. Signal thresholds, queue policy, integration status,
 * and the kill switch. Frontend-only — write wiring is Week 4.
 */
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Circle, Power } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Toggle ─────────────────────────────────────────────────────────────────

function Toggle({
  value,
  onChange,
  disabled,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={value}
      disabled={disabled}
      onClick={() => onChange(!value)}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition",
        value ? "bg-brand" : "bg-line-strong",
        disabled && "opacity-40 cursor-not-allowed",
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform",
          value ? "translate-x-6" : "translate-x-1",
        )}
      />
    </button>
  );
}

// ── Section wrapper ────────────────────────────────────────────────────────

function SettingsSection({ title, description, children }: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-3xl border border-line-subtle bg-white">
      <div className="border-b border-line-subtle px-6 py-4">
        <h2 className="text-sm font-semibold text-ink-primary">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
      </div>
      <div className="divide-y divide-line-subtle px-6">{children}</div>
    </div>
  );
}

function Row({ label, description, children }: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink-primary">{label}</p>
        {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function ThresholdInput({ value, unit, min, max }: {
  value: number;
  unit: string;
  min: number;
  max: number;
}) {
  const [v, setV] = useState(value);
  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={v}
        min={min}
        max={max}
        onChange={(e) => setV(Number(e.target.value))}
        className="w-20 rounded-xl border border-line-strong bg-white px-3 py-1.5 text-right text-sm font-mono text-ink-primary focus:outline-none focus:ring-2 focus:ring-brand/40"
      />
      <span className="text-xs text-ink-muted">{unit}</span>
    </div>
  );
}

// ── Integration status ─────────────────────────────────────────────────────

type IntegrationStatus = "connected" | "warning" | "disconnected";

function IntegrationDot({ status }: { status: IntegrationStatus }) {
  if (status === "connected")    return <CheckCircle2 className="h-4 w-4 text-green-500" />;
  if (status === "warning")      return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  return <Circle className="h-4 w-4 text-ink-muted" />;
}

const INTEGRATIONS: { name: string; status: IntegrationStatus; detail: string }[] = [
  { name: "Salesforce",     status: "connected",    detail: "edgesolutions.my.salesforce.com · API v62.0 · last sync 4 min ago" },
  { name: "Chorus",         status: "warning",      detail: "API token not configured — call transcripts unavailable" },
  { name: "Activepieces",   status: "disconnected", detail: "Workflow engine not configured — dispatch actions disabled" },
  { name: "Langfuse",       status: "connected",    detail: "pulse-langfuse.fly.dev · traces active · 1 240 events today" },
];

// ── Page ───────────────────────────────────────────────────────────────────

export function AdminSettings() {
  const [killSwitch, setKillSwitch]       = useState(false);
  const [smbauto, setSmbauto]             = useState(true);
  const [entRequired, setEntRequired]     = useState(true);
  const [signalAlerts, setSignalAlerts]   = useState(true);
  const [weeklyDigest, setWeeklyDigest]   = useState(false);

  return (
    <div className="space-y-5 max-w-2xl">

      {/* Kill Switch */}
      <div className={cn(
        "overflow-hidden rounded-3xl border-2 bg-white transition",
        killSwitch ? "border-risk-high-fg" : "border-line-subtle",
      )}>
        <div className={cn("px-6 py-4 border-b", killSwitch ? "border-risk-high-fg/20 bg-risk-high-bg" : "border-line-subtle")}>
          <div className="flex items-center gap-2">
            <Power className={cn("h-4 w-4", killSwitch ? "text-risk-high-fg" : "text-ink-secondary")} />
            <h2 className={cn("text-sm font-semibold", killSwitch ? "text-risk-high-fg" : "text-ink-primary")}>
              Kill Switch
            </h2>
            {killSwitch && (
              <span className="rounded-full bg-risk-high-fg px-2 py-0.5 text-xs font-semibold text-white">
                ACTIVE
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-ink-muted">
            Pause all AI-proposed actions immediately. Existing approvals are not affected.
          </p>
        </div>
        <div className="px-6 py-4">
          <Row
            label={killSwitch ? "All AI actions paused" : "AI actions enabled"}
            description={killSwitch
              ? "No new actions will be proposed until this is disabled."
              : "Pulse is actively surfacing actions to RMs."}
          >
            <Toggle value={killSwitch} onChange={setKillSwitch} />
          </Row>
        </div>
      </div>

      {/* Signal Thresholds */}
      <SettingsSection
        title="Signal Thresholds"
        description="Controls when each AI signal fires. Changes take effect on the next evaluation cycle."
      >
        <Row label="Churn signal threshold" description="Fire when Churn_Probability__c exceeds this value">
          <ThresholdInput value={50} unit="%" min={10} max={90} />
        </Row>
        <Row label="Renewal window" description="Fire when contract close date is within this many days">
          <ThresholdInput value={30} unit="days" min={7} max={90} />
        </Row>
        <Row label="Silent account threshold" description="Fire when no logged contact for this many days">
          <ThresholdInput value={21} unit="days" min={7} max={60} />
        </Row>
        <Row label="Expansion confidence minimum" description="Minimum model confidence to surface expansion signals">
          <ThresholdInput value={65} unit="%" min={30} max={95} />
        </Row>
      </SettingsSection>

      {/* Queue Policy */}
      <SettingsSection
        title="Action Queue Policy"
        description="Controls how proposed actions are handled per account tier."
      >
        <Row
          label="SMB auto-approve window"
          description="Core-tier actions auto-approve after 48 h with no RM decision"
        >
          <Toggle value={smbauto} onChange={setSmbauto} />
        </Row>
        <Row
          label="Enterprise approval required"
          description="Strategic-tier actions always require explicit RM approval"
        >
          <Toggle value={entRequired} onChange={setEntRequired} disabled />
        </Row>
        <Row label="Max pending actions per RM" description="Actions beyond this are queued, not surfaced">
          <ThresholdInput value={20} unit="actions" min={5} max={100} />
        </Row>
        <Row label="Action TTL" description="Expire pending actions after this many hours">
          <ThresholdInput value={72} unit="hours" min={12} max={168} />
        </Row>
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection title="Notifications">
        <Row
          label="Signal performance alerts"
          description="Email admin when precision drops below 60% for any signal"
        >
          <Toggle value={signalAlerts} onChange={setSignalAlerts} />
        </Row>
        <Row
          label="Weekly digest"
          description="Send a weekly Outcome Tracking summary to admins"
        >
          <Toggle value={weeklyDigest} onChange={setWeeklyDigest} />
        </Row>
      </SettingsSection>

      {/* Integrations */}
      <SettingsSection title="Integrations" description="Connection status for external data sources.">
        {INTEGRATIONS.map((item) => (
          <Row key={item.name} label={item.name} description={item.detail}>
            <div className="flex items-center gap-1.5">
              <IntegrationDot status={item.status} />
              <span className={cn("text-xs font-medium capitalize",
                item.status === "connected"    ? "text-green-600" :
                item.status === "warning"      ? "text-amber-600" : "text-ink-muted",
              )}>
                {item.status}
              </span>
            </div>
          </Row>
        ))}
      </SettingsSection>

      <p className="pb-4 text-center text-xs text-ink-muted">
        Settings are frontend-only — write wiring lands in Week 4.
      </p>
    </div>
  );
}

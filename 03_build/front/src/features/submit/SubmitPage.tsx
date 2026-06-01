/*
 * Submit tab — creates RM_Outreach__c in Salesforce.
 * Account and Opportunity are searchable live-filter picklists.
 * All other RM_Outreach__c fields are laid out in logical sections.
 */
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { CheckCircle2, ChevronDown, Loader2, Search, X } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth/AuthContext";
import { useAccounts } from "@/features/account/hooks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── SearchSelect ──────────────────────────────────────────────────────────────

interface SearchSelectOption {
  value: string;
  label: string;
  meta?: string;
}

interface SearchSelectProps {
  options: SearchSelectOption[];
  value: string;
  onChange: (val: string) => void;
  onSearch?: (q: string) => void;
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
}

function SearchSelect({
  options,
  value,
  onChange,
  onSearch,
  placeholder = "Search…",
  loading = false,
  disabled = false,
}: SearchSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Local filter when no external onSearch
  const displayed = onSearch
    ? options
    : query
    ? options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()))
    : options;

  function handleInput(q: string) {
    setQuery(q);
    onSearch?.(q);
    if (!open) setOpen(true);
  }

  function select(opt: SearchSelectOption) {
    onChange(opt.value);
    setQuery("");
    setOpen(false);
  }

  function clear(e: React.MouseEvent) {
    e.stopPropagation();
    onChange("");
    setQuery("");
  }

  return (
    <div ref={ref} className="relative">
      <div
        className={cn(
          "flex items-center gap-2 rounded-xl border border-line-strong bg-white px-3 py-2 text-sm",
          "cursor-text focus-within:ring-2 focus-within:ring-brand/40",
          disabled && "opacity-50 pointer-events-none",
        )}
        onClick={() => !disabled && setOpen(true)}
      >
        <Search className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
        <input
          className="min-w-0 flex-1 bg-transparent text-ink-primary placeholder:text-ink-muted outline-none"
          placeholder={selected ? selected.label : placeholder}
          value={open ? query : ""}
          onFocus={() => setOpen(true)}
          onChange={(e) => handleInput(e.target.value)}
        />
        {value ? (
          <button type="button" onClick={clear} className="shrink-0 text-ink-muted hover:text-ink-primary">
            <X className="h-3.5 w-3.5" />
          </button>
        ) : (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
        )}
      </div>

      {/* Selected badge shown when closed */}
      {!open && selected && (
        <div className="pointer-events-none absolute inset-0 flex items-center gap-2 px-3 py-2">
          <Search className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
          <span className="flex-1 truncate text-sm text-ink-primary">{selected.label}</span>
          {selected.meta && (
            <span className="text-xs text-ink-muted">{selected.meta}</span>
          )}
        </div>
      )}

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-line-subtle bg-white shadow-lg">
          {loading ? (
            <div className="flex items-center gap-2 px-3 py-3 text-xs text-ink-muted">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          ) : displayed.length === 0 ? (
            <p className="px-3 py-3 text-xs text-ink-muted">No results</p>
          ) : (
            <ul className="max-h-60 overflow-auto py-1">
              {displayed.map((opt) => (
                <li key={opt.value}>
                  <button
                    type="button"
                    onClick={() => select(opt)}
                    className={cn(
                      "flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-brand-ghost",
                      opt.value === value && "bg-brand-muted text-brand",
                    )}
                  >
                    <span className="font-medium">{opt.label}</span>
                    {opt.meta && <span className="ml-2 text-xs text-ink-muted">{opt.meta}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ── tiny form primitives ──────────────────────────────────────────────────────

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="mb-1 block text-xs font-medium text-ink-secondary">
      {children}{required && <span className="ml-0.5 text-risk-high-fg">*</span>}
    </label>
  );
}

const inputCls =
  "rounded-xl border border-line-strong bg-white px-3 py-2 text-sm text-ink-primary " +
  "placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brand/40 w-full";

function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(inputCls, props.className)} />;
}
function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} rows={3} className={cn(inputCls, "resize-none")} />;
}
function NativeSelect(props: React.SelectHTMLAttributes<HTMLSelectElement> & { placeholder?: string }) {
  const { placeholder, children, ...rest } = props;
  return (
    <select {...rest} className={cn(inputCls, "cursor-pointer")}>
      <option value="">{placeholder ?? "— select —"}</option>
      {children}
    </select>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-line-subtle bg-white p-6">
      <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.14em] text-ink-secondary border-b border-line-subtle pb-2">
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-4">{children}</div>
    </div>
  );
}

// ── picklist values ───────────────────────────────────────────────────────────

const CUSTOMER_HEALTH = ["Healthy", "Neutral", "At Risk", "At Risk - Escalated", "Unresponsive"];
const PRIORITY = ["High", "Medium", "Low"];
const EXPANSION_SENTIMENT = ["None - No Whitespace", "None - Whitespace", "Neutral", "Partially Interested", "Interested"];
const SATISFACTION = ["High", "Medium", "Low"];
const REFERRAL_SENTIMENT = [
  "None",
  "Already Referred in the Past",
  "Have Contacts but Not Ready to Refer",
  "Don't Have Contacts but Open to Referring",
  "Have Contacts and Ready to Refer",
];
const COMPETITOR_ANALYSIS = [
  "Worked with before but not currently",
  "Currently working with competitor",
  "Never worked with one before",
];
const FEEDBACK_CATEGORY = ["New Feature", "Existing Feature Update"];
const STRUCTURED_FEEDBACK = ["Never", "< 6 months ago", "> 6 months ago", "> 12 months ago"];

// ── form ──────────────────────────────────────────────────────────────────────

interface FormValues {
  account_id: string;
  opportunity_id: string;
  customer_health: string;
  churn_probability: string;
  expansion_probability: string;
  customer_priority_level: string;
  ebr_date: string;
  description: string;
  ebr_description: string;
  recording_link: string;
  transcript_link: string;
  expansion_sentiment: string;
  satisfaction_with_talent: string;
  referral_sentiment: string;
  referral_potential: string;
  competitor_analysis: string;
  feedback_primary_category: string;
  structured_feedback_shared: string;
}

export function SubmitPage() {
  const { user } = useAuth();
  const [oppSearch, setOppSearch] = useState("");
  const [submitted, setSubmitted] = useState<{ record_id: string; message: string } | null>(null);

  const { register, handleSubmit, watch, reset, setValue, formState: { errors } } =
    useForm<FormValues>({ defaultValues: {} });

  const selectedAccountId = watch("account_id") ?? "";
  const selectedOppId = watch("opportunity_id") ?? "";

  // Accounts — full list, filtered client-side
  const { data: accountList, isLoading: accsLoading } = useAccounts();
  const allAccounts = accountList?.accounts ?? [];

  // Opportunities — server search
  const { data: opportunities, isFetching: oppsLoading } = useQuery({
    queryKey: ["opportunities", oppSearch],
    queryFn: () => api.getOpportunities(user, ""),
    staleTime: 60_000,
  });

  const accountOptions: SearchSelectOption[] = allAccounts.map((a) => ({
    value: a.account_id,
    label: a.name,
    meta: a.tier,
  }));

  const oppOptions: SearchSelectOption[] = (opportunities ?? []).map((o) => ({
    value: o.opportunity_id,
    label: o.name,
    meta: o.stage,
  }));

  // Filter opp options client-side
  const filteredOppOptions = oppSearch
    ? oppOptions.filter((o) => o.label.toLowerCase().includes(oppSearch.toLowerCase()))
    : oppOptions;

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const body: Record<string, unknown> = { account_id: values.account_id };
      if (values.customer_health) body.customer_health = values.customer_health;
      if (values.churn_probability) body.churn_probability = parseFloat(values.churn_probability);
      if (values.expansion_probability) body.expansion_probability = parseFloat(values.expansion_probability);
      if (values.customer_priority_level) body.customer_priority_level = values.customer_priority_level;
      if (values.ebr_date) body.ebr_date = values.ebr_date;
      if (values.description) body.description = values.description;
      if (values.ebr_description) body.ebr_description = values.ebr_description;
      if (values.recording_link) body.recording_link = values.recording_link;
      if (values.transcript_link) body.transcript_link = values.transcript_link;
      if (values.expansion_sentiment) body.expansion_sentiment = values.expansion_sentiment;
      if (values.satisfaction_with_talent) body.satisfaction_with_talent = values.satisfaction_with_talent;
      if (values.referral_sentiment) body.referral_sentiment = values.referral_sentiment;
      if (values.referral_potential) body.referral_potential = parseFloat(values.referral_potential);
      if (values.competitor_analysis) body.competitor_analysis = values.competitor_analysis;
      if (values.feedback_primary_category) body.feedback_primary_category = values.feedback_primary_category;
      if (values.structured_feedback_shared) body.structured_feedback_shared = values.structured_feedback_shared;
      return api.createOutreach(user, body);
    },
    onSuccess: (data) => {
      setSubmitted(data);
      reset();
      setOppSearch("");
    },
  });

  if (submitted) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-muted">
            <CheckCircle2 className="h-7 w-7 text-brand" />
          </div>
          <h2 className="text-xl font-semibold text-ink-primary">Outreach submitted</h2>
          <p className="mt-2 text-sm text-ink-secondary">{submitted.message}</p>
          <p className="mt-1 font-mono text-xs text-ink-muted">ID: {submitted.record_id}</p>
          <Button className="mt-6" onClick={() => setSubmitted(null)}>Submit another</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-primary">RM Outreach</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Log a customer interaction — saved directly to Salesforce as RM_Outreach__c.
        </p>
      </div>

      <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-5">

        {/* Account & Opportunity */}
        <Section title="Account & Opportunity">
          <div className="col-span-2 flex flex-col">
            <Label required>Account</Label>
            <SearchSelect
              options={accountOptions}
              value={selectedAccountId}
              onChange={(v) => setValue("account_id", v)}
              loading={accsLoading}
              placeholder="Search accounts…"
            />
            <input type="hidden" {...register("account_id", { required: "Account is required" })} />
            {errors.account_id && (
              <p className="mt-1 text-xs text-risk-high-fg">{errors.account_id.message}</p>
            )}
          </div>

          <div className="col-span-2 flex flex-col">
            <Label>Opportunity</Label>
            <SearchSelect
              options={filteredOppOptions}
              value={selectedOppId}
              onChange={(v) => setValue("opportunity_id", v)}
              onSearch={setOppSearch}
              loading={oppsLoading}
              placeholder="Search opportunities…"
            />
            <input type="hidden" {...register("opportunity_id")} />
          </div>
        </Section>

        {/* Health & Risk */}
        <Section title="Health & Risk">
          <div className="flex flex-col">
            <Label>Customer Health</Label>
            <NativeSelect {...register("customer_health")}>
              {CUSTOMER_HEALTH.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="flex flex-col">
            <Label>Customer Priority</Label>
            <NativeSelect {...register("customer_priority_level")}>
              {PRIORITY.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="flex flex-col">
            <Label>Churn Probability (%)</Label>
            <Input type="number" min={0} max={100} step={1} placeholder="0–100"
              {...register("churn_probability")} />
          </div>

          <div className="flex flex-col">
            <Label>Expansion Probability (%)</Label>
            <Input type="number" min={0} max={100} step={1} placeholder="0–100"
              {...register("expansion_probability")} />
          </div>
        </Section>

        {/* Meeting Details */}
        <Section title="Meeting Details">
          <div className="flex flex-col">
            <Label>EBR Date</Label>
            <Input type="date" {...register("ebr_date")} />
          </div>

          <div className="flex flex-col">
            <Label>Recording Link</Label>
            <Input type="url" placeholder="https://…" {...register("recording_link")} />
          </div>

          <div className="flex flex-col">
            <Label>Transcript Link</Label>
            <Input type="url" placeholder="https://…" {...register("transcript_link")} />
          </div>

          <div className="col-span-2 flex flex-col">
            <Label>Description</Label>
            <Textarea placeholder="What was discussed…" {...register("description")} />
          </div>

          <div className="col-span-2 flex flex-col">
            <Label>EBR Description</Label>
            <Textarea placeholder="Executive Business Review notes…" {...register("ebr_description")} />
          </div>
        </Section>

        {/* Sentiment */}
        <Section title="Sentiment">
          <div className="flex flex-col">
            <Label>Satisfaction with Talent</Label>
            <NativeSelect {...register("satisfaction_with_talent")}>
              {SATISFACTION.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="flex flex-col">
            <Label>Expansion Sentiment</Label>
            <NativeSelect {...register("expansion_sentiment")}>
              {EXPANSION_SENTIMENT.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="col-span-2 flex flex-col">
            <Label>Referral Sentiment</Label>
            <NativeSelect {...register("referral_sentiment")}>
              {REFERRAL_SENTIMENT.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="flex flex-col">
            <Label>Referral Potential (%)</Label>
            <Input type="number" min={0} max={100} step={1} placeholder="0–100"
              {...register("referral_potential")} />
          </div>

          <div className="flex flex-col">
            <Label>Structured Feedback Shared with Talent</Label>
            <NativeSelect {...register("structured_feedback_shared")}>
              {STRUCTURED_FEEDBACK.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>
        </Section>

        {/* Competitive Intelligence */}
        <Section title="Competitive Intelligence">
          <div className="flex flex-col">
            <Label>Competitor Analysis</Label>
            <NativeSelect {...register("competitor_analysis")}>
              {COMPETITOR_ANALYSIS.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>

          <div className="flex flex-col">
            <Label>Feedback Primary Category</Label>
            <NativeSelect {...register("feedback_primary_category")}>
              {FEEDBACK_CATEGORY.map((v) => <option key={v} value={v}>{v}</option>)}
            </NativeSelect>
          </div>
        </Section>

        {mutation.isError && (
          <div className="rounded-2xl border border-risk-high-fg/20 bg-risk-high-bg px-4 py-3 text-sm text-risk-high-fg">
            {(mutation.error as Error)?.message ?? "Something went wrong. Check required fields."}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pb-8">
          <Button type="button" variant="outline"
            onClick={() => { reset(); setOppSearch(""); }}
            disabled={mutation.isPending}
          >
            Clear
          </Button>
          <Button type="submit" disabled={mutation.isPending || !selectedAccountId}>
            {mutation.isPending ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Submitting…
              </span>
            ) : "Submit to Salesforce"}
          </Button>
        </div>
      </form>
    </div>
  );
}

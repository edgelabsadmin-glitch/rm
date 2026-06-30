/* Account-level emails dropdown — client + talent emails for the account. */
import { CollapsibleSection } from "@/features/account/CollapsibleSection";
import { useAccountEmails } from "./hooks";
import { EmailList } from "./EmailList";

export function AccountEmailsPanel({ accountId }: { accountId: string | null }) {
  const { data: emails, isLoading } = useAccountEmails(accountId);
  return (
    <CollapsibleSection title="Emails">
      {isLoading ? (
        <p className="text-sm text-ink-muted">Loading emails…</p>
      ) : (
        <EmailList
          empty="No emails on record for this account."
          emails={(emails ?? []).map((e) => ({
            id: e.email_id,
            subject: e.subject,
            body: e.body,
            received_at: e.received_at,
            from: e.from_name || e.from_email,
            kind: e.sender_kind,
          }))}
        />
      )}
    </CollapsibleSection>
  );
}

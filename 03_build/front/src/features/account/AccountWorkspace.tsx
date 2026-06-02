/*
 * SPEC-037 — three-column workspace. Left = account list, center = hero + panels,
 * right = per-account action queue.
 *
 * Auto-select: once the real SF account list loads, pick the first account if
 * nothing is selected yet. No demo-slug-based scope filtering here — that breaks
 * with real SF IDs. Scope is enforced server-side via the rm_id query param.
 */
import { useEffect } from "react";
import { FadeLift } from "@/components/FadeLift";
import { SituationalHero } from "@/features/hero/SituationalHero";
import { QueueList } from "@/features/queue/QueueList";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { buildAccountFilter } from "@/fixtures/demo_characters";
import { useUser } from "@/lib/auth/AuthContext";
import { AccountListColumn } from "./AccountListColumn";
import { useAccountHealth, useAccounts } from "./hooks";
import { MeetingBriefPanel } from "./MeetingBriefPanel";
import { RecentMeetingsPanel } from "./RecentMeetingsPanel";
import { SignalVectorPanel } from "./SignalVectorPanel";
import { VerifiedThemesPanel } from "./VerifiedThemesPanel";

export function AccountWorkspace() {
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();
  const user = useUser();

  // Same filter as AccountListColumn so auto-select picks from the right scoped set.
  const { data: accountList } = useAccounts(buildAccountFilter(user));
  const { data: account } = useAccountHealth(selectedAccountId);

  // Auto-select the first account once the list loads.
  useEffect(() => {
    if (!selectedAccountId && accountList?.accounts.length) {
      setSelectedAccountId(accountList.accounts[0].account_id);
    }
  }, [accountList, selectedAccountId, setSelectedAccountId]);

  return (
    <div className="grid grid-cols-12 gap-0">
      <AccountListColumn />

      <section className="col-span-12 space-y-5 p-6 lg:col-span-6">
        <SituationalHero account={account} />
        <FadeLift motionKey={`panels-${selectedAccountId}`}>
          <div className="space-y-5">
            <SignalVectorPanel vector={account?.signal_vector ?? []} />
            <VerifiedThemesPanel themes={account?.themes ?? []} />
            <RecentMeetingsPanel />
            <MeetingBriefPanel />
          </div>
        </FadeLift>
      </section>

      <aside className="col-span-12 border-t border-line-subtle bg-surface-sidebar-soft lg:col-span-3 lg:border-l lg:border-t-0">
        <QueueList customerId={selectedAccountId ?? undefined} accountName={account?.name} />
      </aside>
    </div>
  );
}

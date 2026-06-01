/*
 * SPEC-037 — the three-column workspace (Tier-0 §9.3). Left = account list (sets
 * selectedAccountId), center = Hero card + opt-in-depth panels, right = Action Queue.
 * Desktop (lg+): 3-25/50-25 columns. md and below: stacks (list → center → queue).
 *
 * Data: single useAccountHealth fetch here; passed as props to SituationalHero and
 * the depth panels so they all reflect the same selected account with one request.
 * SPEC-042: scope auto-correct — if the selected account falls outside the caller's
 * scope, redirect to the first in-scope account.
 */
import { useEffect, useMemo } from "react";
import { FadeLift } from "@/components/FadeLift";
import { SituationalHero } from "@/features/hero/SituationalHero";
import { QueueList } from "@/features/queue/QueueList";
import { useAuth } from "@/lib/auth/AuthContext";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { AccountListColumn } from "./AccountListColumn";
import { useAccountHealth, useAccounts } from "./hooks";
import { MeetingBriefPanel } from "./MeetingBriefPanel";
import { SignalVectorPanel } from "./SignalVectorPanel";
import { VerifiedThemesPanel } from "./VerifiedThemesPanel";

export function AccountWorkspace() {
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();
  const { accountScope } = useAuth();
  const { data: account } = useAccountHealth(selectedAccountId);
  const { data: accountList } = useAccounts();

  // SPEC-042 Step-5: compute scope-visible IDs from the fetched SF account list.
  // Exec/Admin scope = null (all accounts); RM/Manager = their book/team IDs.
  const visibleIds = useMemo(() => {
    const all = accountList?.accounts.map((a) => a.account_id) ?? [];
    return accountScope ? all.filter((id) => accountScope.includes(id)) : all;
  }, [accountList, accountScope]);

  // Auto-correct: if selected account is out of scope or nothing is selected, land
  // on the first visible account. Runs after the list is fetched.
  useEffect(() => {
    if (!visibleIds.length) return;
    if (!selectedAccountId || !visibleIds.includes(selectedAccountId)) {
      setSelectedAccountId(visibleIds[0]);
    }
  }, [visibleIds, selectedAccountId, setSelectedAccountId]);

  return (
    <div className="grid grid-cols-12 gap-0">
      <AccountListColumn />

      <section className="col-span-12 space-y-5 p-6 lg:col-span-6">
        <SituationalHero account={account} />
        {/* Opt-in depth panels — keyed by account so they reset on switch. */}
        <FadeLift motionKey={`panels-${selectedAccountId}`}>
          <div className="space-y-5">
            <SignalVectorPanel vector={account?.signal_vector ?? []} />
            <VerifiedThemesPanel themes={account?.themes ?? []} />
            <MeetingBriefPanel />
          </div>
        </FadeLift>
      </section>

      <aside className="col-span-12 border-t border-line-subtle bg-surface-sidebar-soft lg:col-span-3 lg:border-l lg:border-t-0">
        <QueueList customerId={selectedAccountId} accountName={account?.name} />
      </aside>
    </div>
  );
}

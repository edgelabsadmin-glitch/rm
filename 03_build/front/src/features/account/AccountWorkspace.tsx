/*
 * SPEC-037 — the three-column workspace (Tier-0 §9.3). Left = account list (sets
 * selectedAccountId), center = Hero card + opt-in-depth panels, right = Action Queue.
 * Desktop (lg+): 3-25/50-25 columns. md and below: stacks (list → center → queue).
 *
 * Data: single useAccountHealth fetch here; passed as props to SituationalHero and
 * the depth panels so they all reflect the same selected account with one request.
 */
import { FadeLift } from "@/components/FadeLift";
import { SituationalHero } from "@/features/hero/SituationalHero";
import { QueueList } from "@/features/queue/QueueList";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { AccountListColumn } from "./AccountListColumn";
import { useAccountHealth } from "./hooks";
import { MeetingBriefPanel } from "./MeetingBriefPanel";
import { SignalVectorPanel } from "./SignalVectorPanel";
import { VerifiedThemesPanel } from "./VerifiedThemesPanel";

export function AccountWorkspace() {
  const { selectedAccountId } = useSelectedAccount();
  const { data: account } = useAccountHealth(selectedAccountId);

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

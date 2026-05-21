/*
 * SPEC-037 — the three-column workspace (Tier-0 §9.3). Left = account list (sets
 * selectedAccountId), center = Hero card + opt-in-depth panels, right = Action Queue.
 * Desktop (lg+): 3-25/50-25 columns. md and below: stacks (list → center → queue).
 */
import { FadeLift } from "@/components/FadeLift";
import { SituationalHero } from "@/features/hero/SituationalHero";
import { getAccountHealthFixture } from "@/features/hero/fixtures";
import { QueueList } from "@/features/queue/QueueList";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { AccountListColumn } from "./AccountListColumn";
import { MeetingBriefPanel } from "./MeetingBriefPanel";
import { SignalVectorPanel } from "./SignalVectorPanel";
import { VerifiedThemesPanel } from "./VerifiedThemesPanel";

export function AccountWorkspace() {
  const { selectedAccountId } = useSelectedAccount();
  const account = getAccountHealthFixture(selectedAccountId);

  return (
    <div className="grid grid-cols-12 gap-0">
      <AccountListColumn />

      <section className="col-span-12 space-y-5 p-6 lg:col-span-6">
        <SituationalHero />
        {/* Opt-in depth (closed by default). Keyed by account so panels reset on switch. */}
        <FadeLift motionKey={`panels-${account.account_id}`}>
          <div className="space-y-5">
            <SignalVectorPanel vector={account.signal_vector} />
            <VerifiedThemesPanel themes={account.themes} />
            <MeetingBriefPanel />
          </div>
        </FadeLift>
      </section>

      <aside className="col-span-12 border-t border-line-subtle bg-surface-sidebar-soft lg:col-span-3 lg:border-l lg:border-t-0">
        <QueueList />
      </aside>
    </div>
  );
}

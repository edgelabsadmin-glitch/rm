/*
 * SPEC-036 — selected-account state (shell-level). The middle-column Hero card and
 * (later) the per-account view read this; the left-rail account list (spec 037,
 * repo per-account-view) will SET it. Standalone now with a demo default so the
 * Hero renders before the account list exists.
 *
 * Phase-1 default: Helix Labs (the React-preview anchor + demo storyboard
 * Helix/Cirventis alias; composite_health 6.4).
 */
import { createContext, useContext, useMemo, useState } from "react";

export const DEFAULT_ACCOUNT_ID = "helix-labs";

interface SelectedAccountValue {
  selectedAccountId: string;
  setSelectedAccountId: (id: string) => void;
}

const SelectedAccountContext = createContext<SelectedAccountValue | null>(null);

export function SelectedAccountProvider({ children }: { children: React.ReactNode }) {
  const [selectedAccountId, setSelectedAccountId] = useState<string>(DEFAULT_ACCOUNT_ID);
  const value = useMemo(
    () => ({ selectedAccountId, setSelectedAccountId }),
    [selectedAccountId],
  );
  return (
    <SelectedAccountContext.Provider value={value}>{children}</SelectedAccountContext.Provider>
  );
}

export function useSelectedAccount(): SelectedAccountValue {
  const v = useContext(SelectedAccountContext);
  if (!v) throw new Error("useSelectedAccount must be used within SelectedAccountProvider");
  return v;
}

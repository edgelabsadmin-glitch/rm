/*
 * SPEC-042 Step-2 — AuthContext: the single source of the current user + their derived
 * AccountScope. Supersedes the spec-034 stubbed `useSession` (A3 disposition). Phase 1A
 * starts as `pulse-admin` (full access) and exposes a `switchUser` callback for the dev
 * user-switcher (gated `import.meta.env.DEV` at the consumer). Phase 1B (spec 043 OAuth)
 * hydrates `initialUserId` from SSO claims — no consumer change.
 */
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { DEMO_USERS, type DemoUser } from "@/fixtures/demo_characters";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { AccountScope } from "@/lib/rbac/types";

interface AuthContextValue {
  user: DemoUser;
  accountScope: AccountScope;
  // Dev-only user-switcher affordance; gated import.meta.env.DEV at the consumer level.
  switchUser: (userId: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Default Phase 1A starting user — operator chooses at app start via the dev switcher.
// Production (Phase 1B post-spec-043) hydrates this from OAuth claims.
const DEFAULT_USER_ID = "pulse-admin";

interface AuthProviderProps {
  children: ReactNode;
  initialUserId?: string;
}

export function AuthProvider({ children, initialUserId = DEFAULT_USER_ID }: AuthProviderProps) {
  const [userId, setUserId] = useState<string>(initialUserId);

  const value = useMemo<AuthContextValue>(() => {
    const user = DEMO_USERS.find((u) => u.id === userId);
    if (!user) {
      throw new Error(`AuthProvider: unknown user id '${userId}'`);
    }
    const accountScope = deriveAccountScope(user.role, user.id);
    return { user, accountScope, switchUser: setUserId };
  }, [userId]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth() must be called within an AuthProvider");
  }
  return ctx;
}

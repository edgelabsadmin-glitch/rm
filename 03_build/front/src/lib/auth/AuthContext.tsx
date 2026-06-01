/*
 * SPEC-042 / SPEC-043 — AuthContext: single source of current user + account scope.
 *
 * Phase 1A (DEV): auto-logs in as pulse-admin; dev persona switcher still works.
 * Phase 1B (real users): Google OAuth flow sets google_user_id in the URL after
 *   the FastAPI callback; AuthContext picks it up, saves to localStorage, and sets
 *   the active user. logout() clears localStorage and returns to /login.
 *
 * user is DemoUser | null. null means unauthenticated → App.tsx redirects to /login.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEMO_USERS, type DemoUser } from "@/fixtures/demo_characters";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { AccountScope } from "@/lib/rbac/types";

const STORAGE_KEY = "pulse_user_id";
const DEV_DEFAULT_USER = "pulse-admin";

interface AuthContextValue {
  user: DemoUser | null;
  loading: boolean;
  accountScope: AccountScope;
  switchUser: (userId: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if Google OAuth just completed — backend redirects here with these params.
    const params = new URLSearchParams(window.location.search);
    const googleUserId = params.get("google_user_id");
    const googleStatus = params.get("google");

    if (googleUserId && googleStatus === "success") {
      localStorage.setItem(STORAGE_KEY, googleUserId);
      // Strip the OAuth params from the URL without a page reload.
      window.history.replaceState({}, "", window.location.pathname);
      setUserId(googleUserId);
      setLoading(false);
      return;
    }

    // Restore persisted session.
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && DEMO_USERS.find((u) => u.id === stored)) {
      setUserId(stored);
      setLoading(false);
      return;
    }

    // DEV only: auto-login so the persona switcher works without Google OAuth.
    if (import.meta.env.DEV) {
      setUserId(DEV_DEFAULT_USER);
    }
    setLoading(false);
  }, []);

  const switchUser = useCallback((newId: string) => {
    setUserId(newId);
    // In dev, switching persona also updates localStorage so a refresh keeps the selection.
    localStorage.setItem(STORAGE_KEY, newId);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUserId(null);
    // Hard-navigate so all React Query caches are cleared.
    window.location.href = "/login";
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const user = userId ? (DEMO_USERS.find((u) => u.id === userId) ?? null) : null;
    const accountScope = user ? deriveAccountScope(user.role, user.id) : [];
    return { user, loading, accountScope, switchUser, logout };
  }, [userId, loading, switchUser, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth() must be called within an AuthProvider");
  return ctx;
}

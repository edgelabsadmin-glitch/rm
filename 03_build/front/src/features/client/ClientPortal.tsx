import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { LogOut, Loader2, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { ClientAuthProvider, useClientAuth } from "./ClientAuthContext";
import { ClientLoginPage } from "./ClientLoginPage";
import { ClientChatPage } from "./ClientChatPage";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function ClientHeader() {
  const { me, logout } = useClientAuth();
  const [avatarOpen, setAvatarOpen] = useState(false);
  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!avatarOpen) return;
    function handleClick(e: MouseEvent) {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [avatarOpen]);

  return (
    <header className="flex items-center justify-between border-b border-line-strong bg-white px-7 py-5">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <div className="text-lg font-semibold tracking-tight text-ink-primary">Pulse</div>
            <div className="text-xs text-ink-secondary">Client portal</div>
          </div>
        </div>
        <nav className="hidden items-center gap-1 lg:flex">
          <NavLink
            to="/client/chat"
            className={({ isActive }) =>
              cn(
                "rounded-full px-3 py-1.5 text-sm font-medium transition",
                isActive
                  ? "bg-brand-muted text-brand"
                  : "text-ink-secondary hover:bg-brand-ghost hover:text-brand",
              )
            }
          >
            Chat
          </NavLink>
        </nav>
      </div>

      {me && (
        <div className="relative" ref={avatarRef}>
          <div
            role="button"
            tabIndex={0}
            onClick={() => setAvatarOpen((o) => !o)}
            onKeyDown={(e) => e.key === "Enter" && setAvatarOpen((o) => !o)}
            className="grid h-10 w-10 cursor-pointer place-items-center rounded-full bg-ink-primary text-sm font-semibold text-ink-on-brand"
            title={`${me.client_name} · ${me.account_name}`}
          >
            {initials(me.client_name)}
          </div>
          {avatarOpen && (
            <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-xl border border-line-subtle bg-white p-2 shadow-lg">
              <div className="px-2 py-1.5 mb-1">
                <p className="text-xs font-medium text-ink-primary">{me.client_name}</p>
                <p className="text-xs text-ink-muted">{me.account_name}</p>
              </div>
              <button
                type="button"
                onClick={logout}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-ink-secondary transition hover:bg-surface-sidebar hover:text-ink-primary"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}

function ClientShell({ children }: { children: React.ReactNode }) {
  const { me, loading } = useClientAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-page">
        <Loader2 className="h-6 w-6 animate-spin text-brand" />
      </div>
    );
  }

  if (!me) {
    return <Navigate to="/client/login" replace />;
  }

  return (
    <div className="min-h-screen bg-surface-page p-6 text-ink-primary">
      <div className="mx-auto max-w-7xl overflow-hidden rounded-4xl border border-line-strong bg-surface-chrome shadow-2xl-shell">
        <ClientHeader />
        <main>{children}</main>
      </div>
    </div>
  );
}

export function ClientPortal() {
  return (
    <ClientAuthProvider>
      <Routes>
        <Route path="login" element={<ClientLoginPage />} />
        <Route
          path="chat"
          element={
            <ClientShell>
              <ClientChatPage />
            </ClientShell>
          }
        />
        <Route path="*" element={<Navigate to="/client/login" replace />} />
      </Routes>
    </ClientAuthProvider>
  );
}

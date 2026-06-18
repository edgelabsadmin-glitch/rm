/*
 * SPEC-034 — route tree (react-router-dom v6, nested layouts per audit D4).
 * <AppShell> is the chrome layout owning the Pulse Bar; <AdminLayout> nests under
 * it for admin surfaces.
 *
 * Auth guard: user === null → redirect to /login.
 * /login → redirect to role default if already authenticated.
 */
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { AccountWorkspace } from "@/features/account/AccountWorkspace";
import { ExecutiveView } from "@/features/executive/ExecutiveView";
import { QueueList } from "@/features/queue/QueueList";
import { AdminSettings } from "@/features/admin/AdminSettings";
import { OutcomeTracking } from "@/features/admin/OutcomeTracking";
import { SignalPerformance } from "@/features/admin/SignalPerformance";
import { SubmitPage } from "@/features/submit/SubmitPage";
import { SupportPage } from "@/features/support/SupportPage";
import { InboxPage } from "@/features/inbox/InboxPage";
import { SettingsUsersPanel } from "@/features/settings/SettingsUsersPanel";
import { LoginPage } from "@/features/auth/LoginPage";
import { ClientPortal } from "@/features/client/ClientPortal";
import { useAuth } from "@/lib/auth/AuthContext";
import { defaultRouteForRole } from "@/lib/auth/defaultRoute";
import { RoleGuard, AccountScopeGuard } from "@/lib/auth/RoleGuard";
import { AdminLayout } from "@/routes/AdminLayout";
import { Placeholder } from "@/routes/Placeholder";

// Code-split: react-force-graph + d3 (~200kB gz) load only when /constellation opens.
const ConstellationPage = lazy(() =>
  import("@/features/constellation/ConstellationPage").then((m) => ({
    default: m.ConstellationPage,
  })),
);

export default function App() {
  const { user, loading } = useAuth();

  // Don't render routes until auth state is resolved (avoids flash redirects).
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  return (
    <Routes>
      {/* Login — redirect to home if already authenticated */}
      <Route
        path="/login"
        element={user ? <Navigate to={defaultRouteForRole(user.role)} replace /> : <LoginPage />}
      />

      {/* All authenticated routes */}
      {user ? (
        <Route element={<AppShell />}>
          <Route index element={<Navigate to={defaultRouteForRole(user.role)} replace />} />
          <Route
            path="/accounts"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <AccountWorkspace />
              </RoleGuard>
            }
          />
          <Route
            path="/accounts/:id"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <AccountScopeGuard executiveBypass>
                  <Placeholder
                    spec="Spec 036-037"
                    title="Account detail"
                    blurb="Per-account view with opt-in depth: 270° composite-health ring, dual-sided signal vector, verified themes, and the AI-RM briefing voice."
                  />
                </AccountScopeGuard>
              </RoleGuard>
            }
          />
          <Route
            path="/actions"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "admin"]}>
                <QueueList />
              </RoleGuard>
            }
          />
          <Route
            path="/inbox"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <InboxPage />
              </RoleGuard>
            }
          />
          <Route
            path="/constellation"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <Suspense fallback={<div className="p-6 text-sm text-ink-secondary">Charting the constellation…</div>}>
                  <ConstellationPage />
                </Suspense>
              </RoleGuard>
            }
          />
          <Route
            path="/executive"
            element={
              <RoleGuard allowedRoles={["executive", "admin"]}>
                <ExecutiveView />
              </RoleGuard>
            }
          />
          <Route
            path="/settings/users"
            element={
              <RoleGuard allowedRoles={["admin"]}>
                <SettingsUsersPanel />
              </RoleGuard>
            }
          />
          <Route
            path="/submit"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <SubmitPage />
              </RoleGuard>
            }
          />
          <Route
            path="/support"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <SupportPage />
              </RoleGuard>
            }
          />
          <Route
            path="/admin"
            element={
              <RoleGuard allowedRoles={["admin"]}>
                <AdminLayout />
              </RoleGuard>
            }
          >
            <Route index element={<Navigate to="/admin/signals" replace />} />
            <Route path="signals"  element={<SignalPerformance />} />
            <Route path="outcomes" element={<OutcomeTracking />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
        </Route>
      ) : null}

      {/* Client portal — completely separate auth, no RM session required */}
      <Route path="/client/*" element={<ClientPortal />} />

      {/* Unauthenticated catch-all → login */}
      <Route path="*" element={<Navigate to={user ? "/accounts" : "/login"} replace />} />
    </Routes>
  );
}

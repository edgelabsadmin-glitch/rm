/*
 * SPEC-034 — route tree (react-router-dom v6, nested layouts per audit D4).
 * <AppShell> is the chrome layout owning the Pulse Bar; <AdminLayout> nests under
 * it for admin surfaces. Every surface here is a Placeholder until its feature spec
 * lands (035-045). Login is pre-shell (no Pulse Bar) — stubbed in spec 034, real
 * OAuth in spec 043.
 */
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { AccountWorkspace } from "@/features/account/AccountWorkspace";
import { ExecutiveView } from "@/features/executive/ExecutiveView";
import { QueueList } from "@/features/queue/QueueList";
import { useAuth } from "@/lib/auth/AuthContext";
import { defaultRouteForRole } from "@/lib/auth/defaultRoute";
import { RoleGuard, AccountScopeGuard } from "@/lib/auth/RoleGuard";
import { AdminLayout } from "@/routes/AdminLayout";
import { Placeholder } from "@/routes/Placeholder";

// Code-split: react-force-graph + d3 (~200kB gz) load only when /constellation opens.
const Constellation = lazy(() =>
  import("@/features/constellation/Constellation").then((m) => ({ default: m.Constellation })),
);

export default function App() {
  // SPEC-042 Step 3: the root route lands each role on their default surface.
  const { user } = useAuth();
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to={defaultRouteForRole(user.role)} replace />} />
        <Route path="/accounts" element={<AccountWorkspace />} />
        <Route
          path="/accounts/:id"
          element={
            <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
              <AccountScopeGuard executiveBypass>
                {/* Placeholder until spec 037 builds PerAccountView; the scope guard
                    still enforces RM/Manager out-of-scope redirects today. */}
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
          path="/constellation"
          element={
            <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
              <Suspense fallback={<div className="p-6 text-sm text-ink-secondary">Charting the constellation…</div>}>
                <Constellation />
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
              <Placeholder
                spec="Spec 042 (Step 7)"
                title="Settings — User management"
                blurb="Admin-only read-only role topology + scope counts. The full panel lands in spec 042 Step 7; this route is RBAC-gated now."
              />
            </RoleGuard>
          }
        />
        <Route
          path="/submit"
          element={
            <Placeholder
              spec="Spec 039"
              title="Submit a note"
              blurb="Type or paste a quick note; Pulse ingests it, extracts signals, and surfaces follow-ups in your queue. (Reframed from a Slack command to this web route.)"
            />
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
          <Route
            path="signals"
            element={
              <Placeholder
                spec="Spec 044"
                title="Signal Performance"
                blurb="Layer-8 Mechanism 1 — how each signal definition is performing (fire rate, precision, RM feedback)."
              />
            }
          />
          <Route
            path="outcomes"
            element={
              <Placeholder
                spec="Spec 045"
                title="Outcome Tracking"
                blurb="Layer-8 Mechanism 3 — did the actions Pulse proposed lead to good outcomes? Closed-loop learning."
              />
            }
          />
          <Route
            path="settings"
            element={
              <Placeholder
                spec="Spec 010"
                title="Settings"
                blurb="Admin governance — the kill switch and policy controls."
              />
            }
          />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/accounts" replace />} />
    </Routes>
  );
}

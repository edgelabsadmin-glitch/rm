/*
 * SPEC-034 — route tree (react-router-dom v6, nested layouts per audit D4).
 * <AppShell> is the chrome layout owning the Pulse Bar; <AdminLayout> nests under
 * it for admin surfaces. Every surface here is a Placeholder until its feature spec
 * lands (035-045). Login is pre-shell (no Pulse Bar) — stubbed in spec 034, real
 * OAuth in spec 043.
 */
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { SituationalHero } from "@/features/hero/SituationalHero";
import { QueueList } from "@/features/queue/QueueList";
import { AdminLayout } from "@/routes/AdminLayout";
import { Placeholder } from "@/routes/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<div className="p-6"><SituationalHero /></div>} />
        <Route
          path="/accounts"
          element={
            <Placeholder
              spec="Specs 035-037"
              title="Accounts"
              blurb="The account list + situational hero + per-account deep view land here. Select an account to open its hero, signal vector, verified themes, and meeting brief."
            />
          }
        />
        <Route
          path="/accounts/:id"
          element={
            <Placeholder
              spec="Spec 036-037"
              title="Account detail"
              blurb="Per-account view with opt-in depth: 270° composite-health ring, dual-sided signal vector, verified themes, and the AI-RM briefing voice."
            />
          }
        />
        <Route path="/actions" element={<QueueList />} />
        <Route
          path="/constellation"
          element={
            <Placeholder
              spec="Spec 041"
              title="Constellation"
              blurb="Force-directed map of the whole book of business — nodes sized by placements, colored by health, click-through to the account view."
            />
          }
        />
        <Route
          path="/ceo"
          element={
            <Placeholder
              spec="Spec 040"
              title="CEO View"
              blurb="The weekly Pulse-to-leadership narrative — the highest brand-moment surface, in the AI-RM first-person voice."
            />
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
        <Route path="/admin" element={<AdminLayout />}>
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

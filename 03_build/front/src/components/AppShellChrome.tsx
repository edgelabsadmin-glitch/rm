/*
 * SPEC-034 — the chrome frame, separated from the router so it can wrap arbitrary
 * children (snapshot tests, preview). Two-layer Edge surface (§9.1): #FAFAFA page
 * → #F5F5F7 rounded-[2rem] shell → header + Pulse Bar + content.
 */
import { Header } from "@/components/Header";
import { PulseBar } from "@/components/PulseBar";
import { PulseBarController } from "@/components/PulseBarController";

export function AppShellChrome({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-page p-6 text-ink-primary">
      {/* Headless: polls live queue state, drives the bar on every route. */}
      <PulseBarController />
      <div className="mx-auto max-w-7xl overflow-hidden rounded-4xl border border-line-strong bg-surface-chrome shadow-2xl-shell">
        <Header />
        {/* Pulse Bar: the seam between header and body. Chrome, not content. */}
        <PulseBar />
        <main>{children}</main>
      </div>
    </div>
  );
}

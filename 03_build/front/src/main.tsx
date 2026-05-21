/*
 * SPEC-034 — entry. Providers, outermost to innermost: React Query (server state)
 * → stubbed Session (spec 043 replaces) → PulseState (agent presence) → Router.
 * Inter is self-hosted via @fontsource-variable (NOT a CDN / next/font — Vite).
 */
import "@fontsource-variable/inter";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "@/App";
import { PulseStateProvider } from "@/components/PulseStateProvider";
import { queryClient } from "@/lib/queryClient";
import { SelectedAccountProvider } from "@/session/SelectedAccountProvider";
import { SessionContext, STUB_SESSION } from "@/session/useSession";
import "@/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SessionContext.Provider value={STUB_SESSION}>
        <SelectedAccountProvider>
          <PulseStateProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </PulseStateProvider>
        </SelectedAccountProvider>
      </SessionContext.Provider>
    </QueryClientProvider>
  </StrictMode>,
);

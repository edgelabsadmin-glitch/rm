/*
 * SPEC-034/042 — entry. Providers, outermost to innermost: React Query (server state)
 * → Auth (spec 042 user + accountScope; spec 043 OAuth hydrates initialUserId) → PulseState
 * (agent presence) → Router. Inter is self-hosted via @fontsource-variable (NOT a CDN).
 */
import "@fontsource-variable/inter";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "@/App";
import { PulseStateProvider } from "@/components/PulseStateProvider";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { queryClient } from "@/lib/queryClient";
import { SelectedAccountProvider } from "@/session/SelectedAccountProvider";
import "@/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SelectedAccountProvider>
          <PulseStateProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </PulseStateProvider>
        </SelectedAccountProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);

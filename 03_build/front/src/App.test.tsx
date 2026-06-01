import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "@/App";
import { PulseStateProvider } from "@/components/PulseStateProvider";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { SelectedAccountProvider } from "@/session/SelectedAccountProvider";

function renderApp(initialUserId: string, path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider initialUserId={initialUserId}>
        <SelectedAccountProvider>
          <PulseStateProvider>
            <MemoryRouter initialEntries={[path]}>
              <App />
            </MemoryRouter>
          </PulseStateProvider>
        </SelectedAccountProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const QUEUE = /ACTION QUEUE/i; // QueueList heading
const EXEC = /What I'd ask of you/i; // ExecutiveView asks band

describe("App route guards + default route (spec-042 Step-3)", () => {
  it("RM at / redirects to /actions (queue)", () => {
    renderApp("yozeline-candia", "/");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("Manager at / redirects to /actions", () => {
    renderApp("sarah-hooper", "/");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("Admin at / redirects to /actions", () => {
    renderApp("pulse-admin", "/");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("Executive at / redirects to /executive", () => {
    renderApp("iffi-wahla", "/");
    expect(screen.getByText(EXEC)).toBeTruthy();
  });

  it("RM at /executive is redirected to /actions", () => {
    renderApp("sidra-zia", "/executive");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("Manager at /executive is redirected to /actions", () => {
    renderApp("muhammad-ibrahim", "/executive");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("RM at /settings/users is redirected to /actions", () => {
    renderApp("sidra-zia", "/settings/users");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("Executive at /settings/users is redirected to /executive (role-default fallback)", () => {
    renderApp("iffi-wahla", "/settings/users");
    expect(screen.getByText(EXEC)).toBeTruthy();
  });

  it("Executive at /actions does NOT loop — redirected to /executive (HALT #1 resolution)", () => {
    renderApp("iffi-wahla", "/actions");
    expect(screen.getByText(EXEC)).toBeTruthy();
  });

  it("Admin at /settings/users renders the SettingsUsersPanel (spec-042 Step-7)", () => {
    renderApp("pulse-admin", "/settings/users");
    // The real panel renders the 11-user table (data-testid="user-row"), not the old placeholder.
    expect(screen.getAllByTestId("user-row")).toHaveLength(11);
  });

  it("RM at /admin is redirected to /actions", () => {
    renderApp("yozeline-candia", "/admin");
    expect(screen.getByText(QUEUE)).toBeTruthy();
  });

  it("/accounts is accessible to an RM and shows their scoped account rail (Manhattan only)", () => {
    renderApp("yozeline-candia", "/accounts");
    // The account-list rail (only on the /accounts workspace) renders Yozeline's one account.
    expect(screen.getByRole("button", { name: /Manhattan Restorative/i })).toBeTruthy();
  });

  it("/accounts is accessible to an Executive (read-only) with the full account rail", () => {
    renderApp("iffi-wahla", "/accounts");
    expect(screen.getByRole("button", { name: /DHR Health Clinics/i })).toBeTruthy();
  });
});

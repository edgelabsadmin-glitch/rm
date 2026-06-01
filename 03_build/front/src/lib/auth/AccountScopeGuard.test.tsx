import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "./AuthContext";
import { AccountScopeGuard } from "./RoleGuard";

// Renders /accounts/:id guarded + /actions fallback, starting at the given account id.
function renderAt(opts: { initialUserId: string; accountId: string; executiveBypass?: boolean }) {
  return render(
    <AuthProvider initialUserId={opts.initialUserId}>
      <MemoryRouter initialEntries={[`/accounts/${opts.accountId}`]}>
        <Routes>
          <Route
            path="/accounts/:id"
            element={
              <AccountScopeGuard executiveBypass={opts.executiveBypass}>
                <div>ACCOUNT DETAIL</div>
              </AccountScopeGuard>
            }
          />
          <Route path="/actions" element={<div>ACTIONS FALLBACK</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("AccountScopeGuard (spec-042 Step-2)", () => {
  it("renders children for an in-scope account (RM viewing own book)", () => {
    // Yozeline's only account is manhattan-restorative
    renderAt({ initialUserId: "yozeline-candia", accountId: "manhattan-restorative" });
    expect(screen.getByText("ACCOUNT DETAIL")).toBeTruthy();
  });

  it("redirects to /actions for an out-of-scope account", () => {
    renderAt({ initialUserId: "yozeline-candia", accountId: "dhr-health-clinics" });
    expect(screen.queryByText("ACCOUNT DETAIL")).toBeNull();
    expect(screen.getByText("ACTIONS FALLBACK")).toBeTruthy();
  });

  it("executiveBypass: Executive renders children even out-of-scope", () => {
    renderAt({ initialUserId: "iffi-wahla", accountId: "dhr-health-clinics", executiveBypass: true });
    expect(screen.getByText("ACCOUNT DETAIL")).toBeTruthy();
  });

  it("executiveBypass: Admin renders children even out-of-scope", () => {
    renderAt({ initialUserId: "pulse-admin", accountId: "dhr-health-clinics", executiveBypass: true });
    // Admin scope is full org anyway, but the bypass branch returns early regardless.
    expect(screen.getByText("ACCOUNT DETAIL")).toBeTruthy();
  });

  it("executiveBypass: RM is still scope-checked (bypass only applies to exec/admin)", () => {
    renderAt({ initialUserId: "yozeline-candia", accountId: "dhr-health-clinics", executiveBypass: true });
    expect(screen.getByText("ACTIONS FALLBACK")).toBeTruthy();
  });

  it("default (executiveBypass=false): Executive is scope-checked too — but exec scope is full org, so in-scope renders", () => {
    // Without bypass, exec falls through to the scope check; exec scope = all 14, so any account renders.
    renderAt({ initialUserId: "iffi-wahla", accountId: "dhr-health-clinics" });
    expect(screen.getByText("ACCOUNT DETAIL")).toBeTruthy();
  });
});

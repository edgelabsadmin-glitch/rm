import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "./AuthContext";
import { RoleGuard } from "./RoleGuard";

// Render a guarded route + a fallback route, starting at the guarded path.
function renderGuarded(opts: {
  initialUserId: string;
  allowedRoles: Parameters<typeof RoleGuard>[0]["allowedRoles"];
  fallbackRoute?: string;
}) {
  return render(
    <AuthProvider initialUserId={opts.initialUserId}>
      <MemoryRouter initialEntries={["/guarded"]}>
        <Routes>
          <Route
            path="/guarded"
            element={
              <RoleGuard allowedRoles={opts.allowedRoles} fallbackRoute={opts.fallbackRoute}>
                <div>GUARDED CONTENT</div>
              </RoleGuard>
            }
          />
          <Route path="/actions" element={<div>ACTIONS FALLBACK</div>} />
          <Route path="/executive" element={<div>EXEC FALLBACK</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("RoleGuard (spec-042 Step-2)", () => {
  it("renders children when the role is allowed", () => {
    renderGuarded({ initialUserId: "pulse-admin", allowedRoles: ["admin"] });
    expect(screen.getByText("GUARDED CONTENT")).toBeTruthy();
  });

  it("redirects to the role-default route (RM → /actions) when the role is disallowed", () => {
    // RM blocked from an admin-only route → role-default fallback is /actions.
    renderGuarded({ initialUserId: "sidra-zia", allowedRoles: ["admin"] });
    expect(screen.queryByText("GUARDED CONTENT")).toBeNull();
    expect(screen.getByText("ACTIONS FALLBACK")).toBeTruthy();
  });

  it("Executive disallowed → role-default fallback is /executive, NOT /actions (HALT #1 fix)", () => {
    renderGuarded({ initialUserId: "iffi-wahla", allowedRoles: ["rm", "manager", "admin"] });
    expect(screen.queryByText("GUARDED CONTENT")).toBeNull();
    expect(screen.getByText("EXEC FALLBACK")).toBeTruthy();
  });

  it("respects a custom fallbackRoute", () => {
    renderGuarded({
      initialUserId: "yozeline-candia",
      allowedRoles: ["executive"],
      fallbackRoute: "/executive",
    });
    expect(screen.getByText("EXEC FALLBACK")).toBeTruthy();
  });

  it("passes when any of multiple allowed roles match", () => {
    renderGuarded({
      initialUserId: "sarah-hooper",
      allowedRoles: ["rm", "manager", "executive", "admin"],
    });
    expect(screen.getByText("GUARDED CONTENT")).toBeTruthy();
  });
});

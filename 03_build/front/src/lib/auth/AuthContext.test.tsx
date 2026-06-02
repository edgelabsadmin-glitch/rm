import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth, useUser } from "./AuthContext";

function Probe() {
  const { accountScope, switchUser } = useAuth();
  const user = useUser();
  return (
    <div>
      <div data-testid="role">{user.role}</div>
      <div data-testid="name">{user.displayName}</div>
      <div data-testid="scope">{accountScope.length}</div>
      <button type="button" onClick={() => switchUser("yozeline-candia")}>
        switch
      </button>
    </div>
  );
}

describe("AuthContext (spec-042 Step-2)", () => {
  it("default initialUserId = pulse-admin → admin role + 14-account scope", () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("role").textContent).toBe("admin");
    expect(screen.getByTestId("scope").textContent).toBe("14");
  });

  it("explicit initialUserId yozeline-candia → rm role + 1-account scope", () => {
    render(
      <AuthProvider initialUserId="yozeline-candia">
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("role").textContent).toBe("rm");
    expect(screen.getByTestId("name").textContent).toBe("Yozeline Candia");
    expect(screen.getByTestId("scope").textContent).toBe("1");
  });

  it("explicit initialUserId iffi-wahla → executive role + 14-account scope", () => {
    render(
      <AuthProvider initialUserId="iffi-wahla">
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("role").textContent).toBe("executive");
    expect(screen.getByTestId("scope").textContent).toBe("14");
  });

  it("switchUser updates user + derived scope on re-render", () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("role").textContent).toBe("admin");
    fireEvent.click(screen.getByRole("button", { name: "switch" }));
    expect(screen.getByTestId("role").textContent).toBe("rm");
    expect(screen.getByTestId("scope").textContent).toBe("1");
  });

  it("useAuth() throws outside an AuthProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/within an AuthProvider/);
    spy.mockRestore();
  });

  it("AuthProvider throws on unknown initialUserId", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <AuthProvider initialUserId="nobody">
          <Probe />
        </AuthProvider>,
      ),
    ).toThrow(/unknown user id/);
    spy.mockRestore();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Header } from "@/components/Header";
import { PulseStateProvider } from "@/components/PulseStateProvider";
import { AuthProvider } from "@/lib/auth/AuthContext";

function renderHeader(initialUserId: string) {
  return render(
    <AuthProvider initialUserId={initialUserId}>
      <PulseStateProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </PulseStateProvider>
    </AuthProvider>,
  );
}

const link = (name: RegExp) => screen.queryByRole("link", { name });

describe("Header role-based nav visibility (spec-042 Step-3)", () => {
  it("Executive: no Queue (/actions) link; Executive View visible; no Settings", () => {
    renderHeader("iffi-wahla");
    expect(link(/^Queue/)).toBeNull();
    expect(link(/Executive View/)).toBeTruthy();
    expect(link(/^Settings$/)).toBeNull();
  });

  it("RM: no Executive View link; no Settings; Queue visible", () => {
    renderHeader("yozeline-candia");
    expect(link(/Executive View/)).toBeNull();
    expect(link(/^Settings$/)).toBeNull();
    expect(link(/^Queue/)).toBeTruthy();
  });

  it("Manager: no Executive View link; no Settings; Queue visible", () => {
    renderHeader("sarah-hooper");
    expect(link(/Executive View/)).toBeNull();
    expect(link(/^Settings$/)).toBeNull();
    expect(link(/^Queue/)).toBeTruthy();
  });

  it("Admin: all nav links visible (Executive View + Settings + Admin + Queue)", () => {
    renderHeader("pulse-admin");
    expect(link(/Executive View/)).toBeTruthy();
    expect(link(/^Settings$/)).toBeTruthy();
    expect(link(/^Admin$/)).toBeTruthy();
    expect(link(/^Queue/)).toBeTruthy();
    expect(link(/Accounts/)).toBeTruthy();
    expect(link(/Constellation/)).toBeTruthy();
  });
});

describe("Header dev persona switcher (spec-042 Step-9 DoD §12)", () => {
  it("renders the dev-only switcher reflecting the current user", () => {
    renderHeader("pulse-admin");
    const sel = screen.getByTestId("dev-user-switcher") as HTMLSelectElement;
    expect(sel.value).toBe("pulse-admin");
  });

  it("switching personas re-derives the role-gated nav (Admin → RM hides Settings)", () => {
    renderHeader("pulse-admin");
    expect(link(/^Settings$/)).toBeTruthy();
    fireEvent.change(screen.getByTestId("dev-user-switcher"), {
      target: { value: "yozeline-candia" },
    });
    expect(link(/^Settings$/)).toBeNull();
    expect(link(/Executive View/)).toBeNull();
    expect(link(/^Queue/)).toBeTruthy();
  });
});

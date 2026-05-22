import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccountListColumn } from "@/features/account/AccountListColumn";
import { CollapsibleSection } from "@/features/account/CollapsibleSection";
import { AuthProvider } from "@/lib/auth/AuthContext";
import {
  SelectedAccountProvider,
  DEFAULT_ACCOUNT_ID,
} from "@/session/SelectedAccountProvider";

// AccountListColumn reads useAuth (scope) + useSelectedAccount.
function renderList(initialUserId = "pulse-admin") {
  return render(
    <AuthProvider initialUserId={initialUserId}>
      <SelectedAccountProvider>
        <AccountListColumn />
      </SelectedAccountProvider>
    </AuthProvider>,
  );
}

describe("CollapsibleSection (opt-in depth, §22)", () => {
  it("is closed by default and opens on click", () => {
    render(
      <CollapsibleSection title="Signal vector">
        <div>secret body</div>
      </CollapsibleSection>,
    );
    const header = screen.getByRole("button", { name: /signal vector/i });
    expect(header).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("secret body")).toBeNull();

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("secret body")).toBeTruthy();
  });
});

describe("AccountListColumn (account switch)", () => {
  it("highlights the default account, and switches on click (admin → full list)", () => {
    renderList("pulse-admin");
    // DHR Health Clinics is the default (aria-current=true).
    const dflt = screen.getByRole("button", { name: /DHR Health Clinics/i });
    expect(dflt.getAttribute("aria-current")).toBe("true");
    expect(DEFAULT_ACCOUNT_ID).toBe("dhr-health-clinics");

    const other = screen.getByRole("button", { name: /ReminderMedia/i });
    expect(other.getAttribute("aria-current")).toBe("false");

    fireEvent.click(other);
    expect(other.getAttribute("aria-current")).toBe("true");
    expect(dflt.getAttribute("aria-current")).toBe("false");
  });
});

describe("AccountListColumn — scope filtering (spec-042 Step-5)", () => {
  // Each account renders exactly one <button>, so the button count = visible account count.
  const cardCount = () => screen.getAllByRole("button").length;

  it("admin sees all 14 accounts", () => {
    renderList("pulse-admin");
    expect(cardCount()).toBe(14);
  });
  it("executive sees all 14 accounts", () => {
    renderList("iffi-wahla");
    expect(cardCount()).toBe(14);
  });
  it("Manager Sarah sees 7 (her team's books)", () => {
    renderList("sarah-hooper");
    expect(cardCount()).toBe(7);
  });
  it("Manager Muhammad sees 7", () => {
    renderList("muhammad-ibrahim");
    expect(cardCount()).toBe(7);
  });
  it("RM Sidra sees her 3 (DHR Clinics + DHR Hospital + Palm)", () => {
    renderList("sidra-zia");
    expect(cardCount()).toBe(3);
    expect(screen.getByRole("button", { name: /DHR Health Clinics/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /ReminderMedia/i })).toBeNull();
  });
  it("RM Sajjal sees his 3 (Mendota + DMV + Cirventis)", () => {
    renderList("sajjal-shaheedi");
    expect(cardCount()).toBe(3);
    expect(screen.getByRole("button", { name: /Mendota/i })).toBeTruthy();
  });
  it("RM Yozeline sees her 1 (Manhattan)", () => {
    renderList("yozeline-candia");
    expect(cardCount()).toBe(1);
    expect(screen.getByRole("button", { name: /Manhattan Restorative/i })).toBeTruthy();
  });
});

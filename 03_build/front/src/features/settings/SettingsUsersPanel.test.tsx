/*
 * SPEC-042 Step-7 — Settings panel /settings/users.
 * The panel is a pure DEMO_USERS view (no AuthContext / router), so it renders bare.
 * Scope counts are NOT hardcoded here — they are the canonical truth from
 * deriveAccountScope over demo_characters.ts (RM own book / Manager team / Exec+Admin full org):
 *   Yozeline 1 · Sajjal 3 · Sidra 3 · Ameer 5 · Sarah 7 · Iffi 14.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SettingsUsersPanel } from "./SettingsUsersPanel";

const renderPanel = () => render(<SettingsUsersPanel />);

const rows = () => screen.getAllByTestId("user-row");
const rowFor = (name: string) =>
  rows().find((el) => el.textContent?.includes(name)) as HTMLElement;

// Filter chips live in the left aside; a string `name` is an EXACT accessible-name match,
// so "RM" hits only the chip (user-row buttons have longer composite names).
const filterChip = (label: string) => screen.getByRole("button", { name: label });
const selectUser = (name: string) => fireEvent.click(rowFor(name));

describe("SettingsUsersPanel — table + role filter (spec-042 Step-7)", () => {
  it("renders all 11 demo users by default", () => {
    renderPanel();
    expect(rows()).toHaveLength(11);
  });

  it("Executive filter → 2 rows (Iffi + Eddy)", () => {
    renderPanel();
    fireEvent.click(filterChip("Executive"));
    expect(rows()).toHaveLength(2);
  });

  it("Manager filter → 2 rows (Sarah + Muhammad)", () => {
    renderPanel();
    fireEvent.click(filterChip("Manager"));
    expect(rows()).toHaveLength(2);
  });

  it("RM filter → 6 rows", () => {
    renderPanel();
    fireEvent.click(filterChip("RM"));
    expect(rows()).toHaveLength(6);
  });

  it("Admin filter → 1 row (Pulse Admin)", () => {
    renderPanel();
    fireEvent.click(filterChip("Admin"));
    expect(rows()).toHaveLength(1);
  });
});

describe("SettingsUsersPanel — selected-user detail (spec-042 Step-7)", () => {
  it("shows the empty state before any selection", () => {
    renderPanel();
    expect(screen.getByText("Click a user to view details.")).toBeTruthy();
  });

  it("clicking a row populates the detail panel", () => {
    renderPanel();
    expect(screen.queryByText("Permissions")).toBeNull();
    selectUser("Sidra Zia");
    expect(screen.getByText("Permissions")).toBeTruthy();
    expect(screen.getByText("Account scope · 3")).toBeTruthy();
  });

  it("scope counts derive from deriveAccountScope (no hardcoding)", () => {
    renderPanel();
    const cases: ReadonlyArray<[string, number]> = [
      ["Yozeline Candia", 1],
      ["Sajjal Shaheedi", 3],
      ["Sidra Zia", 3],
      ["Ameer Ali", 5],
      ["Sarah Hooper", 7],
      ["Iffi Wahla", 14],
    ];
    for (const [name, count] of cases) {
      selectUser(name);
      expect(screen.getByText(`Account scope · ${count}`)).toBeTruthy();
    }
  });

  it("detail lists the in-scope account NAMES (Sidra → her 3 accounts)", () => {
    renderPanel();
    selectUser("Sidra Zia");
    expect(screen.getByText("DHR Health Clinics")).toBeTruthy();
    expect(screen.getByText("DHR Health Hospital")).toBeTruthy();
    expect(screen.getByText("Palm Primary Care Texas")).toBeTruthy();
  });

  it("detail renders the role permission summary (spec §3 matrix)", () => {
    renderPanel();
    selectUser("Sidra Zia");
    expect(screen.getByText(/Action Queue \(own book\)/)).toBeTruthy();
    selectUser("Iffi Wahla");
    expect(screen.getByText(/Executive View/)).toBeTruthy();
  });

  it("Change role CTA reveals the Phase-2 placeholder note", () => {
    renderPanel();
    selectUser("Sidra Zia");
    fireEvent.click(screen.getByRole("button", { name: "Change role" }));
    expect(screen.getByText(/Role assignment workflow coming in Phase 2/)).toBeTruthy();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccountListColumn } from "@/features/account/AccountListColumn";
import { CollapsibleSection } from "@/features/account/CollapsibleSection";
import {
  SelectedAccountProvider,
  DEFAULT_ACCOUNT_ID,
} from "@/session/SelectedAccountProvider";

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
  it("highlights the default account, and switches on click", () => {
    render(
      <SelectedAccountProvider>
        <AccountListColumn />
      </SelectedAccountProvider>,
    );
    // Helix Labs is the default (aria-current=true).
    const helix = screen.getByRole("button", { name: /Helix Labs/i });
    expect(helix.getAttribute("aria-current")).toBe("true");
    expect(DEFAULT_ACCOUNT_ID).toBe("helix-labs");

    const vertex = screen.getByRole("button", { name: /Vertex Group/i });
    expect(vertex.getAttribute("aria-current")).toBe("false");

    fireEvent.click(vertex);
    expect(vertex.getAttribute("aria-current")).toBe("true");
    expect(helix.getAttribute("aria-current")).toBe("false");
  });
});

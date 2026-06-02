import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { composeCapacityImbalance, type CapacityImbalanceCard } from "../composers/rm_capacity_composer";
import { RmCapacityImbalanceOverlay } from "./RmCapacityImbalanceOverlay";

const CARD = composeCapacityImbalance()[0];

describe("RmCapacityImbalanceOverlay (spec-041 Step-6)", () => {
  it("renders the imbalance card with derived numbers", () => {
    render(<RmCapacityImbalanceOverlay card={CARD} x={120} y={120} onInvestigate={() => {}} />);
    expect(screen.getByText(/CAPACITY IMBALANCE/i)).toBeTruthy();
    expect(screen.getByText(/Sajjal Shaheedi carrying significant book risk/)).toBeTruthy();
    // summary uses derived account + churn counts
    expect(screen.getByText(/owns 3 accounts with 2 in churn-state/)).toBeTruthy();
    // meta uses derived comparison + manager
    expect(screen.getByText(/Compare: Yozeline Candia at score 1\.1 · Manager: Sarah Hooper/)).toBeTruthy();
  });

  it("fires onInvestigate with the card when Investigate is clicked", () => {
    const onInvestigate = vi.fn();
    render(<RmCapacityImbalanceOverlay card={CARD} x={0} y={0} onInvestigate={onInvestigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Investigate" }));
    expect(onInvestigate).toHaveBeenCalledWith(CARD);
  });

  it("renders nothing when the imbalance list is empty (overlay-level empty state)", () => {
    const empty: CapacityImbalanceCard[] = [];
    const { container } = render(
      <>
        {empty.map((c) => (
          <RmCapacityImbalanceOverlay key={c.id} card={c} x={0} y={0} onInvestigate={() => {}} />
        ))}
      </>,
    );
    expect(container.querySelector('[role="region"]')).toBeNull();
  });
});

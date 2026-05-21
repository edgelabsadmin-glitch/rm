import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EscalationTierJumpCard } from "../composers/escalation_tier_jump_composer";
import { EscalationTierJumpOverlay } from "./EscalationTierJumpOverlay";

const CARD: EscalationTierJumpCard = {
  id: "escalation-tier-jump-demo-001",
  accountId: "manhattan-restorative",
  accountName: "Manhattan Restorative Health Sciences",
  previousTier: "watch",
  newTier: "at-risk",
  occurredAt: "2026-05-21T08:00:00Z",
  hoursAgo: 12,
  owningRmId: "yozeline-candia",
  owningRmName: "Yozeline Candia",
  reason: "Composite health declined past at-risk threshold",
};

describe("EscalationTierJumpOverlay (spec-041 Step-7)", () => {
  it("renders the escalation card with derived fields", () => {
    render(<EscalationTierJumpOverlay card={CARD} x={100} y={100} onInvestigate={() => {}} />);
    expect(screen.getByText(/TIER ESCALATION/i)).toBeTruthy();
    expect(
      screen.getByText(/Manhattan Restorative Health Sciences escalated to at-risk/),
    ).toBeTruthy();
    expect(screen.getByText(/Health tier moved from watch → at-risk/)).toBeTruthy();
    expect(screen.getByText(/12h ago · Owning RM: Yozeline Candia/)).toBeTruthy();
  });

  it("renders within a role=region for accessibility", () => {
    const { container } = render(
      <EscalationTierJumpOverlay card={CARD} x={0} y={0} onInvestigate={() => {}} />,
    );
    const region = container.querySelector('[role="region"]');
    expect(region).toBeTruthy();
    expect(region!.getAttribute("aria-label")).toMatch(/escalated to at-risk/);
  });

  it("fires onInvestigate with the card when Investigate is clicked", () => {
    const onInvestigate = vi.fn();
    render(<EscalationTierJumpOverlay card={CARD} x={0} y={0} onInvestigate={onInvestigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Investigate" }));
    expect(onInvestigate).toHaveBeenCalledWith(CARD);
  });

  it("renders nothing when there are no cards (overlay-level empty state)", () => {
    const empty: EscalationTierJumpCard[] = [];
    const { container } = render(
      <>
        {empty.map((c) => (
          <EscalationTierJumpOverlay key={c.id} card={c} x={0} y={0} onInvestigate={() => {}} />
        ))}
      </>,
    );
    expect(container.querySelector('[role="region"]')).toBeNull();
  });
});

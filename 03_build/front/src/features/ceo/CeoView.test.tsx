import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CeoView } from "@/features/ceo/CeoView";

describe("CeoView (spec-040 three-column agentic workspace)", () => {
  it("renders the three top-row cards + asks band + numbers strip", () => {
    render(<CeoView />);
    expect(screen.getByText(/Client Stickiness/i)).toBeTruthy();
    expect(screen.getByText(/This week, with Pulse/i)).toBeTruthy();
    expect(screen.getByText(/Upsell Opportunities/i)).toBeTruthy();
    expect(screen.getByText(/What I'd ask of you · 3 this week/i)).toBeTruthy();
    expect(screen.getByText(/Book in numbers/i)).toBeTruthy();
  });

  it("shows the locked ARR figures via the revenue heuristic", () => {
    render(<CeoView />);
    expect(screen.getByText(/\$1\.52M ARR exposure/)).toBeTruthy(); // churn exposure
    expect(screen.getByText("$2.69M")).toBeTruthy(); // book ARR in the strip
  });

  it("has Approve + Edit on each of the 3 asks (stub handlers)", () => {
    render(<CeoView />);
    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(3);
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(3);
  });

  it("renders inline-tag prose as styled spans (not raw tags)", () => {
    const { container } = render(<CeoView />);
    expect(container.querySelector("span.text-risk-high-fg")).toBeTruthy(); // <bad>
    expect(container.innerHTML).not.toContain("<bad>");
  });
});

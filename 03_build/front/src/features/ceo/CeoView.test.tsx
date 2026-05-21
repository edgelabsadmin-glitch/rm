import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CeoView } from "@/features/ceo/CeoView";

describe("CeoView (spec 040 composition)", () => {
  it("renders the header band, the 3 narrative sections, and attribution", () => {
    render(<CeoView />);
    expect(screen.getByText(/This week, with Pulse/i)).toBeTruthy();
    expect(screen.getByText("What's emerging")).toBeTruthy();
    expect(screen.getByText("Where talent matters")).toBeTruthy();
    expect(screen.getByText("What I'd ask of you")).toBeTruthy();
    expect(screen.getByText(/Composed by Pulse/i)).toBeTruthy();
  });

  it("renders inline-tag prose as styled spans (not raw tags)", () => {
    const { container } = render(<CeoView />);
    // <num>/<bad>/<good> become spans; no literal angle-bracket tags leak through.
    expect(container.querySelector("span.font-mono")).toBeTruthy();
    expect(container.querySelector("span.text-risk-high-fg")).toBeTruthy();
    expect(container.innerHTML).not.toContain("<num>");
  });
});

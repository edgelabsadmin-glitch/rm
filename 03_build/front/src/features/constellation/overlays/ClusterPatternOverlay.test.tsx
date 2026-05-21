import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { clusterCentroid, DEMO_PATTERNS, type PatternCard } from "../demo_patterns";
import { ClusterPatternOverlay } from "./ClusterPatternOverlay";

const PATTERN = DEMO_PATTERNS[0];

describe("ClusterPatternOverlay (spec-041 Step-5 cluster-pattern alert)", () => {
  it("renders the pattern card when given a pattern", () => {
    render(<ClusterPatternOverlay pattern={PATTERN} x={100} y={100} onInvestigate={() => {}} />);
    expect(screen.getByText(/PATTERN ALERT/i)).toBeTruthy();
    expect(screen.getByText(PATTERN.title)).toBeTruthy();
    expect(screen.getByText(PATTERN.summary)).toBeTruthy();
    // meta: "Affects N accounts · Owning RM: Sidra Zia"
    expect(screen.getByText(/Affects 2 accounts · Owning RM: Sidra Zia/)).toBeTruthy();
  });

  it("fires onInvestigate with the pattern when Investigate is clicked", () => {
    const onInvestigate = vi.fn();
    render(<ClusterPatternOverlay pattern={PATTERN} x={0} y={0} onInvestigate={onInvestigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Investigate" }));
    expect(onInvestigate).toHaveBeenCalledWith(PATTERN);
  });

  it("renders nothing when the pattern list is empty (overlay-level empty state)", () => {
    const empty: PatternCard[] = [];
    const { container } = render(
      <>
        {empty.map((p) => (
          <ClusterPatternOverlay key={p.id} pattern={p} x={0} y={0} onInvestigate={() => {}} />
        ))}
      </>,
    );
    expect(container.querySelector('[role="region"]')).toBeNull();
  });
});

describe("clusterCentroid", () => {
  const nodes = [
    { id: "dhr-health-clinics", x: -100, y: 200 },
    { id: "manhattan-restorative", x: 100, y: 100 },
    { id: "other", x: 999, y: 999 },
  ];

  it("averages the support-account positions (within their bounds)", () => {
    const c = clusterCentroid(["dhr-health-clinics", "manhattan-restorative"], nodes);
    expect(c).toEqual({ x: 0, y: 150 });
    // centroid lies within the bounding box of the support points
    expect(c!.x).toBeGreaterThanOrEqual(-100);
    expect(c!.x).toBeLessThanOrEqual(100);
    expect(c!.y).toBeGreaterThanOrEqual(100);
    expect(c!.y).toBeLessThanOrEqual(200);
  });

  it("returns null when no support account is positioned yet", () => {
    expect(clusterCentroid(["dhr-health-clinics"], [{ id: "dhr-health-clinics" }])).toBeNull();
    expect(clusterCentroid(["missing"], nodes)).toBeNull();
  });

  it("the demo fixture has at least one pattern", () => {
    expect(DEMO_PATTERNS.length).toBeGreaterThan(0);
  });
});

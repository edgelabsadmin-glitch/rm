import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { deriveAccountScope } from "@/lib/rbac/accountScope";
import type { AccountScope } from "@/lib/rbac/types";
import { clusterCentroid, DEMO_PATTERNS, type PatternCard } from "../demo_patterns";
import { ClusterPatternOverlay } from "./ClusterPatternOverlay";

const PATTERN = DEMO_PATTERNS[0];

// Mirrors the partial-scope filter-out predicate used in Constellation.tsx (spec-042 Step-4):
// a pattern is visible only if EVERY support account is in scope.
function scopedPatterns(scope?: AccountScope) {
  return scope
    ? DEMO_PATTERNS.filter((p) => p.support_account_ids.every((id) => scope.includes(id)))
    : DEMO_PATTERNS;
}

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

describe("cluster-pattern scope filter-out (spec-042 Step-4)", () => {
  // pattern-demo-001 spans DHR Health Clinics (Sidra) + Manhattan Restorative (Yozeline) —
  // two different RMs' books, so only a Manager over both / Executive / Admin sees it.
  it("undefined scope → all patterns visible", () => {
    expect(scopedPatterns(undefined)).toHaveLength(DEMO_PATTERNS.length);
  });

  it("empty scope → zero patterns", () => {
    expect(scopedPatterns([])).toHaveLength(0);
  });

  it("Yozeline (Manhattan only, missing DHR) → pattern filtered out", () => {
    expect(scopedPatterns(deriveAccountScope("rm", "yozeline-candia"))).toHaveLength(0);
  });

  it("Sidra (DHR only, missing Manhattan) → pattern filtered out", () => {
    // Correction vs prompt: Sidra does NOT own Manhattan, so she does NOT see this pattern.
    expect(scopedPatterns(deriveAccountScope("rm", "sidra-zia"))).toHaveLength(0);
  });

  it("Sarah (manages both Sidra + Yozeline → both accounts in scope) → pattern visible", () => {
    expect(scopedPatterns(deriveAccountScope("manager", "sarah-hooper"))).toHaveLength(1);
  });

  it("Executive / Admin (full org) → pattern visible", () => {
    expect(scopedPatterns(deriveAccountScope("admin", "pulse-admin"))).toHaveLength(1);
    expect(scopedPatterns(deriveAccountScope("executive", "iffi-wahla"))).toHaveLength(1);
  });
});

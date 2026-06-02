import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExecutiveView, TeamWorkloadRowView } from "@/features/executive/ExecutiveView";
import type { TeamWorkloadRow } from "@/features/executive/composers/team_workload_composer";
import { AuthProvider } from "@/lib/auth/AuthContext";

// ExecutiveView now reads useAuth (scope) + useNavigate (row → constellation deep-link), so
// the harness wraps it in AuthProvider + a Router. useNavigate is mocked to assert the target.
const navigateMock = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock };
});

function renderExec(initialUserId = "iffi-wahla") {
  return render(
    <AuthProvider initialUserId={initialUserId}>
      <MemoryRouter>
        <ExecutiveView />
      </MemoryRouter>
    </AuthProvider>,
  );
}

beforeEach(() => navigateMock.mockClear());

describe("ExecutiveView (spec-040 three-column agentic workspace)", () => {
  it("renders the three top-row cards + asks band + numbers strip", () => {
    renderExec();
    expect(screen.getByText(/Client Stickiness/i)).toBeTruthy();
    expect(screen.getByText(/This week, with Pulse/i)).toBeTruthy();
    expect(screen.getByText(/Upsell Opportunities/i)).toBeTruthy();
    expect(screen.getByText(/What I'd ask of you · 3 this week/i)).toBeTruthy();
    expect(screen.getByText(/Book in numbers/i)).toBeTruthy();
  });

  it("shows the locked ARR figures via the revenue heuristic", () => {
    renderExec();
    expect(screen.getByText(/\$1\.52M ARR exposure/)).toBeTruthy(); // churn exposure
    expect(screen.getByText("$2.69M")).toBeTruthy(); // book ARR in the strip
  });

  it("has Approve + Edit on each of the 3 asks (stub handlers)", () => {
    renderExec();
    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(3);
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(3);
  });

  it("renders inline-tag prose as styled spans (not raw tags)", () => {
    const { container } = renderExec();
    expect(container.querySelector("span.font-mono")).toBeTruthy(); // <num>
    expect(container.querySelector("span.italic")).toBeTruthy(); // <em>
    expect(container.innerHTML).not.toContain("<num>");
    expect(container.innerHTML).not.toContain("<em>");
  });
});

describe("ExecutiveView — Team workload panel (spec-042 Step-8 §6.6)", () => {
  it("renders the panel for an Executive viewer", () => {
    renderExec("iffi-wahla");
    expect(screen.getByText(/Team workload/i)).toBeTruthy();
  });

  it("renders the panel for an Admin viewer", () => {
    renderExec("pulse-admin");
    expect(screen.getByText(/Team workload/i)).toBeTruthy();
  });

  it("shows all 6 RM rows for an Executive (full-org scope)", () => {
    renderExec("iffi-wahla");
    expect(screen.getAllByTestId("team-workload-row")).toHaveLength(6);
  });

  it("rows are sorted by combinedLoad descending — Sajjal at the top", () => {
    renderExec("iffi-wahla");
    const rows = screen.getAllByTestId("team-workload-row");
    expect(rows[0].textContent).toContain("Sajjal Shaheedi");
  });

  it("clicking a row deep-links to /constellation?rm=<rm-id>", () => {
    renderExec("iffi-wahla");
    const top = screen.getAllByTestId("team-workload-row")[0];
    fireEvent.click(top);
    expect(navigateMock).toHaveBeenCalledWith("/constellation?rm=sajjal-shaheedi");
  });
});

describe("TeamWorkloadRowView — overload warning styling (synthetic rows)", () => {
  const baseRow: TeamWorkloadRow = {
    rmId: "synthetic-rm",
    rmName: "Synthetic RM",
    avatarInitials: "SR",
    pendingCount: 0,
    approvedThisWeek: 0,
    modifiedThisWeek: 0,
    rejectedThisWeek: 0,
    throughputIndicator: "flat",
    combinedLoad: 0,
  };
  const renderRow = (row: TeamWorkloadRow) =>
    render(
      <MemoryRouter>
        <table>
          <tbody>
            <TeamWorkloadRowView row={row} onSelect={() => {}} />
          </tbody>
        </table>
      </MemoryRouter>,
    );

  it("does NOT flag warning below the threshold (fixture-realistic load)", () => {
    renderRow({ ...baseRow, pendingCount: 2 });
    expect(screen.getByTestId("team-workload-row").getAttribute("data-warning")).toBe("false");
  });

  it("flags warning at/above the threshold (pendingCount >= 6)", () => {
    renderRow({ ...baseRow, pendingCount: 7 });
    expect(screen.getByTestId("team-workload-row").getAttribute("data-warning")).toBe("true");
  });
});

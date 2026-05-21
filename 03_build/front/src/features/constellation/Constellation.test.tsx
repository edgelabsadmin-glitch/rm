import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { SelectedAccountProvider } from "@/session/SelectedAccountProvider";
import { Constellation } from "./Constellation";
import { buildConstellationGraph } from "./fixtures";
import {
  ConstellationEmpty,
  ConstellationError,
  ConstellationLoading,
} from "./states/ConstellationStates";

describe("Constellation defensive states (spec-041 Step-8)", () => {
  it("loading state renders the skeleton + label", () => {
    render(<ConstellationLoading />);
    expect(screen.getByText(/Loading constellation/i)).toBeTruthy();
  });

  it("error state renders the headline, message + retry", () => {
    render(<ConstellationError message="boom" onRetry={() => {}} />);
    expect(screen.getByText(/Couldn't load constellation/i)).toBeTruthy();
    expect(screen.getByText(/API error · boom/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("empty state renders the no-accounts message", () => {
    render(<ConstellationEmpty />);
    expect(screen.getByText(/No accounts in your view/i)).toBeTruthy();
  });

  it("accountScope=[] renders the empty state (RBAC scope-empty)", () => {
    render(
      <MemoryRouter>
        <SelectedAccountProvider>
          <Constellation accountScope={[]} />
        </SelectedAccountProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText(/No accounts in your view/i)).toBeTruthy();
  });
});

describe("buildConstellationGraph accountScope filtering", () => {
  const accountNodes = (scope?: string[]) =>
    buildConstellationGraph(scope).nodes.filter((n) => n.type === "account");

  it("undefined scope = all 14 accounts (no scoping, Phase-1 default)", () => {
    expect(accountNodes(undefined)).toHaveLength(14);
  });

  it("scope=['dhr-health-clinics'] yields only that account node", () => {
    const accts = accountNodes(["dhr-health-clinics"]);
    expect(accts).toHaveLength(1);
    expect(accts[0].id).toBe("dhr-health-clinics");
  });

  it("scope=[] yields zero account nodes (drives the empty state)", () => {
    expect(accountNodes([])).toHaveLength(0);
    // the org scaffold (globe + managers + RMs) still renders
    expect(buildConstellationGraph([]).nodes.some((n) => n.type === "globe")).toBe(true);
  });
});

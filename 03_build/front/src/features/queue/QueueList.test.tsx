import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { QueueList } from "./QueueList";

function renderQueue(initialUserId = "pulse-admin") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider initialUserId={initialUserId}>
        <MemoryRouter>
          <QueueList />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => localStorage.clear());

const btn = (name: string | RegExp) => screen.queryByRole("button", { name });

describe("QueueList filter UI (spec-042 Step-5 follow-up Q3)", () => {
  it("renders Status chips (Active/Approved/All)", () => {
    renderQueue();
    expect(btn("Active")).toBeTruthy();
    expect(btn("Approved")).toBeTruthy();
    expect(btn("All")).toBeTruthy();
  });

  it("renders Time chips (All time/Today/This week)", () => {
    renderQueue();
    expect(btn("All time")).toBeTruthy();
    expect(btn("Today")).toBeTruthy();
    expect(btn("This week")).toBeTruthy();
  });

  it("renders Tier chips (Core/Growth/Strategic)", () => {
    renderQueue();
    expect(btn("Core")).toBeTruthy();
    expect(btn("Growth")).toBeTruthy();
    expect(btn("Strategic")).toBeTruthy();
  });

  it("no longer renders the dead My Queue / Overall toggle", () => {
    renderQueue();
    expect(btn("My Queue")).toBeNull();
    expect(btn("Overall")).toBeNull();
  });
});

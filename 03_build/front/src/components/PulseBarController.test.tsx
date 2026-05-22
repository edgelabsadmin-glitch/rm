import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PulseBarController } from "@/components/PulseBarController";
import { PulseStateProvider, usePulseState } from "@/components/PulseStateProvider";
import { AuthProvider } from "@/lib/auth/AuthContext";

function Count() {
  const { queueCount } = usePulseState();
  return <div data-testid="count">{queueCount}</div>;
}

function renderController(initialUserId: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider initialUserId={initialUserId}>
        <PulseStateProvider>
          <PulseBarController />
          <Count />
        </PulseStateProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const count = () => screen.getByTestId("count").textContent;

// The demo fallback (DEV) supplies the 5 cards; the badge reflects the caller's ROLE SCOPE.
describe("PulseBarController badge scope (spec-042 Step-5 follow-up Q2)", () => {
  it("RM Sidra → 1 (her own card)", async () => {
    renderController("sidra-zia");
    await waitFor(() => expect(count()).toBe("1"));
  });

  it("Manager Sarah → 3 (team total, not 0)", async () => {
    renderController("sarah-hooper");
    await waitFor(() => expect(count()).toBe("3"));
  });

  it("Admin → 5 (all cards)", async () => {
    renderController("pulse-admin");
    await waitFor(() => expect(count()).toBe("5"));
  });
});

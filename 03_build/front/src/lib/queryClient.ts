import { QueryClient } from "@tanstack/react-query";

/*
 * SPEC-034 — React Query client (server-state, audit disposition D7). Server state
 * only; selected-account state is URL-param-driven, ephemeral agent state is the
 * PulseStateProvider context, forms use react-hook-form. No Redux/Zustand.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

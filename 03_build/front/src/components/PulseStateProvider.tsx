/*
 * SPEC-034 — Pulse Bar state context (singleton, ephemeral).
 * Holds the agent-presence state + pending Action Queue count that the chrome-level
 * Pulse Bar (§8.14) and the header Queue badge read. Idle by default.
 *
 * Phase 1 transport is 10s POLLING (pre-034 sequencing decision; SSE/WebSocket
 * deferred to v1.5+ candidate #23). Spec 038 wires the poll to the back-end
 * (agent_state_change + action_suggested_count); 034 ships the provider as a
 * drop-in with a static idle default so the bar mounts on every surface now.
 */
import { createContext, useContext, useMemo, useState } from "react";

export type PulseState = "idle" | "processing" | "ready";

interface PulseStateValue {
  state: PulseState;
  queueCount: number;
  setState: (s: PulseState) => void;
  setQueueCount: (n: number) => void;
}

const PulseStateContext = createContext<PulseStateValue | null>(null);

export function PulseStateProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PulseState>("idle");
  const [queueCount, setQueueCount] = useState(0);
  // NOTE (spec 038): replace with a 10s poll of GET /api/agent/state →
  // { state, queueCount }. Keep the 600ms heartbeat serialization client-side.
  const value = useMemo(
    () => ({ state, queueCount, setState, setQueueCount }),
    [state, queueCount],
  );
  return <PulseStateContext.Provider value={value}>{children}</PulseStateContext.Provider>;
}

export function usePulseState(): PulseStateValue {
  const v = useContext(PulseStateContext);
  if (!v) throw new Error("usePulseState must be used within PulseStateProvider");
  return v;
}

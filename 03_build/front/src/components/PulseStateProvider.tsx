/*
 * SPEC-038 — Pulse Bar state lifecycle (Tier-0 §8.14). Singleton, ephemeral.
 *
 * Effective state (deriveState):
 *   ready      — a 600ms heartbeat is animating (a new action just landed)
 *   processing — ≥1 fetch/mutation in flight ("processing state stacks")
 *   idle       — nothing happening (1px / 0.15 default)
 *
 * Heartbeats SERIALIZE at one per 600ms (§8.14): a batch of new cards enqueues a
 * heartbeat; the queue drains one-at-a-time so heartbeats never overlap. Phase-1
 * transport is 10s polling (PulseBarController); SSE/WebSocket is v1.5+ #23.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

export type PulseState = "idle" | "processing" | "ready";

export const HEARTBEAT_MS = 600;

/** Pure: the visible bar state from the lifecycle flags (unit-tested). */
export function deriveState(heartbeatActive: boolean, processing: boolean): PulseState {
  if (heartbeatActive) return "ready";
  if (processing) return "processing";
  return "idle";
}

interface PulseStateValue {
  state: PulseState;
  queueCount: number;
  setQueueCount: (n: number) => void;
  setProcessing: (b: boolean) => void;
  notifyNewActions: (count: number) => void;
}

const PulseStateContext = createContext<PulseStateValue | null>(null);

export function PulseStateProvider({ children }: { children: React.ReactNode }) {
  const [queueCount, setQueueCount] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [heartbeatActive, setHeartbeatActive] = useState(false);
  const [queued, setQueued] = useState(0); // pending heartbeats
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Drain one heartbeat per 600ms; the timer lives in a ref so re-renders don't
  // clear it mid-flight. When it ends, heartbeatActive flips → effect re-runs →
  // fires the next queued heartbeat if any.
  useEffect(() => {
    if (!heartbeatActive && queued > 0) {
      setQueued((q) => q - 1);
      setHeartbeatActive(true);
      timer.current = setTimeout(() => setHeartbeatActive(false), HEARTBEAT_MS);
    }
  }, [heartbeatActive, queued]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const notifyNewActions = useCallback((count: number) => {
    if (count > 0) setQueued((q) => q + 1); // one announcement per batch
  }, []);

  const value = useMemo<PulseStateValue>(
    () => ({
      state: deriveState(heartbeatActive, processing),
      queueCount,
      setQueueCount,
      setProcessing,
      notifyNewActions,
    }),
    [heartbeatActive, processing, queueCount, notifyNewActions],
  );
  return <PulseStateContext.Provider value={value}>{children}</PulseStateContext.Provider>;
}

export function usePulseState(): PulseStateValue {
  const v = useContext(PulseStateContext);
  if (!v) throw new Error("usePulseState must be used within PulseStateProvider");
  return v;
}

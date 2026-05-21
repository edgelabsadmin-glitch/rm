import { describe, expect, it } from "vitest";
import { deriveState } from "@/components/PulseStateProvider";

describe("deriveState (Pulse Bar §8.14 lifecycle)", () => {
  it("heartbeat wins over processing → ready", () => {
    expect(deriveState(true, true)).toBe("ready");
    expect(deriveState(true, false)).toBe("ready");
  });
  it("processing when in-flight and no heartbeat", () => {
    expect(deriveState(false, true)).toBe("processing");
  });
  it("idle when nothing happening", () => {
    expect(deriveState(false, false)).toBe("idle");
  });
});

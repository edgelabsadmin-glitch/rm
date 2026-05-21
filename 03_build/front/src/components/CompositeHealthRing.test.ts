import { describe, expect, it } from "vitest";
import { scoreToAngle } from "@/components/CompositeHealthRing";

describe("scoreToAngle (Tier-0 §8.8 — 270° max)", () => {
  it("score 10 → 270°", () => expect(scoreToAngle(10)).toBe(270));
  it("score 5 → 135°", () => expect(scoreToAngle(5)).toBe(135));
  it("score 0 → 0°", () => expect(scoreToAngle(0)).toBe(0));
  it("score 6.4 → 172.8°", () => expect(scoreToAngle(6.4)).toBeCloseTo(172.8));
  it("clamps above 10", () => expect(scoreToAngle(12)).toBe(270));
  it("clamps below 0", () => expect(scoreToAngle(-3)).toBe(0));
});

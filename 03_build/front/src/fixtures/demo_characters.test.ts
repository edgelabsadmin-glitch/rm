import { describe, expect, it } from "vitest";
import {
  accountARR,
  bookARR,
  churnExposureARR,
  formatARR,
  REVENUE_PER_SEAT_USD,
} from "@/fixtures/demo_characters";

describe("revenue heuristic ($10K/seat, SPEC-041 Phase-1)", () => {
  it("per-seat heuristic is $10K", () => expect(REVENUE_PER_SEAT_USD).toBe(10_000));
  it("book ARR = 269 active × $10K = $2.69M", () => expect(bookARR()).toBe(2_690_000));
  it("DHR Health Clinics (76) = $760K", () =>
    expect(accountARR("dhr-health-clinics")).toBe(760_000));
  it("Mendota Insurance (42) = $420K", () =>
    expect(accountARR("mendota-insurance")).toBe(420_000));
  it("churn exposure (5 at-risk + churn-signal accounts) = $1.52M", () =>
    expect(churnExposureARR()).toBe(1_520_000));
  it("unknown account → $0", () => expect(accountARR("nope")).toBe(0));
});

describe("formatARR (compact currency)", () => {
  it("$760K", () => expect(formatARR(760_000)).toBe("$760K"));
  it("$2.69M", () => expect(formatARR(2_690_000)).toBe("$2.69M"));
  it("$1.5M (trailing zero trimmed)", () => expect(formatARR(1_500_000)).toBe("$1.5M"));
  it("$2M (both zeros trimmed)", () => expect(formatARR(2_000_000)).toBe("$2M"));
  it("$10K", () => expect(formatARR(10_000)).toBe("$10K"));
});

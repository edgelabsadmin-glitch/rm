import { describe, expect, it } from "vitest";
import { DEMO_ACCOUNTS } from "@/fixtures/demo_characters";
import type { UserRole } from "./types";
import { deriveAccountScope } from "./accountScope";

const ALL = DEMO_ACCOUNTS.length; // 14 (derived, not hardcoded)

describe("deriveAccountScope — RM own book (derived from canonical fixture)", () => {
  it("yozeline-candia → exactly ['manhattan-restorative']", () => {
    expect(deriveAccountScope("rm", "yozeline-candia")).toEqual(["manhattan-restorative"]);
  });

  it("sajjal-shaheedi → 3 accounts, all owned by sajjal", () => {
    const scope = deriveAccountScope("rm", "sajjal-shaheedi");
    expect(scope).toHaveLength(3);
    expect(scope.every((id) => DEMO_ACCOUNTS.find((a) => a.id === id)?.rmId === "sajjal-shaheedi")).toBe(true);
  });

  it("sidra-zia → 3 accounts, all owned by sidra", () => {
    const scope = deriveAccountScope("rm", "sidra-zia");
    expect(scope).toHaveLength(3);
    expect(scope.every((id) => DEMO_ACCOUNTS.find((a) => a.id === id)?.rmId === "sidra-zia")).toBe(true);
  });

  it("ameer-ali → 5 accounts", () => {
    expect(deriveAccountScope("rm", "ameer-ali")).toHaveLength(5);
  });

  it("mubeen-sohail → 1 account", () => {
    expect(deriveAccountScope("rm", "mubeen-sohail")).toHaveLength(1);
  });

  it("akash-tahir → 1 account", () => {
    expect(deriveAccountScope("rm", "akash-tahir")).toHaveLength(1);
  });

  it("nonexistent RM → [] (empty scope)", () => {
    expect(deriveAccountScope("rm", "nonexistent-user")).toEqual([]);
  });
});

describe("deriveAccountScope — Manager team book (derived via team RMs)", () => {
  it("sarah-hooper → 7 accounts (Sidra 3 + Sajjal 3 + Yozeline 1)", () => {
    const scope = deriveAccountScope("manager", "sarah-hooper");
    expect(scope).toHaveLength(7);
    // equals the union of her RMs' books
    const union = [
      ...deriveAccountScope("rm", "sidra-zia"),
      ...deriveAccountScope("rm", "sajjal-shaheedi"),
      ...deriveAccountScope("rm", "yozeline-candia"),
    ];
    expect(new Set(scope)).toEqual(new Set(union));
  });

  it("muhammad-ibrahim → 7 accounts (Ameer 5 + Mubeen 1 + Akash 1)", () => {
    expect(deriveAccountScope("manager", "muhammad-ibrahim")).toHaveLength(7);
  });

  it("nonexistent manager → [] (no team RMs)", () => {
    expect(deriveAccountScope("manager", "nobody")).toEqual([]);
  });
});

describe("deriveAccountScope — Executive / Admin full org", () => {
  it("executive (iffi-wahla) → all accounts", () => {
    expect(deriveAccountScope("executive", "iffi-wahla")).toHaveLength(ALL);
  });

  it("admin (pulse-admin) → all accounts", () => {
    expect(deriveAccountScope("admin", "pulse-admin")).toHaveLength(ALL);
  });

  it("executive/admin scope ignores userId (always full org)", () => {
    expect(deriveAccountScope("executive", "whatever")).toHaveLength(ALL);
  });
});

describe("deriveAccountScope — invalid role", () => {
  it("throws on an unknown role", () => {
    expect(() => deriveAccountScope("invalid" as UserRole, "x")).toThrow(/Unknown role/);
  });
});

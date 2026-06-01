import { describe, expect, it } from "vitest";
import { DEMO_MANAGERS, DEMO_RMS, DEMO_USERS } from "./demo_characters";

describe("DEMO_USERS integrity (spec-042 Step-1)", () => {
  it("has exactly 11 users", () => {
    expect(DEMO_USERS).toHaveLength(11);
  });

  it("every id is unique", () => {
    const ids = DEMO_USERS.map((u) => u.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every email is unique", () => {
    const emails = DEMO_USERS.map((u) => u.email);
    expect(new Set(emails).size).toBe(emails.length);
  });

  it("all RM users have an rmId matching a canonical DEMO_RMS entry", () => {
    const rmIds = new Set(DEMO_RMS.map((r) => r.id));
    const rmUsers = DEMO_USERS.filter((u) => u.role === "rm");
    expect(rmUsers).toHaveLength(6);
    for (const u of rmUsers) {
      expect(u.rmId).toBeDefined();
      expect(rmIds.has(u.rmId!)).toBe(true);
    }
  });

  it("all Manager users have a managerId matching a canonical DEMO_MANAGERS entry", () => {
    const managerIds = new Set(DEMO_MANAGERS.map((m) => m.id));
    const managerUsers = DEMO_USERS.filter((u) => u.role === "manager");
    expect(managerUsers).toHaveLength(2);
    for (const u of managerUsers) {
      expect(u.managerId).toBeDefined();
      expect(managerIds.has(u.managerId!)).toBe(true);
    }
  });

  it("Iffi is on edgeonline.co; everyone else on onedge.co", () => {
    const iffi = DEMO_USERS.find((u) => u.id === "iffi-wahla")!;
    expect(iffi.email).toBe("iffi.wahla@edgeonline.co");
    for (const u of DEMO_USERS) {
      if (u.id === "iffi-wahla") continue;
      expect(u.email.endsWith("@onedge.co")).toBe(true);
    }
  });

  it("avatar initials are exactly 2 characters", () => {
    for (const u of DEMO_USERS) {
      expect(u.avatarInitials).toHaveLength(2);
    }
  });
});

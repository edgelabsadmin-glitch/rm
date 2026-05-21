/*
 * SPEC-034 — Stubbed session.
 * Real identity comes from Google Workspace OAuth in spec 043 (OAuth completion
 * is spec 043's DoD, not 034's — pre-034 audit sequencing decision). Until then
 * the shell runs against a hardcoded demo RM so every authed surface can render.
 *
 * `role` drives front-end route VISIBILITY only (e.g. hiding /admin). It is NOT a
 * security boundary — server-side scope (spec 042 derive_scope) is authoritative.
 */
import { createContext, useContext } from "react";

export type Role = "rm" | "manager" | "admin";

export interface Session {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export const STUB_SESSION: Session = {
  id: "rm-demo",
  name: "Demo RM",
  email: "demo@onedge.co",
  role: "admin", // demo runs as admin so /admin/* is reachable in dev; 043 replaces this
};

export const SessionContext = createContext<Session>(STUB_SESSION);

export function useSession(): Session {
  return useContext(SessionContext);
}

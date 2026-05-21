/*
 * SPEC-034 — AppShell (the chrome singleton). Renders on every AUTHED route via
 * the router's layout element. Owns the header, the Pulse Bar (mounted ONCE here,
 * directly below the header per §8.14 — "part of the chrome, not the content"),
 * and the routed content <Outlet/>. The two-layer Edge surface (page bg + chrome
 * card) comes from Tier-0 §9.1.
 */
import { Outlet } from "react-router-dom";
import { AppShellChrome } from "@/components/AppShellChrome";

export function AppShell() {
  return (
    <AppShellChrome>
      <Outlet />
    </AppShellChrome>
  );
}

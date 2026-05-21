/*
 * SPEC-034 / §8.14 LOCKED — Pulse Bar (Breathing). The single, canonical agent-
 * presence indicator. Chrome-level singleton: same on every authed surface, does
 * not scroll, does not resize with content. CSS-keyframes only (the animation
 * lives in tokens.css `.pulse-bar`), NOT framer-motion — pre-034 audit disposition.
 *
 * This component is intentionally thin: it renders the bar and binds `data-state`.
 * The state itself comes from PulseStateProvider (spec 038 feeds it via polling).
 */
import { usePulseState } from "@/components/PulseStateProvider";

export function PulseBar() {
  const { state } = usePulseState();
  return <div className="pulse-bar" data-state={state} role="presentation" aria-hidden="true" />;
}

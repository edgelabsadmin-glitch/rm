/*
 * SPEC-034 — the single Phase-1 state-transition motion (Tier-0 §7): fade-and-lift,
 * 250ms ease-out. Per-component, keyed re-mount (no root AnimatePresence in Phase 1;
 * exit motion is deferred to the first surface that needs it — likely spec 035).
 * Respects prefers-reduced-motion (§7 rule 6) by collapsing to an instant render.
 */
import { motion, useReducedMotion } from "framer-motion";

export function FadeLift({
  children,
  motionKey,
}: {
  children: React.ReactNode;
  motionKey?: string | number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      key={motionKey}
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

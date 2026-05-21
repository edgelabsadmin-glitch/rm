/*
 * SPEC-036 — Composite Health Ring (Tier-0 §8.8, LOCKED Session 10 / §6 #27).
 * 270° conic-gradient signature. The arc is "continuously evaluated", not a closed
 * verdict: score 10 → 270° (3/4 circle), score 0 → 0°. angle = (score/10)·270.
 *
 * Per §8.8 + the React preview, the FILLED arc is white and the unfilled arc is a
 * translucent white track — because the ring sits ON the purple hero. (The spec-037
 * directive said "brand fill"; that conflicts with §8.8/preview and would be near-
 * invisible on the brand background — followed the locked design, flagged in report.)
 */
export const SCORE_MAX = 10;
export const ARC_MAX_DEG = 270;

/** score (0-10) → filled-arc degrees (0-270), clamped. */
export function scoreToAngle(score: number): number {
  const clamped = Math.max(0, Math.min(SCORE_MAX, score));
  return (clamped / SCORE_MAX) * ARC_MAX_DEG;
}

export function CompositeHealthRing({ score }: { score: number }) {
  const angle = scoreToAngle(score);
  return (
    <div
      className="grid h-28 w-28 place-items-center rounded-full"
      style={{
        background: `conic-gradient(var(--color-text-on-brand) ${angle}deg, var(--color-ring-track) 0deg)`,
      }}
      role="img"
      aria-label={`Composite health ${score} out of ${SCORE_MAX}`}
    >
      <div className="grid h-20 w-20 place-items-center rounded-full bg-brand-deep">
        <div className="text-center">
          <div className="text-2xl font-bold text-ink-on-brand">{score}</div>
          <div className="text-2xs uppercase tracking-widest text-ink-on-brand-faint">Health</div>
        </div>
      </div>
    </div>
  );
}

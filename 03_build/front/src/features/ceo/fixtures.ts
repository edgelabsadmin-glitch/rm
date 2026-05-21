/*
 * SPEC-040 — CEO View weekly fixture (pulse-api/composer not built; the LLM-driven
 * ceo_view_composer.py + email + static-HTML fallback land later — this spec renders
 * the React surface against fixture data only).
 *
 * Voice (Design 08 §"Tone and voice spec"): "Pulse, on behalf of the book." Candid,
 * specific, credits RMs by name, names losses without finger-pointing, numbers in
 * <num> so they can be challenged, no empty optimism. Prose carries the inline-tag
 * whitelist (Tier-0 §10) — rendered by the spec-035 renderer.
 *
 * API contract the composer WILL emit (Week-4 wiring; matches Design 08 §"Layout"):
 *   GET /ceo/weekly  →  CeoWeekly (this shape)
 */
export interface TalentPairing {
  talent: string;
  account: string;
  note: string; // inline-tag prose
}

export interface CeoWeekly {
  week_of: string;
  recipients: string[]; // CEO + VP-CS (Q90 default)
  lead: string; // the foregrounded "one thing you might miss" — inline-tag prose
  emerging: string[]; // 2-3 themes, inline-tag prose
  talent_matters: TalentPairing[]; // 1-2 pairings
  asks: string[]; // 1-3 CEO-warranted asks; empty → section is skipped (Q94)
  signal_sources_count: number;
}

// Phase-1 demo week — reuses the spec-037 accounts (Helix / Mendota / Vertex).
export const CEO_WEEKLY: CeoWeekly = {
  week_of: "May 17 → 23, 2026",
  recipients: ["Eddy · CEO", "VP · Client Success"],
  lead:
    "The one to watch this week is <em>Helix Labs</em> — their renewal lands in " +
    "<num>3</num> days and the signals are mixed. We delivered a replacement on time, " +
    "but a <bad>senior-talent pay concern</bad> surfaced and the champion has gone " +
    "quiet for <num>21</num> days. I'd rather we walk in Thursday with a plan than a hope.",
  emerging: [
    "<bad>Vendor-consolidation</bad> language is spreading — <num>2</num> accounts " +
      "raised it this month (Helix Labs, Mendota Health). Individually it's noise; " +
      "together it looks like a market signal worth a Sales positioning play.",
    "Vertex Group keeps getting healthier — <good>adoption rising and a strong " +
      "ambassador pool</good>. Priya R. has built real trust there; it's our cleanest " +
      "reference-ask candidate this quarter.",
  ],
  talent_matters: [
    {
      talent: "Senior coder cohort",
      account: "Helix Labs",
      note:
        "<bad>Pay concern raised by senior talent</bad> — this is the human signal " +
        "underneath Helix's renewal risk, not a separate issue. Worth naming directly Thursday.",
    },
    {
      talent: "Placed RNs",
      account: "Mendota Health",
      note:
        "<good>Burnout mentions easing</good> since the schedule change — Jordan's work " +
        "is landing. The recurring recognition gap is the one item still on watch.",
    },
  ],
  asks: [
    "<num>2</num> minutes on Helix Labs before Thursday: do we escalate the pay-concern " +
      "signal into a retention play, or hold and listen at the renewal?",
    "A read on the <bad>vendor-consolidation</bad> pattern — should we run a short Sales " +
      "play across the <num>2</num> accounts in the next 30 days?",
  ],
  signal_sources_count: 14,
};

export function getCeoWeekly(): CeoWeekly {
  return CEO_WEEKLY;
}

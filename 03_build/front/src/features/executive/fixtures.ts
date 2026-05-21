/*
 * SPEC-040 — Executive View weekly fixture (pulse-api/composer not built; the LLM-driven
 * exec_view_composer.py + email + static-HTML fallback land later — this spec renders
 * the React surface against fixture data only).
 *
 * Voice (Design 08 §"Tone and voice spec"): "Pulse, on behalf of the book." Candid,
 * specific, credits RMs by name, names losses without finger-pointing, numbers in
 * <num> so they can be challenged, no empty optimism. Prose carries the inline-tag
 * whitelist (Tier-0 §10) — rendered by the spec-035 renderer.
 *
 * API contract the composer WILL emit (Week-4 wiring; matches Design 08 §"Layout"):
 *   GET /executive/weekly  →  CeoWeekly (this shape)
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

// Phase-1 demo week — real accounts/RMs/talent from demo_characters.ts.
export const CEO_WEEKLY: CeoWeekly = {
  week_of: "May 17 → 23, 2026",
  recipients: ["Iffi Wahla · CEO", "Eddy Chen · VP Client Success"],
  lead:
    "The one to watch this week is <em>DHR Health Clinics</em> — our largest book at " +
    "<num>76</num> active placements, and churn risk just crossed <num>50%</num>. Sidra " +
    "has held the relationship well, but a <bad>vendor-consolidation</bad> signal is now " +
    "showing across two accounts. I'd rather we get ahead of it than react to a renewal note.",
  emerging: [
    "<bad>Vendor-consolidation</bad> language surfaced at <num>2</num> accounts this month — " +
      "DHR Health Clinics and Mendota Insurance. Individually it's noise; together it reads " +
      "like a market signal worth a short Sales positioning play.",
    "Mubeen's book is our quiet win — <good>NAVADERM holding healthy at 14 active placements</good>, " +
      "no escalations. It's our cleanest reference-ask candidate this quarter.",
  ],
  talent_matters: [
    {
      talent: "Senior placement cohort",
      account: "DHR Health Clinics",
      note:
        "<bad>Replacement rate elevated</bad> across the <num>76</num> active placements — this is " +
        "the human signal underneath the churn number, not a separate issue. Sidra should name it directly.",
    },
    {
      talent: "Placed associates",
      account: "Manhattan Restorative",
      note:
        "<bad>Escalated to 90% churn</bad> on Yozeline's book — <num>10</num> active placements still " +
        "in play. The escalation is open; this is the one I'd watch alongside DHR.",
    },
  ],
  asks: [
    "<num>2</num> minutes on DHR Health Clinics before the renewal: do we escalate the " +
      "vendor-consolidation signal into a retention play, or hold and listen?",
    "A read on the <bad>vendor-consolidation</bad> pattern — should we run a short Sales play " +
      "across the <num>2</num> accounts in the next 30 days?",
  ],
  signal_sources_count: 14,
};

export function getCeoWeekly(): CeoWeekly {
  return CEO_WEEKLY;
}

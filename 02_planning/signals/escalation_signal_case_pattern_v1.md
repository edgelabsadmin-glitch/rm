# escalation_signal_case_pattern_v1

**Version:** v1
**Category:** escalation
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 05 (escalation-router) — primary; Skill 10 (cross-account-pattern-finder)
**Status:** active

## Plain-English definition

Multiple risk-tagged Cases at the same customer share a theme (same category, or same root cause described in their descriptions) within a recent window. A single Case is the customer raising a problem; a pattern across Cases is the customer telling EDGE there's a systemic issue.

## Detection mechanism

**Type:** hybrid — rule on the existing `Case.Categories__c` taxonomy + LLM clustering of free-text descriptions

**Rule layer (category-based):**
```
For each Customer:
  cases_60d = retrieve(sfdc.Case where AccountId=Customer
                                  AND Categories__c IS NOT NULL
                                  AND Categories__c LIKE 'Risk%'   # EDGE risk taxonomy
                                  AND CreatedDate >= today - 60)
  if len(cases_60d) < 2:
    return None

  # Group by category
  by_category = group_by(cases_60d, key='Categories__c')
  pattern_categories = [cat for cat, cases in by_category.items() if len(cases) >= 2]

  if not pattern_categories:
    # Fall through to LLM clustering
    return llm_cluster(cases_60d)

  severity = 'medium' if any(len(cases) >= 2 for cases in by_category.values()) else 'low'
  severity = 'high' if any(len(cases) >= 3 for cases in by_category.values()) else severity
  fire(severity, pattern_categories=pattern_categories)
```

**LLM clustering (when categories differ but descriptions echo a theme):**
```
Prompt input: list of {case_number, category, description, details}.
Prompt: "Identify whether these cases share a root cause or thematic concern.
Output JSON with: {has_pattern: bool, theme: '<short>', evidence_case_ids: [...]}.
A 'pattern' requires at least 2 cases referencing the same underlying issue
in different ways (e.g. two cases categorized differently but both about
a manager-fit problem)."

If has_pattern=true: fire(severity='medium', theme=<theme>)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| SFDC `Case` where `AccountId=Customer` | `Id`, `CaseNumber`, `Categories__c`, `Description`, `Details__c`, `CreatedDate`, `Status` | last 60 days |
| Graphiti `escalated_via` edges from Case → Customer | source case, severity | last 60 days |

## Triggering threshold

- **Category-pattern rule fires** when ≥2 cases share a category in 60 days.
  - 2 cases same-category → `low` to `medium` (based on category — `Risk - Customer Payment Failure` always `medium+`)
  - 3+ cases same-category → `high`
- **LLM-clustering rule fires** when the rule layer didn't catch a category pattern but the LLM identifies a thematic pattern across ≥2 cases.
- **Composite escalation:** if both rules fire, severity is `high`.

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | Standard ladder. |
| **Mid-Market** | Standard. |
| **Enterprise** | Severity floor raised by one (any pattern → `medium`+); cc VP-CS always at `medium+`. |

## False-positive failure modes

- **Routine high-volume customer.** Some Enterprise customers naturally generate more cases due to volume of placements. 5 cases in 60 days might be normal for them. Mitigation: per-customer baseline tracking deferred to v1.5+ (Layer 8 Mechanism 2). Phase 1 default fires on absolute thresholds.
- **Resolved cases.** Cases already closed and resolved successfully are technically a pattern but not necessarily concerning. Mitigation: rule should weight unresolved (`Status != 'Closed'`) more heavily; closed-and-resolved cases bump severity less. Phase 1 default treats both equally; tuning candidate.

## False-negative failure modes

- **One serious case carrying pattern-level weight.** A single severe case may matter more than three minor ones. Captured by other signals (`escalation_signal_severity_jump_v1`), not this one.
- **Cases at different Talent within same Customer.** If 2 Cases at the same customer are about different Talent with different root causes, the LLM clustering should *not* find a pattern — but this is the LLM's job to discriminate. Risk surface for prompt-tuning.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| `min_cases_for_pattern` | int | 2 | Admin | Higher = fewer fires |
| Lookback window | int days | 60 | Admin | |
| Category-severity-floor map | dict | per category | Admin | Per-category sensitivity (e.g. `Customer Payment Failure` always medium+) |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (root cause documented in next RM_Outreach): _TBD_
- Outcome (Cases of same category cease within 30d of action): _TBD_  ← success case
- Last tuned: never

## Examples

### Example 1 — Acrisure
- **Evidence:** 3 Cases at Acrisure in last 60 days: 2 tagged `Risk - Talent Competency` (about different talent's audit failures), 1 tagged `Performance`. LLM clustering: theme = "dental audit competency", evidence_case_ids=[C-19284, C-19310, C-19401].
- **Signal fires at:** `high` (3 same-category-or-thematic).
- **Action proposed:** Skill 05 routes to Talent Dev + cc VP-CS (Mid-Market threshold); Skill 10 cross-references for cohort patterns.

### Example 2 — Helix Labs (Enterprise)
- **Evidence:** 2 Cases in last 60 days: 1 `Risk - Resignation`, 1 `Risk - Talent Professionalism`. Different categories. LLM clustering: `has_pattern=False`.
- **Signal fires at:** No fire from category rule (only 1 per category); LLM clustering returned no pattern. **Signal does not fire.** (Skill 05 still fires on each individual Case via `escalation_signal_severity_jump_v1` or direct case-trigger.)

## Open questions

- **Q138:** Per-customer baseline learning. Some customers run case-heavy; the pattern rule needs context. v1.5+ candidate.
- **Q139:** Category-severity-floor defaults. Some categories are intrinsically severe (`Risk - Customer Payment Failure`); should they fire `high` on a single occurrence even without pattern? PM proposes: separate signal (`escalation_signal_severity_jump_v1`) handles single-severe cases; this signal focuses on pattern.

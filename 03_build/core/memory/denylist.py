"""
SPEC-007 — protected-class theme denylist (defense in depth).

The cross-account pattern retriever must never aggregate signals along a
protected-class dimension. Skill 10 is responsible for never *requesting* such a
theme, but the retriever also refuses one as a second line of defense
(find_pattern_across_customers raises ValueError on a match).

Matching is case-insensitive substring containment so close variants ("racial",
"religious") are caught. This is intentionally broad; false positives are safer
than a discrimination-shaped aggregation reaching a user.
"""

from __future__ import annotations

# Substrings that, if present in a requested theme, are refused.
PROTECTED_CLASS_TERMS: frozenset[str] = frozenset(
    {
        "race",
        "racial",
        "ethnic",
        "national origin",
        "color",
        "religion",
        "religious",
        "creed",
        "sex",
        "gender",
        "sexual orientation",
        "lgbt",
        "transgender",
        "pregnan",  # pregnant / pregnancy
        "age",
        "disab",  # disabled / disability
        "marital",
        "veteran",
        "genetic",
        "immigrant",
        "citizenship",
    }
)


def is_protected_theme(theme: str) -> bool:
    """True if the theme contains a protected-class term (case-insensitive)."""
    t = theme.casefold()
    return any(term in t for term in PROTECTED_CLASS_TERMS)


def assert_theme_allowed(theme: str) -> None:
    """Raise ValueError if `theme` names a protected class."""
    if is_protected_theme(theme):
        raise ValueError(
            f"refusing cross-account aggregation on a protected-class theme: {theme!r} "
            "(SPEC-007 denylist / §6 anti-discrimination guardrail)"
        )

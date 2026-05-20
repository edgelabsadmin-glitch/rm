"""
SPEC-009 — policy I/O types (Design 04 §"Policy module").

These are written with OPA-shape inputs/outputs so the Phase-1 Python rules
migrate mechanically to OPA `.rego` in v1.5+ (Q44). `ActionSuggested` here is the
policy-layer view of an action proposal (carries the routing-relevant fields);
it is distinct from the event-log payload model in core.events.types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Decision = Literal["auto-approve", "require-human", "block"]


@dataclass
class ActionSuggested:
    """The policy input: an action a skill wants to take."""

    skill_id: str
    urgency: str  # "low" | "medium" | "high" | ...
    action_id: str | None = None
    customer_id: str | None = None
    tier_class: str | None = None  # "SMB" | "Mid" | "Enterprise" | None
    action_card: dict = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """The policy output: where the action routes, and why (for audit)."""

    decision: Decision
    reason: str
    thresholds_applied: dict = field(default_factory=dict)
    delay_seconds: int = 0  # auto-approve rules dispatch after a delay (+1h)

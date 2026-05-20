"""
SPEC-008 — Event Log types: the Phase-1 event-type enum + per-type payload
schemas (Design 04 §"Event types"). The emitter validates each event's `payload`
JSONB against the model registered here, so a malformed payload raises at *emit*
time, not at read time (Design 04 / §6 rule 14 — no silent failure).

Design 04 enumerates 20 event types across six lifecycle stages. The two written
by other specs (policy-decision → spec 009, kill-switch-flipped → spec 010) have
their payload schemas defined here so the log can record them coherently.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict

# ── The Phase-1 event-type enum (Design 04 §"Event types") ───────────────────
EventType = Literal[
    # Signal / ingestion (Design 02 pipeline)
    "signal-received",
    "signal-rejected",
    "signal-normalized",
    "episode-ingested",
    "episode-deduped",
    "ingestion-failed",
    # Agent reasoning (Design 05 skill runtime)
    "skill-fired",
    "context-retrieved",
    "reasoning-completed",
    "action-suggested",
    # Approval (Design 03 Action Queue)
    "action-approved",
    "action-modified-and-approved",
    "action-rejected",
    "action-expired",
    # Dispatch
    "action-executed",
    "dispatch-failed",
    # Outcome
    "outcome-recorded",
    "outcome-missing",
    # Policy / kill switch (specs 009 / 010)
    "policy-decision",
    "kill-switch-flipped",
]

EVENT_TYPES: tuple[str, ...] = get_args(EventType)


class _Payload(BaseModel):
    """Base payload: strict (unknown keys raise) so typos fail at emit time."""

    model_config = ConfigDict(extra="forbid")


# ── Signal / ingestion ───────────────────────────────────────────────────────
class SignalReceived(_Payload):
    source: str
    source_event_id: str
    headers_hash: str | None = None


class SignalRejected(_Payload):
    source: str
    reason: str  # "bad-signature" | "rate-limit" | "duplicate-dedup-key"


class SignalNormalized(_Payload):
    episode_id: str
    dedup_key: str
    content_size: int


class EpisodeIngested(_Payload):
    episode_id: str
    entity_extractions: list[str] = []
    edge_extractions: list[str] = []
    extraction_model: str
    latency_ms: int


class EpisodeDeduped(_Payload):
    episode_id: str
    duplicate_of: str


class IngestionFailed(_Payload):
    stage: str
    error_class: str
    error_message_summary: str


# ── Agent reasoning ──────────────────────────────────────────────────────────
class SkillFired(_Payload):
    skill_id: str
    trigger_event_id: str | None = None
    context_bundle_summary: str | None = None


class ContextRetrieved(_Payload):
    retrievers_called: list[str] = []
    entity_count: int
    episode_count: int
    retrieval_latency_ms: int


class ReasoningCompleted(_Payload):
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    reasoning_summary: str | None = None


class ActionSuggested(_Payload):
    action_card: dict
    why_oneline: str
    why_detail: str | None = None
    urgency: str
    source_episodes: list[str] = []


# ── Approval ─────────────────────────────────────────────────────────────────
class ActionApproved(_Payload):
    action_id: str
    approver_id: str
    decision_latency_ms: int | None = None


class ActionModifiedAndApproved(_Payload):
    action_id: str
    approver_id: str
    diff: dict
    decision_latency_ms: int | None = None


class ActionRejected(_Payload):
    action_id: str
    approver_id: str
    reason_picker: str
    free_text: str | None = None


class ActionExpired(_Payload):
    action_id: str
    expired_after_seconds: int


# ── Dispatch ─────────────────────────────────────────────────────────────────
class ActionExecuted(_Payload):
    action_id: str
    handler: str
    external_id: str | None = None
    dispatch_latency_ms: int | None = None


class DispatchFailed(_Payload):
    action_id: str
    handler: str
    error_class: str
    retry_attempt: int


# ── Outcome ──────────────────────────────────────────────────────────────────
class OutcomeRecorded(_Payload):
    action_id: str
    outcome_type: str
    evidence_episode_id: str | None = None


class OutcomeMissing(_Payload):
    action_id: str
    outcome_window_closed_at: str
    expected_outcome_type: str


# ── Policy / kill switch ─────────────────────────────────────────────────────
class PolicyDecision(_Payload):
    action_id: str
    decision: str  # "auto-approve" | "require-human" | "block"
    thresholds_applied: dict = {}


class KillSwitchFlipped(_Payload):
    user_id: str
    scope: str  # "global" | "skill:X" | "customer:X"
    on_or_off: bool


# event_type -> payload model. The emitter looks the model up here to validate.
PAYLOAD_MODELS: dict[str, type[_Payload]] = {
    "signal-received": SignalReceived,
    "signal-rejected": SignalRejected,
    "signal-normalized": SignalNormalized,
    "episode-ingested": EpisodeIngested,
    "episode-deduped": EpisodeDeduped,
    "ingestion-failed": IngestionFailed,
    "skill-fired": SkillFired,
    "context-retrieved": ContextRetrieved,
    "reasoning-completed": ReasoningCompleted,
    "action-suggested": ActionSuggested,
    "action-approved": ActionApproved,
    "action-modified-and-approved": ActionModifiedAndApproved,
    "action-rejected": ActionRejected,
    "action-expired": ActionExpired,
    "action-executed": ActionExecuted,
    "dispatch-failed": DispatchFailed,
    "outcome-recorded": OutcomeRecorded,
    "outcome-missing": OutcomeMissing,
    "policy-decision": PolicyDecision,
    "kill-switch-flipped": KillSwitchFlipped,
}

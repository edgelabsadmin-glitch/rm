"""
SPEC-009/010 unit tests — pure policy logic, kill-switch helpers, admin 403.

No DB: these exercise _evaluate (every rule + cascade precedence), the
kill-switch pure helpers, and the admin-auth 403 path. The end-to-end tests
(policy_decide emits an event, toggle blocks, admin round-trip) live in
tests/test_policy_db.py (marker `db`).
"""

import pytest

from core.policy import kill_switch
from core.policy.decide import AUTO_APPROVE_DELAY_SECONDS, _evaluate
from core.policy.types import ActionSuggested

AUTO_APPROVE = ["recognition", "talent-care", "onboarding"]


def _decide(skill="renewal-watcher", urgency="medium", tier=None, *, kill=None, rejections=0):
    return _evaluate(
        ActionSuggested(skill_id=skill, urgency=urgency, tier_class=tier),
        kill_scope=kill,
        rejections=rejections,
        auto_approve_skills=AUTO_APPROVE,
    )


# ── the 7 rules ──────────────────────────────────────────────────────────────
def test_rule1_kill_switch_blocks():
    d = _decide(kill="global")
    assert d.decision == "block" and "global" in d.reason


def test_rule2_rejection_dampening_requires_human():
    d = _decide(rejections=3)
    assert d.decision == "require-human" and d.reason == "skill_rejection_dampening"
    assert d.thresholds_applied["flag_for_tuning"] is True


def test_rule3_enterprise_requires_human():
    assert _decide(tier="Enterprise").decision == "require-human"


def test_rule4_high_urgency_requires_human():
    assert _decide(urgency="high", tier="SMB").decision == "require-human"


def test_rule5_recognition_auto_approves_with_delay():
    d = _decide(skill="recognition", tier="Mid")
    assert d.decision == "auto-approve"
    assert d.delay_seconds == AUTO_APPROVE_DELAY_SECONDS


def test_rule6_smb_auto_approve_list():
    d = _decide(skill="onboarding", tier="SMB")
    assert d.decision == "auto-approve" and d.reason == "smb_auto_approve_list"


def test_rule7_default_requires_human():
    assert _decide(skill="renewal-watcher", tier="Mid").decision == "require-human"


# ── cascade precedence (block > require-human > auto-approve) ─────────────────
def test_kill_switch_beats_everything():
    # Even a recognition SMB action is blocked when the switch is on.
    assert _decide(skill="recognition", tier="SMB", kill="skill:recognition").decision == "block"


def test_enterprise_recognition_still_requires_human():
    # "recognition auto-approves across tiers" yields to Enterprise require-human.
    assert _decide(skill="recognition", tier="Enterprise").decision == "require-human"


def test_rejection_dampening_beats_recognition_auto_approve():
    assert _decide(skill="recognition", tier="SMB", rejections=5).decision == "require-human"


def test_high_urgency_beats_smb_auto_approve():
    assert _decide(skill="onboarding", tier="SMB", urgency="high").decision == "require-human"


# ── kill-switch pure helpers ─────────────────────────────────────────────────
def test_blocked_detects_each_scope():
    state = {"global": False, "by_skill": {"renewal-watcher": True}, "by_customer": {"001": True}}
    assert kill_switch._blocked(state, None, None) is None
    assert kill_switch._blocked(state, "renewal-watcher", None) == "skill:renewal-watcher"
    assert kill_switch._blocked(state, "x", "001") == "customer:001"
    assert kill_switch._blocked({"global": True}, "x", "y") == "global"


def test_apply_sets_each_scope():
    base = {"global": False, "by_skill": {}, "by_customer": {}}
    assert kill_switch._apply(base, "global", True)["global"] is True
    assert kill_switch._apply(base, "skill:renewal-watcher", True)["by_skill"]["renewal-watcher"]
    assert kill_switch._apply(base, "customer:001", True)["by_customer"]["001"]
    with pytest.raises(ValueError, match="unknown kill-switch scope"):
        kill_switch._apply(base, "bogus", True)


# ── admin auth (403, no DB) ──────────────────────────────────────────────────
async def test_admin_kill_switch_requires_token(monkeypatch):
    monkeypatch.delenv("PULSE_INTERNAL_API_TOKEN", raising=False)
    from fastapi import HTTPException
    from api.admin.kill_switch import require_admin

    with pytest.raises(HTTPException) as exc:
        await require_admin(x_admin_token=None)
    assert exc.value.status_code == 403

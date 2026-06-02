"""SPEC-031 unit tests — pure ranking + scope logic (no DB)."""

from datetime import datetime, timedelta, timezone
UTC = timezone.utc

from api.actions import Caller
from core.actions.queue import _status_from_history, ranking_score


def test_urgency_dominates_ranking():
    now = datetime(2026, 5, 20, tzinfo=UTC)
    high = ranking_score("high", "SMB", now, now)
    low = ranking_score("low", "Enterprise", now, now)
    assert high > low  # urgency weight (100) dominates tier bonus (20)


def test_tier_bonus_breaks_ties_within_urgency():
    now = datetime(2026, 5, 20, tzinfo=UTC)
    ent = ranking_score("medium", "Enterprise", now, now)
    smb = ranking_score("medium", "SMB", now, now)
    assert ent > smb


def test_recency_bonus_favors_newer():
    now = datetime(2026, 5, 20, tzinfo=UTC)
    fresh = ranking_score("medium", "SMB", now, now)
    stale = ranking_score("medium", "SMB", now - timedelta(hours=72), now)
    assert fresh > stale


def test_unknown_urgency_defaults_to_medium():
    now = datetime(2026, 5, 20, tzinfo=UTC)
    assert ranking_score("bogus", None, now, now) == ranking_score("medium", None, now, now)


def test_status_folds_to_latest_terminal():
    hist = [
        {"event_type": "action-suggested"},
        {"event_type": "action-approved"},
        {"event_type": "action-executed"},
    ]
    assert _status_from_history(hist) == "dispatched"
    assert _status_from_history([{"event_type": "action-suggested"}]) == "pending"
    assert (
        _status_from_history(
            [{"event_type": "action-suggested"}, {"event_type": "action-rejected"}]
        )
        == "rejected"
    )


def test_caller_scope_rm_sees_only_self():
    rm = Caller("rmA", "rm", [])
    assert rm.visible_rm_ids() == ["rmA"]
    assert rm.can_act_on("rmA") is True
    assert rm.can_act_on("rmB") is False


def test_caller_scope_manager_sees_reports():
    mgr = Caller("mgr1", "manager", ["rmA", "rmB"])
    assert set(mgr.visible_rm_ids() or []) == {"mgr1", "rmA", "rmB"}
    assert mgr.can_act_on("rmA") is True
    assert mgr.can_act_on("rmZ") is False


def test_caller_scope_admin_sees_all():
    admin = Caller("boss", "admin", [])
    assert admin.visible_rm_ids() is None
    assert admin.can_act_on("anyone") is True
    assert admin.can_act_on(None) is True

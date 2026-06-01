"""SPEC-033 unit tests — outcome plan (type + window) logic (no DB)."""

from datetime import datetime, timedelta, timezone
UTC = timezone.utc

from core.outcomes.watchers import WINDOW_DAYS, plan_for


def test_email_action_gets_7day_window():
    d = datetime(2026, 5, 1, tzinfo=UTC)
    plan = plan_for("renewal-touch", d)
    assert plan.watched and plan.expected_outcome_type == "email-reply"
    assert plan.window_close_at == d + timedelta(days=7)


def test_task_action_gets_14day_window():
    d = datetime(2026, 5, 1, tzinfo=UTC)
    plan = plan_for("escalation-routed", d)
    assert plan.expected_outcome_type == "task-completed"
    assert plan.window_close_at == d + timedelta(days=WINDOW_DAYS["task-completed"])


def test_ebr_window_aligns_to_meeting_date():
    d = datetime(2026, 5, 1, tzinfo=UTC)
    meeting = datetime(2026, 5, 10, tzinfo=UTC)
    plan = plan_for("meeting-brief", d, meeting_date=meeting)
    assert plan.expected_outcome_type == "ebr-detected"
    assert plan.window_close_at == meeting + timedelta(days=1)


def test_ebr_without_meeting_date_falls_back_to_14d():
    d = datetime(2026, 5, 1, tzinfo=UTC)
    plan = plan_for("meeting-brief", d)
    assert plan.expected_outcome_type == "ebr-detected"
    assert plan.window_close_at == d + timedelta(days=14)


def test_unwatched_action_type_is_not_watched():
    d = datetime(2026, 5, 1, tzinfo=UTC)
    plan = plan_for("brand-new-thing", d)
    assert plan.watched is False
    assert plan.expected_outcome_type is None

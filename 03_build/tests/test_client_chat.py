"""Unit tests for client chat helpers — no DB, no network."""
from __future__ import annotations


def test_truncate_title_from_otp_module():
    from core.client.otp import truncate_title
    long_text = "Hello, I have a question about my staffing needs"
    assert truncate_title(long_text) == long_text


def test_truncate_title_caps_at_60():
    from core.client.otp import truncate_title
    long = "x" * 100
    assert truncate_title(long) == "x" * 60


def test_format_context_no_episodes():
    from api.client_chat import _format_context
    result = _format_context([], [])
    assert "No recent emails" in result
    assert "No recent meetings" in result


def test_format_context_with_episodes():
    from api.client_chat import _format_context
    emails = [{"subject": "Follow up", "description": "Hope you are well"}]
    meetings = [{"subject": "Quarterly Review", "description": "Discussed placements"}]
    result = _format_context(emails, meetings)
    assert "Follow up" in result
    assert "Quarterly Review" in result

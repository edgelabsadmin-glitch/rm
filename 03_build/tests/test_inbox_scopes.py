"""Inbox feature requires the gmail.send scope in the Google OAuth grant."""

from api.auth_google import _SCOPES


def test_gmail_send_scope_present():
    assert "https://www.googleapis.com/auth/gmail.send" in _SCOPES


def test_readonly_scope_still_present():
    # Send is additive; reading must keep working.
    assert "https://www.googleapis.com/auth/gmail.readonly" in _SCOPES

"""Pure helpers over Gmail message payloads — no network."""

import base64

from core.inbox.threads import extract_plain_body, latest_inbound_message


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_extract_plain_body_simple():
    payload = {"mimeType": "text/plain", "body": {"data": _b64("Hello there")}}
    assert extract_plain_body(payload) == "Hello there"


def test_extract_plain_body_multipart_prefers_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>HTML</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("Plain wins")}},
        ],
    }
    assert extract_plain_body(payload) == "Plain wins"


def test_extract_plain_body_nested_multipart():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Nested plain")}},
                ],
            }
        ],
    }
    assert extract_plain_body(payload) == "Nested plain"


def test_extract_plain_body_missing_returns_empty():
    assert extract_plain_body({"mimeType": "text/html", "body": {}}) == ""


def test_latest_inbound_message_returns_latest_when_client_last():
    msgs = [
        {"id": "m1", "from_email": "client@acme.com", "internal_date": 100},
        {"id": "m2", "from_email": "rm@onedge.co", "internal_date": 200},
        {"id": "m3", "from_email": "client@acme.com", "internal_date": 300},
    ]
    out = latest_inbound_message(msgs, "rm@onedge.co")
    assert out is not None
    assert out["id"] == "m3"


def test_latest_inbound_message_none_when_rm_replied_last():
    msgs = [
        {"id": "m1", "from_email": "client@acme.com", "internal_date": 100},
        {"id": "m2", "from_email": "rm@onedge.co", "internal_date": 200},
    ]
    assert latest_inbound_message(msgs, "rm@onedge.co") is None


def test_latest_inbound_message_case_insensitive_rm_match():
    msgs = [
        {"id": "m1", "from_email": "RM@OnEdge.co", "internal_date": 200},
        {"id": "m0", "from_email": "client@acme.com", "internal_date": 100},
    ]
    assert latest_inbound_message(msgs, "rm@onedge.co") is None

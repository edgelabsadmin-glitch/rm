"""Pure MIME construction for a threaded Gmail reply."""

import base64
from email.message import Message

from core.inbox.send import build_reply_raw


def _decode_raw(raw: str) -> Message:
    from email import message_from_bytes

    padded = raw + "=" * (-len(raw) % 4)
    return message_from_bytes(base64.urlsafe_b64decode(padded))


def test_build_reply_raw_sets_recipients_and_subject():
    raw = build_reply_raw(
        to_email="client@acme.com",
        from_email="rm@onedge.co",
        subject="Re: Renewal",
        body="Happy to help.",
        in_reply_to="<abc@mail.gmail.com>",
    )
    msg = _decode_raw(raw)
    assert msg["To"] == "client@acme.com"
    assert msg["From"] == "rm@onedge.co"
    assert msg["Subject"] == "Re: Renewal"
    assert "Happy to help." in msg.get_payload()


def test_build_reply_raw_adds_threading_headers():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: x",
        body="b", in_reply_to="<abc@mail.gmail.com>",
    )
    msg = _decode_raw(raw)
    assert msg["In-Reply-To"] == "<abc@mail.gmail.com>"
    assert msg["References"] == "<abc@mail.gmail.com>"


def test_build_reply_raw_prefixes_re_once():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Renewal",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["Subject"] == "Re: Renewal"


def test_build_reply_raw_keeps_existing_re():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: Renewal",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["Subject"] == "Re: Renewal"


def test_build_reply_raw_omits_threading_when_no_message_id():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: x",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["In-Reply-To"] is None
    assert msg["References"] is None

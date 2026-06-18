"""Reply prompt construction + draft parsing — Claude is mocked."""

import json

from core.inbox import reply as reply_mod
from core.inbox.reply import build_reply_prompt, parse_reply_response


def test_prompt_includes_style_account_and_body():
    p = build_reply_prompt(
        style_prompt="Warm and concise.",
        account_name="Acme Health",
        from_name="Jane Client",
        subject="Renewal timing",
        body="When does our contract renew?",
    )
    assert "Warm and concise." in p
    assert "Acme Health" in p
    assert "Jane Client" in p
    assert "When does our contract renew?" in p


def test_prompt_tone_formal_adds_instruction():
    p = build_reply_prompt(
        style_prompt="x",
        account_name="A",
        from_name="B",
        subject="s",
        body="b",
        tone="formal",
    )
    assert "formal" in p.lower()


def test_prompt_tone_shorter_and_warmer():
    assert (
        "short"
        in build_reply_prompt(
            style_prompt="x", account_name="A", from_name="B", subject="s", body="b", tone="shorter"
        ).lower()
    )
    assert (
        "warm"
        in build_reply_prompt(
            style_prompt="x", account_name="A", from_name="B", subject="s", body="b", tone="warmer"
        ).lower()
    )


def test_parse_reply_response_valid_json():
    raw = json.dumps({"reply": "Hi Jane,\n\nHappy to help.", "rationale": "Confirms renewal date."})
    out = parse_reply_response(raw)
    assert out["reply"].startswith("Hi Jane,")
    assert out["rationale"] == "Confirms renewal date."


def test_parse_reply_response_json_in_codefence():
    raw = "```json\n" + json.dumps({"reply": "R", "rationale": "X"}) + "\n```"
    out = parse_reply_response(raw)
    assert out["reply"] == "R"
    assert out["rationale"] == "X"


def test_parse_reply_response_falls_back_to_plain_text():
    out = parse_reply_response("just a plain reply, no json")
    assert out["reply"] == "just a plain reply, no json"
    assert out["rationale"] == ""


async def test_generate_reply_uses_mocked_claude(monkeypatch):
    captured = {}

    def fake_call(prompt: str) -> str:
        captured["prompt"] = prompt
        return json.dumps({"reply": "Drafted reply", "rationale": "Because reasons."})

    monkeypatch.setattr(reply_mod, "_call_claude", fake_call)

    out = await reply_mod.generate_reply(
        style_prompt="Warm.",
        account_name="Acme",
        from_name="Jane",
        subject="Hi",
        body="Question?",
    )
    assert out == {"reply": "Drafted reply", "rationale": "Because reasons."}
    assert "Acme" in captured["prompt"]

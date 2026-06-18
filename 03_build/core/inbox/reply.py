"""
Draft a reply to a client email in the RM's voice.

build_reply_prompt assembles the prompt (pure). generate_reply runs Claude
(off-thread) and returns {"reply", "rationale"}. parse_reply_response is the
tolerant JSON parser used to read the model's structured output.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from core.llm.config import ANTHROPIC_SONNET, load_env

log = logging.getLogger(__name__)

_TONE_INSTRUCTIONS = {
    "formal": "Make the reply more formal and polished.",
    "shorter": "Make the reply noticeably shorter and more to the point.",
    "warmer": "Make the reply warmer and more personable.",
}


def build_reply_prompt(
    *,
    style_prompt: str,
    account_name: str,
    from_name: str,
    subject: str,
    body: str,
    tone: str | None = None,
) -> str:
    """Build the LLM prompt for drafting a reply in the RM's voice."""
    tone_line = ""
    if tone and tone in _TONE_INSTRUCTIONS:
        tone_line = f"\nADJUSTMENT: {_TONE_INSTRUCTIONS[tone]}\n"

    return (
        "You are a Relationship Manager at EDGE Solutions, a healthcare staffing company, "
        "drafting a reply to an email from your client.\n\n"
        f"YOUR WRITING STYLE (impersonate this exactly):\n{style_prompt}\n\n"
        f"CLIENT ACCOUNT: {account_name}\n"
        f"FROM: {from_name}\n"
        f"SUBJECT: {subject}\n\n"
        f"THE EMAIL YOU ARE REPLYING TO:\n{body}\n"
        f"{tone_line}\n"
        "Write a complete, ready-to-send reply email body (no subject line, no placeholders "
        "like [Name] — use the real names). Then give a one-sentence rationale explaining what "
        "the reply does.\n\n"
        'Respond ONLY with a JSON object: {"reply": "<the email body>", '
        '"rationale": "<one sentence>"}'
    )


def parse_reply_response(raw: str) -> dict:
    """Parse the model output into {"reply", "rationale"}; tolerant of code fences.

    Falls back to treating the whole text as the reply with an empty rationale.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    try:
        obj = json.loads(candidate)
        return {
            "reply": str(obj.get("reply", "")).strip(),
            "rationale": str(obj.get("rationale", "")).strip(),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"reply": text, "rationale": ""}


def _call_claude(prompt: str) -> str:
    load_env()
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model=ANTHROPIC_SONNET,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    block = response.content[0]
    return block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]


async def generate_reply(
    *,
    style_prompt: str,
    account_name: str,
    from_name: str,
    subject: str,
    body: str,
    tone: str | None = None,
) -> dict:
    """Draft a reply; returns {"reply", "rationale"}. Empty reply on failure."""
    prompt = build_reply_prompt(
        style_prompt=style_prompt,
        account_name=account_name,
        from_name=from_name,
        subject=subject,
        body=body,
        tone=tone,
    )
    try:
        raw = await asyncio.to_thread(_call_claude, prompt)
    except Exception as exc:
        log.error("inbox reply generation failed: %s", exc)
        return {"reply": "", "rationale": ""}
    return parse_reply_response(raw)

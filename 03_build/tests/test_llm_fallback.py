"""Opus-primary → Sonnet-fallback wrapper (pure, no network)."""

import pytest

from core.llm.config import ANTHROPIC_OPUS, ANTHROPIC_SONNET
from core.llm.fallback import acall_with_fallback, call_with_fallback


def test_primary_success_calls_once():
    calls = []

    def fn(model):
        calls.append(model)
        return f"ok:{model}"

    out = call_with_fallback(fn)
    assert out == f"ok:{ANTHROPIC_OPUS}" and calls == [ANTHROPIC_OPUS]


def test_primary_fails_falls_back_to_sonnet():
    calls = []

    def fn(model):
        calls.append(model)
        if model == ANTHROPIC_OPUS:
            raise RuntimeError("opus boom")
        return f"ok:{model}"

    out = call_with_fallback(fn)
    assert out == f"ok:{ANTHROPIC_SONNET}"
    assert calls == [ANTHROPIC_OPUS, ANTHROPIC_SONNET]  # primary first, then fallback


def test_both_fail_reraises():
    def fn(model):
        raise RuntimeError(f"boom:{model}")

    with pytest.raises(RuntimeError, match=f"boom:{ANTHROPIC_SONNET}"):
        call_with_fallback(fn)


async def test_async_falls_back():
    calls = []

    async def fn(model):
        calls.append(model)
        if model == ANTHROPIC_OPUS:
            raise RuntimeError("opus boom")
        return f"ok:{model}"

    out = await acall_with_fallback(fn)
    assert out == f"ok:{ANTHROPIC_SONNET}" and calls == [ANTHROPIC_OPUS, ANTHROPIC_SONNET]

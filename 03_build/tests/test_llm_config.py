"""
SPEC-003 — model-ID pinning tests + the `-latest` meta-test (Q115).
"""

import re
from pathlib import Path

import pytest

from core.llm import config

_BUILD_ROOT = Path(__file__).resolve().parents[1]


def test_pinned_model_ids_are_dated():
    # No `-latest` aliases among the pinned constants (Q115).
    for const in (config.ANTHROPIC_HAIKU, config.ANTHROPIC_SONNET, config.ANTHROPIC_OPUS):
        assert not const.endswith("-latest"), f"{const} is a -latest alias"


def test_make_llm_config_rejects_latest_alias():
    with pytest.raises(ValueError):
        config.make_llm_config("claude-haiku-4-5-latest")


def test_timeout_budgets_present():
    assert config.timeout_for(config.ANTHROPIC_HAIKU) == 15
    assert config.timeout_for(config.ANTHROPIC_OPUS) == 45


# Files that legitimately contain the guard logic / explanatory text and are
# therefore exempt from the grep meta-tests below: config.py (the guard itself,
# which contains the canonical `endswith("-latest")` check + the documented
# `load_dotenv(..., override=True)` call) and this test file.
_META_EXEMPT = {"test_llm_config.py", "config.py"}


def test_no_latest_aliases_anywhere_in_codebase():
    """Q115 meta-test: no `claude-*-latest` literals in application code.

    Grep-based guard. If a future spec hardcodes a -latest alias, CI fails here.
    """
    pattern = re.compile(r"claude-[a-z0-9.\-]*-latest")
    offenders: list[str] = []
    for path in _BUILD_ROOT.rglob("*.py"):
        if ".venv" in path.parts or path.name in _META_EXEMPT:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(str(path.relative_to(_BUILD_ROOT)))
    assert not offenders, f"`-latest` alias found in: {offenders}"


def test_load_dotenv_uses_override_everywhere():
    """Q116 meta-test: every load_dotenv() call passes override=True.

    Bare load_dotenv() lets empty parent-shell vars win over .env (Spike 3 bug).
    """
    offenders: list[str] = []
    call_re = re.compile(r"load_dotenv\s*\(([^)]*)\)")
    for path in _BUILD_ROOT.rglob("*.py"):
        if ".venv" in path.parts or path.name in _META_EXEMPT:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in call_re.finditer(text):
            if "override=True" not in m.group(1):
                offenders.append(f"{path.relative_to(_BUILD_ROOT)}: load_dotenv({m.group(1)})")
    assert not offenders, f"load_dotenv without override=True: {offenders}"

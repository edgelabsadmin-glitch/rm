"""
SPEC-003 — Model-ID pinning module + env-loading discipline.

Resolves:
- Q115: Graphiti 0.29 defaults to `claude-haiku-4-5-latest`, which the Anthropic
  API does NOT resolve (404 observed in Spike 3 live run). Pin dated model IDs here;
  every Pulse code path imports from this module — no model-ID string literals scattered.
- Q116: `load_dotenv()` defaults to override=False, which lets an empty parent-shell
  env var win over the .env file (observed in Spike 3). Always override=True.

This module is the single source of truth for which models Pulse calls. Model rotation
(e.g. 4.6 → 4.7) is a one-line change here.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# ── Env loading discipline (Q116) ───────────────────────────────────────────
# The project-root .env lives two levels up from this file:
#   03_build/core/llm/config.py  ->  parents[3] == ai-rm/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_env() -> None:
    """Load the project-root .env with override=True (Q116).

    override=True is mandatory: empty parent-shell vars (e.g. an empty
    ANTHROPIC_API_KEY exported by a launcher) must not win over the .env file.
    Call this once at process startup (FastAPI lifespan, scripts' __main__).
    """
    load_dotenv(_PROJECT_ROOT / ".env", override=True)


# ── Pinned model IDs (Q115) ─────────────────────────────────────────────────
# Dated release IDs only. NEVER use `-latest` aliases — they 404 on the org's
# pinned API surface and make rotation invisible. A CI grep check enforces this.
ANTHROPIC_HAIKU = (
    "claude-haiku-4-5-20251001"  # bulk extraction (Skill 01, Graphiti entity extraction)
)
ANTHROPIC_SONNET = "claude-sonnet-4-6"  # per-action reasoning + narrative synthesis
ANTHROPIC_OPUS = "claude-opus-4-7"  # CEO View weekly composition; profile regeneration

# Embedder — Anthropic ships no public embedding model; OpenAI per Spike 3 §C.
OPENAI_EMBEDDER = "text-embedding-3-small"

# Per-model output-token + timeout budgets (ADR-001: per-LLM-call timeout).
_MODEL_DEFAULTS: dict[str, dict[str, int]] = {
    ANTHROPIC_HAIKU: {"max_tokens": 4096, "timeout_s": 15},
    ANTHROPIC_SONNET: {"max_tokens": 8192, "timeout_s": 30},
    ANTHROPIC_OPUS: {"max_tokens": 16384, "timeout_s": 45},
}


def make_llm_config(model: str, max_tokens: int | None = None):
    """Return a graphiti_core LLMConfig for the given pinned model.

    `model` must be one of the ANTHROPIC_* constants above. Passing a `-latest`
    alias or an unpinned string is a programming error.
    """
    if model.endswith("-latest"):
        raise ValueError(
            f"Refusing to build config for `-latest` alias {model!r}; "
            "use a dated model ID from core.llm.config (Q115)."
        )
    # Imported here so the module is importable without graphiti installed
    # (e.g. for the meta-test that greps for `-latest`).
    from graphiti_core.llm_client.config import LLMConfig

    defaults = _MODEL_DEFAULTS.get(model, {"max_tokens": 4096, "timeout_s": 30})
    return LLMConfig(model=model, max_tokens=max_tokens or defaults["max_tokens"])


def timeout_for(model: str) -> int:
    """Per-LLM-call timeout in seconds (ADR-001 Implementation Contract item 3)."""
    return _MODEL_DEFAULTS.get(model, {"timeout_s": 30})["timeout_s"]

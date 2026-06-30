"""
LLM analyst — turns an Evidence Pack into a structured signal matrix via Anthropic
tool-forced output (the model must call `emit_matrix`, so the result is schema-shaped
JSON, never free text). Sonnet is primary; the agent re-runs with Opus on validation
failure (model routing lives here; the fallback orchestration is in agent.py).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from core.llm.config import ANTHROPIC_OPUS, ANTHROPIC_SONNET, load_env

_MODELS = {"sonnet": ANTHROPIC_SONNET, "opus": ANTHROPIC_OPUS}

MATRIX_TOOL = {
    "name": "emit_matrix",
    "description": (
        "Emit the per-entity signal matrix. Fire a signal ONLY with cited evidence ids "
        "drawn from the EVIDENCE block; otherwise set fired=false."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "signals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "signal_id": {"type": "string"},
                        "fired": {"type": "boolean"},
                        "severity": {
                            "type": ["string", "null"],
                            "enum": ["low", "medium", "high", None],
                        },
                        "confidence": {"type": "number"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["signal_id", "fired", "confidence", "evidence"],
                },
            },
            "narrative": {"type": "string"},
        },
        "required": ["signals", "narrative"],
    },
}


def build_analyst_prompt(pack: Any, signal_defs: list[str]) -> str:
    """Render the analyst prompt from an Evidence Pack + the applicable signal defs."""
    if isinstance(pack, dict):
        tier = pack.get("tier")
        facts = pack.get("facts", {})
        snippets = pack.get("snippets", [])
        lines = [f"TIER: {tier}", "FACTS (cite via the bracketed id):"]
        for k, v in facts.items():
            if k == "evidence_ids" or isinstance(v, dict):
                continue
            if v is not None:
                lines.append(f"  [fact:{k}] {k} = {v}")
        if snippets:
            lines.append("SNIPPETS:")
            for s in snippets:
                lines.append(f"  [{s['id']}] ({s.get('source')} {s.get('date')}) {s.get('text')}")
        body = "\n".join(lines)
    else:
        body = str(pack)
    defs = "\n".join(f"- {d}" for d in signal_defs)
    return (
        "You are a relationship-intelligence analyst. Evaluate ONLY the signals listed "
        "against ONLY the evidence provided. Fire a signal ONLY if the evidence clearly "
        "supports it and cite the exact bracketed evidence id(s). If data is missing or "
        "ambiguous, do NOT fire (fired=false). Never invent facts or evidence ids.\n\n"
        f"SIGNALS:\n{defs}\n\nEVIDENCE:\n{body}\n\n"
        "Call emit_matrix with exactly one entry per signal."
    )


def _call_tool(model_id: str, prompt: str) -> dict:
    """Blocking Anthropic call forcing the emit_matrix tool; returns its input dict."""
    load_env()
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    resp = client.messages.create(
        model=model_id,
        max_tokens=2048,
        temperature=0,
        tools=[MATRIX_TOOL],
        tool_choice={"type": "tool", "name": "emit_matrix"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)  # type: ignore[arg-type]
    raise RuntimeError("analyst: model returned no tool_use block")


async def run_analyst(
    pack: Any, signal_defs: list[str], *, model: str = "sonnet"
) -> tuple[dict, str]:
    """Run the analyst with the named model; returns (raw_output, model_name)."""
    prompt = build_analyst_prompt(pack, signal_defs)
    out = await asyncio.to_thread(_call_tool, _MODELS.get(model, ANTHROPIC_SONNET), prompt)
    return out, model

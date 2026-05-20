"""
SPEC-017 — Signal Definition Library runtime.

Loads every `02_planning/signals/<signal_id>.md`, validates its structure
against the canonical template, imports the matching
`core/signals/<signal_id>.py` module, and asserts the markdown header and the
module's META agree on category / severity model / owning skills / detection
type. That lock-step is the §6-rule-8 guarantee: inspectable English ⇆
executable code, enforced (the loader and a CI meta-test both check it).

`evaluate(signal_id, ctx)` dispatches to the module and emits a
`signal-evaluated` event so the evaluation history is auditable (Layer 8).
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from langfuse import observe

from core.signals.base import (
    DetectionType,
    EvaluationContext,
    SeverityModel,
    SignalCategory,
    SignalMeta,
    SignalResult,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

SIGNALS_DIR = Path(__file__).resolve().parents[3] / "02_planning" / "signals"
CODE_DIR = Path(__file__).resolve().parent

_REQUIRED_SECTIONS = (
    "## Plain-English definition",
    "## Detection mechanism",
    "## Evidence shape",
    "## Triggering threshold",
    "## Tier-aware variants",
    "## Examples",
)

_CATEGORIES = ("churn", "expansion", "talent-care", "escalation", "recognition", "account-context")
_SEVERITIES = ("binary", "tiered", "scored")
_DETECTION = ("rule-based", "llm-based", "hybrid")

# Modules in core/signals/ that are NOT signal definitions.
_NON_SIGNAL_MODULES = {"__init__", "base", "runtime"}


@dataclass
class ParsedDefinition:
    signal_id: str
    category: SignalCategory
    severity_model: SeverityModel
    owning_skills: frozenset[int]
    detection_type: DetectionType
    status: str
    path: Path


@dataclass
class LoadedSignal:
    meta: SignalMeta
    evaluate: Callable[[EvaluationContext], Awaitable[SignalResult | None]]
    definition: ParsedDefinition


def _header_value(text: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", text, flags=re.M)
    if not m:
        raise ValueError(f"missing header '{label}'")
    return m.group(1).strip()


def _leading_token(value: str, allowed: tuple[str, ...], field: str) -> str:
    low = value.lower()
    for tok in allowed:
        if low.startswith(tok):
            return tok
    # not at the very start (e.g. "binary fire ..."): take first allowed token present
    for tok in allowed:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            return tok
    raise ValueError(f"could not parse {field} from {value!r}")


def parse_definition(path: Path) -> ParsedDefinition:
    text = path.read_text()
    for section in _REQUIRED_SECTIONS:
        if section not in text:
            raise ValueError(f"{path.name}: missing required section {section!r}")

    category = _leading_token(_header_value(text, "Category"), _CATEGORIES, "category")
    severity = _leading_token(_header_value(text, "Severity model"), _SEVERITIES, "severity")
    owning = frozenset(
        int(n) for n in re.findall(r"Skill\s+(\d+)", _header_value(text, "Owning skill(s)"))
    )
    # Detection type lives in the "Detection mechanism" section's **Type:** line.
    type_value = _header_value(text, "Type")
    detection = _leading_token(type_value, _DETECTION, "detection_type")
    status = _header_value(text, "Status").split()[0]

    return ParsedDefinition(
        signal_id=path.stem,
        category=category,  # type: ignore[arg-type]
        severity_model=severity,  # type: ignore[arg-type]
        owning_skills=owning,
        detection_type=detection,  # type: ignore[arg-type]
        status=status,
        path=path,
    )


def _assert_alignment(parsed: ParsedDefinition, meta: SignalMeta) -> None:
    mismatches = []
    if parsed.signal_id != meta.signal_id:
        mismatches.append(f"signal_id md={parsed.signal_id} py={meta.signal_id}")
    if parsed.category != meta.category:
        mismatches.append(f"category md={parsed.category} py={meta.category}")
    if parsed.severity_model != meta.severity_model:
        mismatches.append(f"severity md={parsed.severity_model} py={meta.severity_model}")
    if parsed.owning_skills != meta.owning_skills:
        mismatches.append(
            f"owning_skills md={set(parsed.owning_skills)} py={set(meta.owning_skills)}"
        )
    if parsed.detection_type != meta.detection_type:
        mismatches.append(f"detection md={parsed.detection_type} py={meta.detection_type}")
    if mismatches:
        raise ValueError(f"{parsed.signal_id}: markdown↔code misalignment: {'; '.join(mismatches)}")


def signal_ids_from_markdown() -> set[str]:
    return {p.stem for p in SIGNALS_DIR.glob("*.md")}


def signal_ids_from_code() -> set[str]:
    return {p.stem for p in CODE_DIR.glob("*.py") if p.stem not in _NON_SIGNAL_MODULES}


def check_correspondence() -> None:
    """Raise if any markdown lacks code or vice versa (CI meta-test uses this)."""
    md, code = signal_ids_from_markdown(), signal_ids_from_code()
    if md != code:
        raise ValueError(
            f"signal markdown↔code mismatch: "
            f"md-only={sorted(md - code)} code-only={sorted(code - md)}"
        )


def load_signal_library() -> dict[str, LoadedSignal]:
    """Load + validate all signal definitions. Raises on a missing/misaligned module."""
    check_correspondence()
    library: dict[str, LoadedSignal] = {}
    for md in sorted(SIGNALS_DIR.glob("*.md")):
        parsed = parse_definition(md)
        module = importlib.import_module(f"core.signals.{parsed.signal_id}")
        meta: SignalMeta = module.META
        if not callable(getattr(module, "evaluate", None)):
            raise ValueError(f"{parsed.signal_id}: module missing async evaluate()")
        _assert_alignment(parsed, meta)
        library[parsed.signal_id] = LoadedSignal(
            meta=meta, evaluate=module.evaluate, definition=parsed
        )
    return library


_LIBRARY: dict[str, LoadedSignal] | None = None


def get_library() -> dict[str, LoadedSignal]:
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = load_signal_library()
    return _LIBRARY


@observe(name="signal_evaluate")
async def evaluate(
    signal_id: str,
    context: EvaluationContext,
    *,
    library: dict[str, LoadedSignal] | None = None,
) -> SignalResult | None:
    """Evaluate one signal and emit a `signal-evaluated` event."""
    lib = library or get_library()
    loaded = lib.get(signal_id)
    if loaded is None:
        raise ValueError(f"unknown signal_id {signal_id!r}")

    result = await loaded.evaluate(context)

    from core.events import log

    await log.emit_signal_evaluated(
        signal_id=signal_id,
        fired=bool(result and result.fired),
        severity=(result.severity if result else None),
        evidence_count=(len(result.evidence) if result else 0),
        detection_type=loaded.meta.detection_type,
        customer_id=context.customer_id,
        talent_id=context.talent_id,
    )
    return result

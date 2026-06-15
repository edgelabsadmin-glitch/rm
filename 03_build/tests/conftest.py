"""
Shared pytest fixtures and module stubs.

graphiti_core and kuzu are not installed in the fast unit-test environment
(they require the full optional deps + embedded Kuzu store). Tests that need
to *import* modules that reference these libraries get a lightweight stub
so Python's import machinery doesn't raise ModuleNotFoundError.

Tests that actually exercise Graphiti behavior are marked `integration` or
`db` and are excluded from the default CI run (pyproject.toml addopts).
"""

from __future__ import annotations

import enum
import importlib.abc
import importlib.machinery
import sys
from unittest.mock import MagicMock


def _pkg_mock(name: str) -> MagicMock:
    """MagicMock that registers as a package (has __path__ + __package__)."""
    mock = MagicMock()
    mock.__path__ = []
    mock.__package__ = name
    mock.__name__ = name
    mock.__spec__ = None
    return mock


class _StubLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return _pkg_mock(spec.name)

    def exec_module(self, module):
        pass


class _StubFinder(importlib.abc.MetaPathFinder):
    """Auto-stub any import under graphiti_core.* or kuzu that isn't installed."""

    _STUBS = ("graphiti_core", "kuzu")

    def find_spec(self, fullname, path, target=None):
        if any(fullname == p or fullname.startswith(p + ".") for p in self._STUBS):
            if fullname not in sys.modules:
                return importlib.machinery.ModuleSpec(fullname, _StubLoader())
        return None


sys.meta_path.insert(0, _StubFinder())


# ── graphiti_core post-stub fixups ────────────────────────────────────────────
# After the finder is installed, import the stubs so we can inject the
# real EpisodeType enum before any production module uses it.

import graphiti_core.nodes as _gn  # noqa: E402 — after finder install


class _EpisodeType(enum.Enum):
    text = "text"
    json = "json"


_gn.EpisodeType = _EpisodeType  # type: ignore[attr-defined]

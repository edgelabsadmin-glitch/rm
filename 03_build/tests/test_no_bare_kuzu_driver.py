"""
SPEC-002 — guard: memory-layer code uses PulseKuzuDriver, never bare KuzuDriver.

Q114: the upstream KuzuDriver doesn't bootstrap FTS. Any code path that
instantiates `KuzuDriver(...)` directly (rather than PulseKuzuDriver) would
hit the missing-FTS-index error on first add_episode. This meta-test fails CI
if a future spec imports/instantiates the bare driver outside driver.py itself.
"""

import re
from pathlib import Path

_BUILD_ROOT = Path(__file__).resolve().parents[1]


def test_no_bare_kuzu_driver_instantiation():
    offenders: list[str] = []
    # Match `KuzuDriver(` not preceded by `Pulse`
    bad = re.compile(r"(?<!Pulse)KuzuDriver\s*\(")
    for path in _BUILD_ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        # driver.py legitimately subclasses KuzuDriver; this test file names it.
        if path.name in ("driver.py", "test_no_bare_kuzu_driver.py"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if bad.search(text):
            offenders.append(str(path.relative_to(_BUILD_ROOT)))
    assert not offenders, f"bare KuzuDriver() instantiation in: {offenders} (use PulseKuzuDriver)"

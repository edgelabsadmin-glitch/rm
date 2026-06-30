"""
Background loop: re-analyze active entities after data refreshes.

Runs `run_incremental` (changed-only, cheap) on an interval, plus a full
`run_backfill` pass once per day to catch anything the version check missed.
Enabled by default; set PULSE_ANALYSIS=0 to disable (CI/local opt-out). Errors
are isolated per cycle and logged; one failure never kills the loop.
"""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

# Incremental cadence (default 90 min); a full backfill runs every _FULL_EVERY cycles.
_INTERVAL_S = int(os.environ.get("PULSE_ANALYSIS_INTERVAL", str(90 * 60)))
_FULL_EVERY = max(1, int(os.environ.get("PULSE_ANALYSIS_FULL_EVERY", "16")))  # ~daily at 90m


async def analysis_loop() -> None:
    """Incremental every _INTERVAL_S; a full backfill every _FULL_EVERY cycles.

    Waits 300s at startup so the data syncs (SF, inbox, stage history) land first.
    On by default; set PULSE_ANALYSIS=0 to disable.
    """
    if os.environ.get("PULSE_ANALYSIS", "1") == "0":
        log.info("analysis loop disabled (PULSE_ANALYSIS=0)")
        return
    await asyncio.sleep(300)
    from core.analysis.agent import run_backfill, run_incremental

    cycle = 0
    while True:
        try:
            if cycle % _FULL_EVERY == 0:
                result = await run_backfill()
                log.info("analysis backfill: %s", result)
            else:
                result = await run_incremental()
                log.info("analysis incremental: %s", result)
        except Exception as exc:  # noqa: BLE001 — keep the loop alive across failures
            log.error("analysis loop error: %s", exc)
        cycle += 1
        await asyncio.sleep(_INTERVAL_S)

"""
Background loop: sync every connected RM's inbox on an interval.

Enabled only when PULSE_INBOX_SYNC=1 so CI/local can opt out. Errors are isolated
per-user and logged; one user's failure never aborts the round.
"""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

_INTERVAL_S = int(os.environ.get("PULSE_INBOX_SYNC_INTERVAL", "180"))


async def inbox_sync_loop() -> None:
    """Sync all connected RMs' inboxes every _INTERVAL_S seconds.

    Waits 200s at startup so SF contacts + google sessions are ready first.
    No-op unless PULSE_INBOX_SYNC=1.
    """
    if os.environ.get("PULSE_INBOX_SYNC") != "1":
        log.info("inbox sync loop disabled (set PULSE_INBOX_SYNC=1 to enable)")
        return
    await asyncio.sleep(200)
    from core.google.auth import list_connected_users
    from core.inbox.sync import sync_inbox

    while True:
        try:
            users = await list_connected_users()
            for u in users:
                try:
                    await sync_inbox(u["user_id"])
                except Exception as exc:
                    log.error("inbox sync failed for %s: %s", u["user_id"], exc)
        except Exception as exc:
            log.error("inbox sync loop error: %s", exc)
        await asyncio.sleep(_INTERVAL_S)

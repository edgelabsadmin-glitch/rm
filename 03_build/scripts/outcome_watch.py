"""
SPEC-033 — entry point for the Activepieces `outcome_watch_daily` cron.

Runs the after-action outcome sweep once and prints the tally. The Phase-1 SFDC
Task-completed checker is wired here (via the `sf` CLI); email-reply and EBR
checks stay conservative defaults until their adapters are connected.

Usage:  python scripts/outcome_watch.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess


async def _sfdc_task_completed(external_id: str | None) -> bool:
    """True iff the SFDC Task `external_id` is Status='Completed' (sf CLI query)."""
    if not external_id:
        return False
    target_org = os.environ.get("PULSE_SFDC_TARGET_ORG", "production")
    query = f"SELECT Status FROM Task WHERE Id = '{external_id}' LIMIT 1"
    cmd = ["sf", "data", "query", "--target-org", target_org, "--query", query, "--json"]
    p = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return False
    records = json.loads(p.stdout)["result"].get("records", [])
    return bool(records) and records[0].get("Status") == "Completed"


async def main() -> None:
    from core.llm.config import load_env
    from core.outcomes.watchers import EvidenceCheckers, run_outcome_watch

    load_env()
    tally = await run_outcome_watch(evidence=EvidenceCheckers(task_completed=_sfdc_task_completed))
    print(json.dumps({"outcome_watch": tally}))


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())

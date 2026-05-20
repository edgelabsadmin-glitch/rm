"""
SPEC-032 — SFDC Task dispatch (the canonical Pulse → SFDC write path, §6 rule 6).

Creates a Salesforce `Task` via the `sf` CLI (Decision 14 / reference_sfdc_access:
alias `production`, always --target-org). OwnerId is set to the action's owning
RM so the task lands on the right rep's list. This is the ONLY place Pulse writes
to SFDC, and it is reached only from `dispatch_approved_action` (post-approval).

The CLI call is blocking, so it runs in a worker thread (ADR-001 async). The
runner is injectable for unit tests (no real org touched).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess

from core.actions.queue import ActionRecord


def _sf_create_task(values: dict[str, str], *, target_org: str, sf_bin: str = "sf") -> str:
    """Run `sf data create record --sobject Task`; return the new record Id."""
    pairs = " ".join(f"{k}={json.dumps(v)}" for k, v in values.items())
    cmd = [
        sf_bin,
        "data",
        "create",
        "record",
        "--sobject",
        "Task",
        "--target-org",
        target_org,
        "--values",
        pairs,
        "--json",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"sf Task create failed ({p.returncode}): {p.stderr[:300]}")
    return json.loads(p.stdout)["result"]["id"]


def _compose_values(action: ActionRecord) -> dict[str, str]:
    card = action.action_card
    subject = card.get("subject") or card.get("headline") or action.why_oneline
    description = (
        card.get("body") or card.get("note") or card.get("description") or action.why_oneline
    )
    values: dict[str, str] = {
        "Subject": str(subject)[:255],
        "Description": str(description),
        "Status": "Not Started",
        "Priority": "High" if action.urgency == "high" else "Normal",
    }
    if action.rm_id:
        values["OwnerId"] = action.rm_id  # land on the owning RM's list
    if action.customer_id:
        values["WhatId"] = action.customer_id  # relate to the Account
    return values


async def create(action: ActionRecord, *, runner=None) -> str:
    """Create the SFDC Task; returns the record Id. `runner` overrides the CLI
    call in tests (signature: (values: dict, *, target_org: str) -> str)."""
    values = _compose_values(action)
    if os.environ.get("PULSE_DISPATCH_DRY_RUN") == "1":
        return "dry-run"
    target_org = os.environ.get("PULSE_SFDC_TARGET_ORG", "production")
    if runner is not None:
        result = runner(values, target_org=target_org)
        if asyncio.iscoroutine(result):
            return await result
        return result
    return await asyncio.to_thread(_sf_create_task, values, target_org=target_org)

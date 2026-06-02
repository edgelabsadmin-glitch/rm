"""
Match email addresses to SF account IDs via pulse.sf_contacts.

build_email_index() loads the full contact email → account_id map once per
sync run. match_accounts(addresses, index) returns a deduplicated list of
candidate_entity dicts for any addresses that hit a known contact.
"""
from __future__ import annotations

import logging

from core.db import get_pool
from psycopg.rows import dict_row

log = logging.getLogger(__name__)


async def build_email_index() -> dict[str, str]:
    """Return {lowercase_email: account_id} for all SF contacts."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (
            await conn.execute(
                "SELECT LOWER(email) AS email, account_id "
                "FROM pulse.sf_contacts WHERE email IS NOT NULL"
            )
        ).fetchall()
    return {r["email"]: r["account_id"] for r in rows}


def match_accounts(
    addresses: list[str],
    index: dict[str, str],
) -> list[dict]:
    """Return candidate_entity dicts for any address that hits a known contact.

    Each result has {type: 'sf_account', sfdc_id: <account_id>} — same shape
    used by Chorus/Zoom candidate_entities so the meetings query works uniformly.
    Deduplicates: one entry per account even if multiple contacts match.
    """
    seen: set[str] = set()
    entities: list[dict] = []
    for addr in addresses:
        normalized = addr.lower().strip()
        account_id = index.get(normalized)
        if account_id and account_id not in seen:
            seen.add(account_id)
            entities.append({"type": "sf_account", "sfdc_id": account_id})
    return entities

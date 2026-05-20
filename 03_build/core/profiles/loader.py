"""
SPEC-029 — Per-Profile Markdown loader (Design 06). Read/upsert the pulse.profiles
row for a (profile_type, entity_id). Skills with a profile-read dependency call
get_profile(); the regenerator/editor call upsert_profile().
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from psycopg.rows import dict_row

from core.db import get_pool

PROFILE_TYPES = ("customer", "talent", "rm")


def content_hash(content_md: str) -> str:
    return hashlib.sha256(content_md.encode()).hexdigest()


async def get_profile(profile_type: str, entity_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT * FROM pulse.profiles WHERE profile_type = %s AND entity_id = %s;",
                (profile_type, entity_id),
            )
            return await cur.fetchone()


async def upsert_profile(
    profile_type: str,
    entity_id: str,
    content_md: str,
    *,
    override_active: bool = False,
    override_source_md: str | None = None,
) -> str:
    """Insert or update a profile by entity_id; returns the content hash."""
    digest = content_hash(content_md)
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.profiles "
            "(profile_id, profile_type, entity_id, content_md, content_hash, "
            " override_active, override_source_md, last_regenerated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) "
            "ON CONFLICT (entity_id) DO UPDATE SET "
            "content_md = EXCLUDED.content_md, content_hash = EXCLUDED.content_hash, "
            "override_active = EXCLUDED.override_active, "
            "override_source_md = EXCLUDED.override_source_md, "
            "last_regenerated_at = NOW();",
            (
                str(uuid4()),
                profile_type,
                entity_id,
                content_md,
                digest,
                override_active,
                override_source_md,
            ),
        )
    return digest

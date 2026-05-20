"""
SPEC-029 — Per-Profile Markdown API (Design 06).

GET  /profiles/{profile_type}/{entity_id}  → the profile (404 if none).
PUT  /profiles/{profile_type}/{entity_id}  → RM edit (override; emits profile-edited).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.profiles.editor import edit_profile
from core.profiles.loader import PROFILE_TYPES, get_profile

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileEdit(BaseModel):
    content_md: str
    editor_id: str | None = None


def _validate_type(profile_type: str) -> None:
    if profile_type not in PROFILE_TYPES:
        raise HTTPException(status_code=400, detail=f"unknown profile_type {profile_type!r}")


@router.get("/{profile_type}/{entity_id}")
async def read_profile(profile_type: str, entity_id: str) -> dict[str, Any]:
    _validate_type(profile_type)
    row = await get_profile(profile_type, entity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return {
        "profile_type": row["profile_type"],
        "entity_id": row["entity_id"],
        "content_md": row["content_md"],
        "override_active": row["override_active"],
        "last_regenerated_at": row["last_regenerated_at"].isoformat(),
    }


@router.put("/{profile_type}/{entity_id}")
async def update_profile(profile_type: str, entity_id: str, body: ProfileEdit) -> dict[str, Any]:
    _validate_type(profile_type)
    return await edit_profile(profile_type, entity_id, body.content_md, body.editor_id)

# ABOUTME: Data fetching service for NPC information (like React hooks/services pattern)

"""
Service layer for fetching NPC data from the database.
Separates data fetching logic from UI components.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import and_, select

from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import (
    NPC,
    CharacterProfile,
    GeneratedDialogue,
    VoicePreview,
    WikiSnapshot,
)


async def get_available_npcs(db: DatabaseManager) -> list[dict[str, Any]]:
    """
    Query NPCs with complete voice profiles suitable for Tab 1 demonstration.

    Requires: wiki snapshot, character profile, selected voice, AND dialogue samples.

    Returns list of dicts with 'id', 'name', and 'display_name' (name + variant if present).
    """
    async with db.async_session() as session:
        # Query NPCs with complete profiles:
        # - Has wiki snapshot with content
        # - Has character profile
        # - Has selected voice preview
        # - Has at least one dialogue sample
        stmt = (
            select(NPC)
            .join(WikiSnapshot, WikiSnapshot.npc_id == NPC.id)
            .join(CharacterProfile, CharacterProfile.npc_id == NPC.id)
            .where(
                and_(
                    NPC.selected_preview_id.is_not(None),
                    WikiSnapshot.raw_markdown.is_not(None),
                    CharacterProfile.profile_json.is_not(None),
                )
            )
        )

        result = await session.execute(stmt)
        npcs = result.scalars().unique().all()

        # Filter to only those with dialogue samples
        npc_list = []
        for npc in npcs:
            # Check if this NPC has dialogue samples
            dialogue_stmt = select(GeneratedDialogue).where(GeneratedDialogue.npc_id == npc.id).limit(1)
            dialogue_result = await session.execute(dialogue_stmt)
            if dialogue_result.scalar_one_or_none():
                display_name = npc.name
                if npc.variant:
                    display_name = f"{npc.name} ({npc.variant})"
                npc_list.append({"id": npc.id, "name": npc.name, "display_name": display_name})

        # Sort alphabetically by display name
        npc_list.sort(key=lambda x: x["display_name"])
        return npc_list


async def get_npcs_with_voices(db: DatabaseManager) -> list[dict[str, Any]]:
    """
    Query NPCs that have voice previews (for voice management and dialogue generation).

    Less strict than get_available_npcs - only requires voices, not dialogue samples.
    Suitable for Tab 2 pipeline operations.

    Returns list of dicts with 'id', 'name', and 'display_name' (name + variant if present).
    """
    async with db.async_session() as session:
        # Query NPCs with voice previews
        # - Has at least one voice preview
        # - Preferably has selected voice
        stmt = (
            select(NPC)
            .join(VoicePreview, VoicePreview.npc_id == NPC.id)
            .distinct()
        )

        result = await session.execute(stmt)
        npcs = result.scalars().unique().all()

        npc_list = []
        for npc in npcs:
            display_name = npc.name
            if npc.variant:
                display_name = f"{npc.name} ({npc.variant})"
            npc_list.append({"id": npc.id, "name": npc.name, "display_name": display_name})

        # Sort alphabetically by display name
        npc_list.sort(key=lambda x: x["display_name"])
        return npc_list


async def get_npc_display_data(db: DatabaseManager, npc_id: int) -> dict[str, Any]:
    """
    Retrieve all display information for a selected NPC.

    Returns structured dict mapping directly to UI components.
    """
    async with db.async_session() as session:
        # Load NPC with all related data
        stmt = select(NPC).where(NPC.id == npc_id)
        result = await session.execute(stmt)
        npc = result.scalar_one_or_none()

        if not npc:
            return {
                "npc": None,
                "wiki_snapshot": None,
                "character_profile": None,
                "voice_previews": [],
                "dialogue_samples": [],
            }

        # Load wiki snapshot
        wiki_stmt = select(WikiSnapshot).where(WikiSnapshot.npc_id == npc_id)
        wiki_result = await session.execute(wiki_stmt)
        wiki_snapshot = wiki_result.scalar_one_or_none()

        # Load character profile
        profile_stmt = select(CharacterProfile).where(CharacterProfile.npc_id == npc_id)
        profile_result = await session.execute(profile_stmt)
        character_profile = profile_result.scalar_one_or_none()

        # Load all voice previews
        preview_stmt = select(VoicePreview).where(VoicePreview.npc_id == npc_id).order_by(VoicePreview.id)
        preview_result = await session.execute(preview_stmt)
        voice_previews = list(preview_result.scalars().all())

        # Load dialogue samples (limit to first 10 for UI)
        dialogue_stmt = (
            select(GeneratedDialogue).where(GeneratedDialogue.npc_id == npc_id).order_by(GeneratedDialogue.id).limit(10)
        )
        dialogue_result = await session.execute(dialogue_stmt)
        dialogue_samples = list(dialogue_result.scalars().all())

        return {
            "npc": npc,
            "wiki_snapshot": wiki_snapshot,
            "character_profile": character_profile,
            "voice_previews": voice_previews,
            "dialogue_samples": dialogue_samples,
        }


async def get_all_npcs_for_pipeline(db: DatabaseManager) -> list[dict[str, Any]]:
    """
    Query ALL NPCs that exist in the database (for pipeline selection).

    Returns list of dicts with 'id', 'name', and 'display_name' (name + variant if present).
    Sorted alphabetically.
    """
    async with db.async_session() as session:
        stmt = select(NPC).order_by(NPC.name)
        result = await session.execute(stmt)
        npcs = result.scalars().all()

        npc_list = []
        for npc in npcs:
            display_name = npc.name
            if npc.variant:
                display_name = f"{npc.name} ({npc.variant})"
            npc_list.append({"id": npc.id, "name": npc.name, "display_name": display_name})

        return npc_list


async def find_npc_id_by_display_name(db: DatabaseManager, display_name: str) -> int | None:
    """
    Find NPC ID from display name.

    Args:
        db: Database manager instance
        display_name: The display name (e.g., "Romeo" or "Romeo (Varrock)")

    Returns:
        NPC ID if found, None otherwise
    """
    npcs = await get_available_npcs(db)
    for npc in npcs:
        if npc["display_name"] == display_name:
            return npc["id"]
    logger.warning(f"Could not find NPC ID for display name: {display_name}")
    return None

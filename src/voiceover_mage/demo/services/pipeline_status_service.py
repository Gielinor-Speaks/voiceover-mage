# ABOUTME: Pipeline status detection service - check what stages exist for an NPC

"""
Service for detecting what pipeline stages have been completed for an NPC.
Helps UI show intelligent options about what to run or regenerate.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import CharacterProfile, NPC, VoicePreview, WikiSnapshot


async def get_pipeline_status(db: DatabaseManager, npc_id: int) -> dict[str, Any]:
    """
    Check what pipeline stages exist for an NPC.

    Returns dict with:
    - exists: bool - NPC exists in database
    - npc_name: str | None - NPC name if exists
    - stages: dict with completion status for each stage
    - next_action: str - Suggested next action
    """
    async with db.async_session() as session:
        # Check if NPC exists
        npc_stmt = select(NPC).where(NPC.id == npc_id)
        npc_result = await session.execute(npc_stmt)
        npc = npc_result.scalar_one_or_none()

        if not npc:
            return {
                "exists": False,
                "npc_id": npc_id,
                "npc_name": None,
                "stages": {
                    "wiki": False,
                    "profile": False,
                    "voices": False,
                    "selected": False,
                },
                "next_action": "create_new",
                "voice_count": 0,
            }

        # Check wiki snapshot
        wiki_stmt = select(WikiSnapshot).where(WikiSnapshot.npc_id == npc_id)
        wiki_result = await session.execute(wiki_stmt)
        wiki_snapshot = wiki_result.scalar_one_or_none()

        # Check character profile
        profile_stmt = select(CharacterProfile).where(CharacterProfile.npc_id == npc_id)
        profile_result = await session.execute(profile_stmt)
        character_profile = profile_result.scalar_one_or_none()

        # Check voice previews
        voices_stmt = select(VoicePreview).where(VoicePreview.npc_id == npc_id)
        voices_result = await session.execute(voices_stmt)
        voice_previews = list(voices_result.scalars().all())

        # Determine status
        has_wiki = wiki_snapshot is not None
        has_profile = character_profile is not None
        has_voices = len(voice_previews) > 0
        has_selected = npc.selected_preview_id is not None

        # Determine next action
        if not has_wiki:
            next_action = "extract_wiki"
        elif not has_profile:
            next_action = "generate_profile"
        elif not has_voices:
            next_action = "generate_voices"
        elif not has_selected:
            next_action = "select_voice"
        else:
            next_action = "complete"

        return {
            "exists": True,
            "npc_id": npc_id,
            "npc_name": npc.name,
            "stages": {
                "wiki": has_wiki,
                "profile": has_profile,
                "voices": has_voices,
                "selected": has_selected,
            },
            "next_action": next_action,
            "voice_count": len(voice_previews),
        }


def format_pipeline_status_html(status: dict[str, Any]) -> str:
    """
    Format pipeline status as beautiful HTML with emojis.

    Args:
        status: Status dict from get_pipeline_status()

    Returns:
        HTML string showing current pipeline state
    """
    if not status["exists"]:
        return """
        <div style="padding: 24px; background: white; border-radius: 12px; border: 2px dashed #667eea; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 12px;">🆕</div>
            <div style="font-size: 18px; font-weight: 600; color: #111;">New Character</div>
            <div style="font-size: 14px; color: #666; margin-top: 8px;">Ready to create!</div>
        </div>
        """

    npc_name = status["npc_name"]
    stages = status["stages"]
    voice_count = status["voice_count"]

    # Build stage indicators
    wiki_icon = "✅" if stages["wiki"] else "⭕"
    profile_icon = "✅" if stages["profile"] else "⭕"
    voices_icon = "✅" if stages["voices"] else "⭕"
    selected_icon = "✅" if stages["selected"] else "⭕"

    wiki_status = "Complete" if stages["wiki"] else "Not started"
    profile_status = "Complete" if stages["profile"] else "Not started"
    voices_status = f"{voice_count} voices" if stages["voices"] else "Not started"
    selected_status = "Selected" if stages["selected"] else "None selected"

    # Color coding
    complete_color = "#10b981"
    pending_color = "#94a3b8"

    return f"""
    <div style="background: white; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
        <!-- Header -->
        <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div style="font-size: 24px; font-weight: 700; color: white;">
                📋 {npc_name}
            </div>
        </div>

        <!-- Pipeline Stages -->
        <div style="padding: 0;">
            <!-- Wiki Stage -->
            <div style="display: flex; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e2e8f0;">
                <div style="flex: 1; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 28px;">{wiki_icon}</span>
                    <div>
                        <div style="font-weight: 600; color: #1e293b;">📖 Wiki Extraction</div>
                        <div style="font-size: 13px; color: {"#10b981" if stages["wiki"] else "#94a3b8"};">
                            {wiki_status}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Profile Stage -->
            <div style="display: flex; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e2e8f0;">
                <div style="flex: 1; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 28px;">{profile_icon}</span>
                    <div>
                        <div style="font-weight: 600; color: #1e293b;">🧠 Character Analysis</div>
                        <div style="font-size: 13px; color: {"#10b981" if stages["profile"] else "#94a3b8"};">
                            {profile_status}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Voices Stage -->
            <div style="display: flex; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e2e8f0;">
                <div style="flex: 1; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 28px;">{voices_icon}</span>
                    <div>
                        <div style="font-weight: 600; color: #1e293b;">🎤 Voice Generation</div>
                        <div style="font-size: 13px; color: {"#10b981" if stages["voices"] else "#94a3b8"};">
                            {voices_status}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Selection Stage -->
            <div style="display: flex; align-items: center; padding: 16px 20px;">
                <div style="flex: 1; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 28px;">{selected_icon}</span>
                    <div>
                        <div style="font-weight: 600; color: #1e293b;">🎯 Voice Selection</div>
                        <div style="font-size: 13px; color: {"#10b981" if stages["selected"] else "#94a3b8"};">
                            {selected_status}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

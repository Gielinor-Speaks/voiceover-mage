# ABOUTME: Pipeline service wrapper for web UI operations

"""
Service wrapper for UnifiedPipelineService to provide UI-friendly interfaces.
Handles async pipeline operations with progress tracking.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.persistence.manager import DatabaseManager


async def run_full_pipeline(
    db: DatabaseManager, npc_id: int, progress_callback: callable | None = None
) -> dict[str, Any]:
    """
    Run the complete NPC-to-voice pipeline with stage-by-stage progress tracking.

    Args:
        db: Database manager instance
        npc_id: NPC ID to process
        progress_callback: Optional callback for progress updates (progress, status_message)

    Returns:
        Dictionary with results and status
    """
    try:
        if progress_callback:
            progress_callback(0.0, f"🔄 Starting pipeline for NPC {npc_id}...")

        pipeline = UnifiedPipelineService(db)

        # Stage 1: Raw extraction (0% → 25%)
        if progress_callback:
            progress_callback(0.05, "📖 Stage 1/4: Extracting data from OSRS Wiki...")

        state = await pipeline._run_raw_extraction(npc_id)

        if progress_callback:
            progress_callback(0.25, f"✅ Wiki data extracted for {state.npc_name}")

        # Stage 2: LLM extraction (25% → 40%)
        if pipeline.api_key:
            if progress_callback:
                progress_callback(0.28, "🤖 Stage 2/4: Running LLM-enhanced extraction...")

            state = await pipeline._run_llm_extraction(state)

            if progress_callback:
                progress_callback(0.40, "✅ LLM extraction complete")
        else:
            if progress_callback:
                progress_callback(0.40, "⏭️  Stage 2/4: Skipped (no API key)")

        # Stage 3: Intelligent analysis (40% → 65%)
        if progress_callback:
            progress_callback(0.43, "🧠 Stage 3/4: Analyzing character profile...")

        state = await pipeline._run_intelligent_analysis(state)

        if progress_callback:
            progress_callback(0.65, "✅ Character analysis complete")

        # Stage 4: Voice generation (65% → 100%)
        if progress_callback:
            progress_callback(0.68, "🎤 Stage 4/4: Generating voice candidates...")

        state = await pipeline._run_voice_generation(state)

        num_voices = len(state.voice_previews) if state.voice_previews else 0
        if progress_callback:
            progress_callback(1.0, f"🎉 Pipeline complete! Generated {num_voices} voice candidates")

        return {
            "success": True,
            "npc_id": state.id,
            "npc_name": state.npc_name,
            "message": f"Successfully processed {state.npc_name}",
            "details": {
                "wiki_extracted": state.wiki_snapshot is not None,
                "profile_generated": state.character_profile_entry is not None,
                "voices_generated": num_voices,
                "voice_selected": state.npc.selected_preview_id is not None,
            },
        }

    except Exception as e:
        logger.error(f"Pipeline failed for NPC {npc_id}: {e}")
        if progress_callback:
            progress_callback(0.0, f"❌ Error: {str(e)}")
        return {"success": False, "npc_id": npc_id, "error": str(e)}


async def regenerate_voice_candidates(
    db: DatabaseManager, npc_id: int, num_candidates: int = 3, progress_callback: callable | None = None
) -> dict[str, Any]:
    """
    Regenerate voice candidates for an existing NPC with progress tracking.

    Args:
        db: Database manager instance
        npc_id: NPC ID to regenerate voices for
        num_candidates: Number of voice candidates to generate
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary with results and status
    """
    try:
        if progress_callback:
            progress_callback(0.0, "🔄 Loading NPC data...")

        from sqlalchemy import select

        from voiceover_mage.persistence.models import NPC, NPCPipelineState

        # Check if NPC exists and has required data
        async with db.async_session() as session:
            stmt = select(NPCPipelineState).where(NPCPipelineState.id == npc_id)
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            if not state or not state.character_profile_entry:
                return {
                    "success": False,
                    "error": "NPC must have a character profile before generating voices. Run full pipeline first.",
                }

        if progress_callback:
            progress_callback(0.2, f"🎤 Generating {num_candidates} new voice candidates...")

        pipeline = UnifiedPipelineService(db)

        # Re-run voice generation stage only
        state = await pipeline._run_voice_generation(state)

        num_voices = len(state.voice_previews) if state.voice_previews else 0

        if progress_callback:
            progress_callback(1.0, f"🎉 Generated {num_voices} new voices!")

        return {
            "success": True,
            "npc_id": state.id,
            "npc_name": state.npc_name,
            "num_voices": num_voices,
            "message": f"Generated {num_voices} voice candidates",
        }

    except Exception as e:
        logger.error(f"Voice regeneration failed for NPC {npc_id}: {e}")
        if progress_callback:
            progress_callback(0.0, f"❌ Error: {str(e)}")
        return {"success": False, "npc_id": npc_id, "error": str(e)}


async def select_voice_candidate(db: DatabaseManager, npc_id: int, preview_id: int) -> dict[str, Any]:
    """
    Select a voice preview as the active voice for an NPC.

    Args:
        db: Database manager instance
        npc_id: NPC ID
        preview_id: VoicePreview ID to select

    Returns:
        Dictionary with results and status
    """
    try:
        async with db.async_session() as session:
            from sqlalchemy import select, update

            from voiceover_mage.persistence.models import NPC, VoicePreview

            # Verify the preview exists and belongs to this NPC
            preview_stmt = select(VoicePreview).where(
                VoicePreview.id == preview_id, VoicePreview.npc_id == npc_id
            )
            preview_result = await session.execute(preview_stmt)
            preview = preview_result.scalar_one_or_none()

            if not preview:
                return {
                    "success": False,
                    "error": f"Preview {preview_id} not found for NPC {npc_id}",
                }

            # Update NPC's selected preview
            update_stmt = update(NPC).where(NPC.id == npc_id).values(selected_preview_id=preview_id)
            await session.execute(update_stmt)
            await session.commit()

            logger.info(f"Selected voice preview {preview_id} for NPC {npc_id}")

            return {
                "success": True,
                "npc_id": npc_id,
                "preview_id": preview_id,
                "message": f"Voice candidate {preview_id} selected",
            }

    except Exception as e:
        logger.error(f"Voice selection failed: {e}")
        return {"success": False, "error": str(e)}


async def generate_dialogue(
    db: DatabaseManager,
    npc_id: int,
    text: str,
    animation_id: int | None = None,
    emotion: str | None = None,
    progress_callback: callable | None = None,
) -> dict[str, Any]:
    """
    Generate dialogue audio for an NPC with optional emotion/animation.

    Args:
        db: Database manager instance
        npc_id: NPC ID
        text: Text to synthesize
        animation_id: Optional OSRS animation ID for emotion mapping
        emotion: Optional emotion description
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary with audio bytes and metadata
    """
    try:
        if progress_callback:
            progress_callback(0.0, "🔍 Loading NPC voice profile...")

        from sqlalchemy import select

        from voiceover_mage.persistence.models import NPC, VoicePreview

        async with db.async_session() as session:
            # Get NPC and selected voice
            npc_stmt = select(NPC).where(NPC.id == npc_id)
            npc_result = await session.execute(npc_stmt)
            npc = npc_result.scalar_one_or_none()

            if not npc or not npc.selected_preview_id:
                return {"success": False, "error": "NPC not found or no voice selected"}

            # Get selected voice preview
            preview_stmt = select(VoicePreview).where(VoicePreview.id == npc.selected_preview_id)
            preview_result = await session.execute(preview_stmt)
            preview = preview_result.scalar_one_or_none()

            if not preview or not preview.audio_bytes:
                return {"success": False, "error": "Voice preview not found or has no audio"}

            if progress_callback:
                progress_callback(0.2, f"🎙️ Synthesizing speech for {npc.name}...")

            # Use local TTS adapter for voice cloning
            from voiceover_mage.config import get_config
            from voiceover_mage.services.audio.local import LocalTTSAdapter

            config = get_config()
            tts_service = LocalTTSAdapter(api_url=config.local_tts_api_url)

            # Generate audio using the correct LocalTTSAdapter method
            # Note: LocalTTSAdapter uses text_description mode for emotion by default
            # The animation_id parameter is passed through for emotion mapping
            if progress_callback:
                progress_callback(0.5, "⏳ Calling local TTS API (this may take 5-10 seconds)...")

            audio_bytes = await tts_service.generate_speech_with_reference(
                text=text,
                reference_audio_bytes=preview.audio_bytes,
                audio_format=".mp3",  # Voice previews are stored as MP3
                animation_id=animation_id
            )

            if progress_callback:
                progress_callback(1.0, "✅ Speech generated successfully!")

            return {
                "success": True,
                "npc_id": npc_id,
                "npc_name": npc.name,
                "text": text,
                "audio_bytes": audio_bytes,
                "emotion": emotion or "Neutral",
                "animation_id": animation_id,
            }

    except Exception as e:
        logger.error(f"Dialogue generation failed: {e}")
        if progress_callback:
            progress_callback(0.0, f"Error: {str(e)}")
        return {"success": False, "error": str(e)}

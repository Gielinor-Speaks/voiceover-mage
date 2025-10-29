# ABOUTME: Event handlers for pipeline management tab

"""
Event handlers for pipeline operations including NPC processing,
voice management, and dialogue generation.
"""

from __future__ import annotations

from typing import Any

import gradio as gr
from loguru import logger

from voiceover_mage.demo.services.npc_data_service import get_available_npcs, get_npc_display_data, get_npcs_with_voices
from voiceover_mage.demo.services.pipeline_service import (
    generate_dialogue,
    regenerate_voice_candidates,
    run_full_pipeline,
    select_voice_candidate,
)
from voiceover_mage.persistence.manager import DatabaseManager


def _format_pipeline_result(result: dict) -> str:
    """Format pipeline result as readable HTML."""
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"""
        <div style="padding: 20px; background: #fee; border-left: 4px solid #c33; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #c33;">❌ Pipeline Failed</h3>
            <p style="font-family: monospace;">{error}</p>
        </div>
        """

    details = result.get("details", {})
    npc_name = result.get("npc_name", "Unknown")
    npc_id = result.get("npc_id", "?")

    return f"""
    <div style="padding: 20px; background: #efe; border-left: 4px solid #3c3; border-radius: 4px;">
        <h3 style="margin-top: 0; color: #3c3;">✅ Pipeline Completed Successfully</h3>

        <div style="margin: 15px 0;">
            <strong>NPC:</strong> {npc_name} <span style="color: #666;">(ID: {npc_id})</span>
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><strong>Stage</strong></td>
                <td style="padding: 8px;"><strong>Status</strong></td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px;">📖 Wiki Extraction</td>
                <td style="padding: 8px;">{"✅ Complete" if details.get("wiki_extracted") else "❌ Failed"}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px;">🧠 Character Profile</td>
                <td style="padding: 8px;">{"✅ Generated" if details.get("profile_generated") else "❌ Failed"}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px;">🎤 Voice Generation</td>
                <td style="padding: 8px;">✅ {details.get("voices_generated", 0)} candidates generated</td>
            </tr>
            <tr>
                <td style="padding: 8px;">🎯 Voice Selection</td>
                <td style="padding: 8px;">{"✅ Voice selected" if details.get("voice_selected") else "⏸️ Pending (go to Manage Voices tab)"}</td>
            </tr>
        </table>

        <div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 4px;">
            <strong>💡 Next Steps:</strong> Switch to the <strong>🎭 Manage Voices</strong> tab to listen to candidates and select the best voice.
        </div>
    </div>
    """


async def handle_run_pipeline(
    npc_id: int | None, db: DatabaseManager, progress=gr.Progress()
) -> tuple[str, str, gr.update, gr.update]:
    """
    Handle running the full pipeline on an NPC.

    Args:
        npc_id: NPC ID to process
        db: Database manager
        progress: Gradio progress tracker

    Returns:
        Tuple of (status_message, formatted_results_html, voice_dropdown_update, dialogue_dropdown_update)
    """
    if not npc_id:
        return "❌ Please enter an NPC ID", "", gr.update(), gr.update()

    try:
        # Progress callback
        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        result = await run_full_pipeline(db, int(npc_id), progress_callback=update_progress)

        if result["success"]:
            status = f"✅ Successfully processed NPC {result['npc_name']} (ID: {result['npc_id']})"
            html_output = _format_pipeline_result(result)

            # Refresh the NPC dropdowns so the new NPC appears
            npcs = await get_npcs_with_voices(db)
            choices = [npc["display_name"] for npc in npcs]
            dropdown_update = gr.update(choices=choices)

            return status, html_output, dropdown_update, dropdown_update
        else:
            status = f"❌ Pipeline failed: {result.get('error', 'Unknown error')}"
            html_output = _format_pipeline_result(result)
            return status, html_output, gr.update(), gr.update()

    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        error_result = {"success": False, "error": str(e)}
        return f"❌ Error: {str(e)}", _format_pipeline_result(error_result), gr.update(), gr.update()


async def handle_load_npcs_for_voice_management(db: DatabaseManager) -> gr.update:
    """Load NPCs for voice management dropdown (includes NPCs with voices but no dialogue)."""
    npcs = await get_npcs_with_voices(db)
    choices = [npc["display_name"] for npc in npcs]
    return gr.update(choices=choices, value=choices[0] if choices else None)


async def handle_voice_npc_selection(npc_display_name: str | None, db: DatabaseManager) -> tuple[Any, ...]:
    """
    Handle NPC selection in voice management tab.

    Returns:
        Tuple of updates for 3 audio players
    """
    if not npc_display_name:
        return tuple([gr.update(value=None)] * 3)

    try:
        # Find NPC ID (use npcs_with_voices since we're in voice management tab)
        npcs = await get_npcs_with_voices(db)
        npc_id = None
        for npc in npcs:
            if npc["display_name"] == npc_display_name:
                npc_id = npc["id"]
                break

        if not npc_id:
            return tuple([gr.update(value=None)] * 3)

        # Get NPC data
        data = await get_npc_display_data(db, npc_id)
        voice_previews = data.get("voice_previews", [])

        updates = []
        for i in range(3):
            if i < len(voice_previews):
                preview = voice_previews[i]
                audio_data = preview.audio_bytes if preview.audio_bytes else None
                updates.append(gr.update(value=audio_data))
            else:
                updates.append(gr.update(value=None))

        return tuple(updates)

    except Exception as e:
        logger.error(f"Error loading voice candidates: {e}")
        return tuple([gr.update(value=None)] * 3)


async def handle_select_voice(
    candidate_idx: int, npc_display_name: str | None, db: DatabaseManager
) -> tuple[str, Any, Any, Any]:
    """
    Handle voice candidate selection.

    Args:
        candidate_idx: Index of candidate (0, 1, or 2)
        npc_display_name: Display name of NPC
        db: Database manager

    Returns:
        Tuple of (status_message, audio1, audio2, audio3) with selected one highlighted
    """
    if not npc_display_name:
        return "❌ Please select an NPC", gr.update(), gr.update(), gr.update()

    try:
        # Find NPC ID (use npcs_with_voices for voice/dialogue tabs)
        npcs = await get_npcs_with_voices(db)
        npc_id = None
        for npc in npcs:
            if npc["display_name"] == npc_display_name:
                npc_id = npc["id"]
                break

        if not npc_id:
            return "❌ NPC not found", gr.update(), gr.update(), gr.update()

        # Get voice previews
        data = await get_npc_display_data(db, npc_id)
        voice_previews = data.get("voice_previews") or []

        if not voice_previews or candidate_idx >= len(voice_previews):
            return "❌ Voice candidate not found", gr.update(), gr.update(), gr.update()

        preview = voice_previews[candidate_idx]

        # Select the voice
        result = await select_voice_candidate(db, npc_id, preview.id)

        if result["success"]:
            # Reload to show selection
            audio_updates = await handle_voice_npc_selection(npc_display_name, db)
            return f"✅ Selected voice candidate {candidate_idx + 1}", *audio_updates
        else:
            return f"❌ Selection failed: {result.get('error', 'Unknown error')}", gr.update(), gr.update(), gr.update()

    except Exception as e:
        logger.error(f"Voice selection error: {e}")
        return f"❌ Error: {str(e)}", gr.update(), gr.update(), gr.update()


async def handle_regenerate_voices(
    npc_display_name: str | None, db: DatabaseManager, progress=gr.Progress()
) -> tuple[str, Any, Any, Any]:
    """
    Handle voice candidate regeneration.

    Returns:
        Tuple of (status_message, audio1, audio2, audio3)
    """
    if not npc_display_name:
        return "❌ Please select an NPC", gr.update(), gr.update(), gr.update()

    try:
        # Find NPC ID (use npcs_with_voices for voice/dialogue tabs)
        npcs = await get_npcs_with_voices(db)
        npc_id = None
        for npc in npcs:
            if npc["display_name"] == npc_display_name:
                npc_id = npc["id"]
                break

        if not npc_id:
            return "❌ NPC not found", gr.update(), gr.update(), gr.update()

        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        result = await regenerate_voice_candidates(db, npc_id, progress_callback=update_progress)

        if result["success"]:
            # Reload voice candidates
            audio_updates = await handle_voice_npc_selection(npc_display_name, db)
            return f"✅ Generated {result['num_voices']} new voice candidates", *audio_updates
        else:
            return (
                f"❌ Regeneration failed: {result.get('error', 'Unknown error')}",
                gr.update(),
                gr.update(),
                gr.update(),
            )

    except Exception as e:
        logger.error(f"Voice regeneration error: {e}")
        return f"❌ Error: {str(e)}", gr.update(), gr.update(), gr.update()


async def handle_generate_dialogue(
    npc_display_name: str | None,
    text: str,
    emotion_mode: str,
    animation_id: int | None,
    emotion_text: str,
    db: DatabaseManager,
    progress=gr.Progress(),
) -> tuple[str, Any, Any]:
    """
    Handle dialogue generation.

    Returns:
        Tuple of (status_message, audio_component, save_button_visibility)
    """
    if not npc_display_name:
        return "❌ Please select an NPC", gr.update(visible=False), gr.update(visible=False)

    if not text or not text.strip():
        return "❌ Please enter dialogue text", gr.update(visible=False), gr.update(visible=False)

    try:
        # Find NPC ID (use npcs_with_voices for voice/dialogue tabs)
        npcs = await get_npcs_with_voices(db)
        npc_id = None
        for npc in npcs:
            if npc["display_name"] == npc_display_name:
                npc_id = npc["id"]
                break

        if not npc_id:
            return "❌ NPC not found", gr.update(visible=False), gr.update(visible=False)

        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        # Determine emotion settings
        anim_id = None
        emotion = None

        if emotion_mode == "Animation ID" and animation_id is not None:
            if animation_id <= 0:
                return (
                    "❌ Animation ID must be a positive number",
                    gr.update(visible=False),
                    gr.update(visible=False),
                )
            anim_id = int(animation_id)
        elif emotion_mode == "Text Description" and emotion_text:
            emotion = emotion_text.strip()
            if not emotion:
                return (
                    "❌ Please enter an emotion description",
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

        result = await generate_dialogue(
            db, npc_id, text, animation_id=anim_id, emotion=emotion, progress_callback=update_progress
        )

        if result["success"]:
            audio_bytes = result["audio_bytes"]
            emotion_label = result.get("emotion", "Neutral")
            status = f"✅ Generated speech with {emotion_label} emotion"
            return status, gr.update(value=audio_bytes, visible=True, format="wav"), gr.update(visible=True)
        else:
            return (
                f"❌ Generation failed: {result.get('error', 'Unknown error')}",
                gr.update(visible=False),
                gr.update(visible=False),
            )

    except Exception as e:
        logger.error(f"Dialogue generation error: {e}")
        return f"❌ Error: {str(e)}", gr.update(visible=False), gr.update(visible=False)


def handle_emotion_mode_change(emotion_mode: str) -> tuple[Any, Any]:
    """Handle emotion mode radio button change to show/hide relevant inputs."""
    if emotion_mode == "Animation ID":
        return gr.update(visible=True), gr.update(visible=False)
    elif emotion_mode == "Text Description":
        return gr.update(visible=False), gr.update(visible=True)
    else:  # None
        return gr.update(visible=False), gr.update(visible=False)


async def handle_batch_process(
    npc_ids_text: str, extract: bool, profile: bool, voices: bool, db: DatabaseManager, progress=gr.Progress()
) -> tuple[str, dict]:
    """
    Handle batch processing of multiple NPCs.

    Returns:
        Tuple of (status_message, results_dict)
    """
    if not npc_ids_text or not npc_ids_text.strip():
        return "❌ Please enter NPC IDs", {}

    try:
        # Parse NPC IDs
        npc_ids = [int(id.strip()) for id in npc_ids_text.split(",") if id.strip().isdigit()]

        if not npc_ids:
            return "❌ No valid NPC IDs found", {}

        MAX_BATCH_SIZE = 50
        if len(npc_ids) > MAX_BATCH_SIZE:
            return f"❌ Too many NPCs (max {MAX_BATCH_SIZE}). Please split into smaller batches.", {}

        results = {"total": len(npc_ids), "completed": 0, "failed": 0, "npcs": []}

        # NOTE: Currently always runs full pipeline regardless of checkbox settings
        # TODO: Implement partial pipeline support in UnifiedPipelineService

        for idx, npc_id in enumerate(npc_ids):
            progress((idx + 1) / len(npc_ids), desc=f"Processing NPC {npc_id} ({idx + 1}/{len(npc_ids)})")

            try:
                # Always runs full pipeline (extract, profile, voices checkboxes are currently ignored)
                result = await run_full_pipeline(db, npc_id)
                if result["success"]:
                    results["completed"] += 1
                    results["npcs"].append({"npc_id": npc_id, "status": "success", "name": result["npc_name"]})
                else:
                    results["failed"] += 1
                    results["npcs"].append({"npc_id": npc_id, "status": "failed", "error": result.get("error")})
            except Exception as e:
                results["failed"] += 1
                results["npcs"].append({"npc_id": npc_id, "status": "failed", "error": str(e)})

        status = f"✅ Batch complete: {results['completed']} succeeded, {results['failed']} failed"
        return status, results

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return f"❌ Error: {str(e)}", {}

# ABOUTME: Event handlers for Voice Studio unified workflow

"""
Streamlined event handlers for the Voice Studio tab.
Supports progressive reveal - sections appear as they become relevant.
"""

from __future__ import annotations

from typing import Any

import gradio as gr
from loguru import logger

from voiceover_mage.demo.services.npc_data_service import get_npc_display_data
from voiceover_mage.demo.services.pipeline_service import (
    generate_dialogue,
    regenerate_voice_candidates,
    run_full_pipeline,
    select_voice_candidate,
)
from voiceover_mage.demo.services.pipeline_status_service import format_pipeline_status_html, get_pipeline_status
from voiceover_mage.persistence.manager import DatabaseManager


def _create_voice_label(voice_index: int, is_selected: bool) -> str:
    """Create label for voice candidate showing selection status."""
    if is_selected:
        return f"✓ Voice {voice_index + 1} (Currently Selected)"
    else:
        return f"Voice {voice_index + 1}"


async def handle_check_status(
    npc_input: str | None,
    db: DatabaseManager,
) -> tuple[str, gr.update, gr.update, list[Any], int | None, str | None]:
    """
    Check pipeline status for an NPC and show what stages exist.

    Returns tuple with updates for:
    - pipeline_status_html
    - action_buttons_row visibility
    - voice_section visibility
    - voice_cards_updates: list of updates for all 12 voice cards (column visibility, header, audio)
    - hidden_npc_id state
    - hidden_npc_name state
    """
    # Helper to create empty voice card updates (hide all 12 cards)
    def _empty_voice_cards():
        return [
            {
                "column": gr.update(visible=False),
                "audio": gr.update(value=None, label=_create_voice_label(i, False)),
            }
            for i in range(12)
        ]

    if not npc_input or not npc_input.strip():
        return (
            """
            <div style="padding: 20px; background: #fee; border-radius: 8px; border: 1px solid #fca5a5;">
                <p style="text-align: center; color: #991b1b; margin: 0;">
                    ❌ Please enter a character ID
                </p>
            </div>
            """,
            gr.update(visible=False),
            gr.update(visible=False),
            _empty_voice_cards(),
            None,
            None,
        )

    try:
        # Try to parse as NPC ID
        try:
            npc_id = int(npc_input.strip())
        except ValueError:
            return (
                f"""
                <div style="padding: 20px; background: #fee; border-radius: 8px; border: 1px solid #fca5a5;">
                    <p style="text-align: center; color: #991b1b; margin: 0;">
                        ❌ Invalid input: '{npc_input}'. Please enter a numeric NPC ID.
                    </p>
                </div>
                """,
                gr.update(visible=False),
                gr.update(visible=False),
                _empty_voice_cards(),
                None,
                None,
            )

        # Get pipeline status
        status = await get_pipeline_status(db, npc_id)
        status_html = format_pipeline_status_html(status)

        # If NPC has voices, load them and show voice section
        if status["stages"]["voices"]:
            display_data = await get_npc_display_data(db, npc_id)
            voice_previews = display_data.get("voice_previews", [])
            npc = display_data.get("npc")

            # Find which voice is selected (if any)
            selected_preview_id = npc.selected_preview_id if npc else None
            selected_index = None
            if selected_preview_id:
                for i, preview in enumerate(voice_previews[:3]):
                    if preview.id == selected_preview_id:
                        selected_index = i
                        break

            # Update all 12 voice cards (show/hide and populate based on available voices)
            voice_cards_updates = []
            for i in range(12):
                if i < len(voice_previews):
                    # Show this card
                    is_selected = (i == selected_index)
                    audio_bytes = voice_previews[i].audio_bytes
                    voice_cards_updates.append({
                        "column": gr.update(visible=True),
                        "audio": gr.update(value=audio_bytes, label=_create_voice_label(i, is_selected)),
                    })
                else:
                    # Hide this card
                    voice_cards_updates.append({
                        "column": gr.update(visible=False),
                        "audio": gr.update(value=None, label=_create_voice_label(i, False)),
                    })

            return (
                status_html,
                gr.update(visible=True),  # Show action buttons
                gr.update(visible=True),  # Show voice section
                voice_cards_updates,
                npc_id,
                status["npc_name"],
            )
        else:
            # No voices yet, don't show voice section
            return (
                status_html,
                gr.update(visible=True),  # Show action buttons
                gr.update(visible=False),  # Hide voice section
                _empty_voice_cards(),
                npc_id if status["exists"] else None,
                status.get("npc_name"),
            )

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return (
            f"""
            <div style="padding: 20px; background: #fee; border-radius: 8px; border: 1px solid #fca5a5;">
                <p style="text-align: center; color: #991b1b; margin: 0;">
                    ❌ Error: {str(e)}
                </p>
            </div>
            """,
            gr.update(visible=False),
            gr.update(visible=False),
            _empty_voice_cards(),
            None,
            None,
        )


def _format_creation_result(result: dict) -> str:
    """Format pipeline result as readable HTML."""
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"""
        <div style="padding: 20px; background: #fee; border-left: 4px solid #c33; border-radius: 8px;">
            <h3 style="margin-top: 0; color: #c33;">❌ Voice Creation Failed</h3>
            <p style="font-family: monospace; color: #666;">{error}</p>
        </div>
        """

    details = result.get("details", {})
    npc_name = result.get("npc_name", "Unknown")
    npc_id = result.get("npc_id", "?")
    num_voices = details.get("voices_generated", 0)

    return f"""
    <div style="padding: 24px; background: #efe; border-left: 4px solid #3c3; border-radius: 8px;">
        <h3 style="margin-top: 0; color: #3c3;">✅ Voice Created Successfully!</h3>

        <div style="margin: 16px 0; padding: 16px; background: white; border-radius: 6px;">
            <div style="margin-bottom: 8px;">
                <strong style="color: #111;">Character:</strong>
                <span style="color: #667eea; font-size: 16px;">{npc_name}</span>
                <span style="color: #999;"> (ID: {npc_id})</span>
            </div>
            <div>
                <strong style="color: #111;">Voice Options:</strong>
                <span style="color: #10b981; font-weight: 600;">{num_voices} candidates generated</span>
            </div>
        </div>

        <div style="margin-top: 16px; padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 6px;">
            <strong>💡 Next:</strong> Listen to the voice options below and select your favorite!
        </div>
    </div>
    """


async def handle_create_voice(
    npc_input: str | None,
    db: DatabaseManager,
    progress=gr.Progress(),
) -> tuple[str, str, gr.update, gr.update, Any, Any, Any, int | None, str | None]:
    """
    Handle voice creation for a character (new or existing).

    Returns tuple with updates for:
    - status_text
    - results_html
    - results_accordion visibility
    - voice_section visibility
    - voice_candidate_1 audio
    - voice_candidate_2 audio
    - voice_candidate_3 audio
    - hidden_npc_id state
    - hidden_npc_name state
    """
    if not npc_input or not npc_input.strip():
        return (
            "❌ Please enter a character name or ID",
            "",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
            None,
            None,
        )

    try:
        # Try to parse as NPC ID
        try:
            npc_id = int(npc_input.strip())
        except ValueError:
            return (
                f"❌ Invalid input: '{npc_input}'. Please enter a numeric NPC ID for now.",
                "",
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(value=None),
                gr.update(value=None),
                gr.update(value=None),
                None,
                None,
            )

        # Progress callback
        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        # Run the pipeline
        result = await run_full_pipeline(db, npc_id, progress_callback=update_progress)

        if not result["success"]:
            return (
                f"❌ Creation failed: {result.get('error', 'Unknown error')}",
                _format_creation_result(result),
                gr.update(visible=True, open=True),
                gr.update(visible=False),
                gr.update(value=None),
                gr.update(value=None),
                gr.update(value=None),
                None,
                None,
            )

        # Success - load voice previews
        npc_name = result["npc_name"]
        display_data = await get_npc_display_data(db, npc_id)

        voice_previews = display_data.get("voice_previews", [])

        # Prepare audio updates (up to 3 voices)
        audio_updates = []
        for i in range(3):
            if i < len(voice_previews):
                preview = voice_previews[i]
                audio_bytes = preview.audio_bytes  # VoicePreview is SQLModel, use attribute access
                audio_updates.append(gr.update(value=audio_bytes))
            else:
                audio_updates.append(gr.update(value=None))

        return (
            f"✅ Successfully created voice for {npc_name}!",
            _format_creation_result(result),
            gr.update(visible=True, open=True),
            gr.update(visible=True),  # Show voice section
            audio_updates[0],
            audio_updates[1],
            audio_updates[2],
            npc_id,
            npc_name,
        )

    except Exception as e:
        logger.error(f"Voice creation error: {e}")
        return (
            f"❌ Error: {str(e)}",
            _format_creation_result({"success": False, "error": str(e)}),
            gr.update(visible=True, open=True),
            gr.update(visible=False),
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
            None,
            None,
        )


async def handle_select_voice(
    candidate_index: int,
    npc_id: int | None,
    npc_name: str | None,
    db: DatabaseManager,
) -> tuple[str, list[Any]]:
    """
    Handle voice selection.

    Returns:
    - voice_status message
    - audio_label_updates: list of audio label updates for all 12 cards
    """
    # Helper to create all audio label updates
    def _all_label_updates(selected_idx: int | None = None):
        return [
            gr.update(label=_create_voice_label(i, i == selected_idx))
            for i in range(12)
        ]

    if not npc_id:
        return (
            "❌ No character selected",
            _all_label_updates(),
        )

    try:
        # Get display data to find the preview ID for this candidate
        display_data = await get_npc_display_data(db, npc_id)
        voice_previews = display_data.get("voice_previews", [])

        if candidate_index >= len(voice_previews):
            return (
                f"❌ Voice candidate {candidate_index + 1} not found",
                _all_label_updates(),
            )

        preview_id = voice_previews[candidate_index].id  # VoicePreview is SQLModel, use attribute access

        # Select the voice
        result = await select_voice_candidate(db, npc_id, preview_id)

        if result["success"]:
            return (
                f"✅ Voice {candidate_index + 1} selected for {npc_name}!",
                _all_label_updates(candidate_index),
            )
        else:
            return (
                f"❌ Selection failed: {result.get('error')}",
                _all_label_updates(),
            )

    except Exception as e:
        logger.error(f"Voice selection error: {e}")
        return (
            f"❌ Error: {str(e)}",
            _all_label_updates(),
        )


async def handle_regenerate_voices(
    npc_id: int | None,
    npc_name: str | None,
    db: DatabaseManager,
    progress=gr.Progress(),
) -> tuple[str, list[Any]]:
    """
    Handle voice regeneration.

    Returns updates for:
    - voice_status
    - audio_updates: list of audio updates for all 12 cards
    """
    # Helper to create empty audio updates
    def _empty_audio_updates():
        return [gr.update(value=None) for _ in range(12)]

    if not npc_id:
        return (
            "❌ No character selected",
            _empty_audio_updates(),
        )

    try:
        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        result = await regenerate_voice_candidates(db, npc_id, progress_callback=update_progress)

        if not result["success"]:
            return (
                f"❌ Regeneration failed: {result.get('error')}",
                _empty_audio_updates(),
            )

        # Load new voice previews
        display_data = await get_npc_display_data(db, npc_id)
        voice_previews = display_data.get("voice_previews", [])

        audio_updates = []
        for i in range(12):
            if i < len(voice_previews):
                audio_bytes = voice_previews[i].audio_bytes  # VoicePreview is SQLModel, use attribute access
                audio_updates.append(gr.update(value=audio_bytes))
            else:
                audio_updates.append(gr.update(value=None))

        return (
            f"✅ Generated {len(voice_previews)} new voices for {npc_name}!",
            audio_updates,
        )

    except Exception as e:
        logger.error(f"Voice regeneration error: {e}")
        return (
            f"❌ Error: {str(e)}",
            _empty_audio_updates(),
        )


async def handle_generate_dialogue_studio(
    npc_id: int | None,
    npc_name: str | None,
    dialogue_text: str,
    emotion_selector: str,
    db: DatabaseManager,
    progress=gr.Progress(),
) -> tuple[str, Any, gr.update]:
    """
    Handle dialogue generation in Voice Studio.

    Returns:
    - dialogue_status
    - generated_audio value
    - generated_audio visibility
    """
    if not npc_id:
        return "❌ No character selected", gr.update(value=None), gr.update(visible=False)

    if not dialogue_text or not dialogue_text.strip():
        return "❌ Please enter some dialogue text", gr.update(value=None), gr.update(visible=False)

    try:
        def update_progress(pct: float, msg: str):
            progress(pct, desc=msg)

        # Map emotion selector to emotion text (or None)
        emotion_map = {
            "😊 Friendly": "friendly",
            "😠 Angry": "angry",
            "😢 Sad": "sad",
            "😲 Surprised": "surprised",
            "😌 Calm": "calm",
            "😰 Fearful": "fearful",
            "🤢 Disgusted": "disgusted",
            "None": None,
        }
        emotion = emotion_map.get(emotion_selector)

        result = await generate_dialogue(
            db, npc_id, dialogue_text, emotion=emotion, progress_callback=update_progress
        )

        if result["success"]:
            audio_bytes = result["audio_bytes"]
            return (
                f"✅ Generated speech for {npc_name}!",
                gr.update(value=audio_bytes, format="wav"),
                gr.update(visible=True),
            )
        else:
            return (
                f"❌ Generation failed: {result.get('error')}",
                gr.update(value=None),
                gr.update(visible=False),
            )

    except Exception as e:
        logger.error(f"Dialogue generation error: {e}")
        return (
            f"❌ Error: {str(e)}",
            gr.update(value=None),
            gr.update(visible=False),
        )

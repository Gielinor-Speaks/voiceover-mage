# ABOUTME: Event handlers for demo tab interactions

"""
Event handlers for the demo tab.
Manages user interactions like NPC selection and data loading.
"""

from __future__ import annotations

from typing import Any

import gradio as gr
from loguru import logger

from voiceover_mage.demo.services.npc_data_service import (
    find_npc_id_by_display_name,
    get_available_npcs,
    get_npc_display_data,
)
from voiceover_mage.demo.utils.data_transformers import (
    extract_wiki_text,
    get_wiki_url,
    transform_character_profile_to_html,
    transform_dialogue_samples_to_ui,
    transform_voice_previews_to_candidates,
)
from voiceover_mage.demo.utils.wiki_fetcher import fetch_wiki_html
from voiceover_mage.persistence.manager import DatabaseManager


async def handle_load_npcs(db: DatabaseManager) -> gr.update:
    """
    Load available NPCs on interface startup.

    Args:
        db: Database manager instance

    Returns:
        Gradio update for dropdown component
    """
    npcs = await get_available_npcs(db)
    choices = [npc["display_name"] for npc in npcs]

    # Find Romeo if available, otherwise use first NPC
    default_value = None
    for npc in npcs:
        if npc["name"].lower() == "romeo":
            default_value = npc["display_name"]
            break
    if not default_value and choices:
        default_value = choices[0]

    return gr.update(choices=choices, value=default_value)


async def handle_npc_selection(npc_display_name: str | None, db: DatabaseManager) -> tuple[Any, ...]:
    """
    Handle NPC selection change.

    Args:
        npc_display_name: Display name of selected NPC
        db: Database manager instance

    Returns:
        Tuple of Gradio updates for all UI components
    """
    # Count of all output components (wiki + profile + candidates + dialogue samples)
    # 2 wiki + 1 profile + 3 candidates + (5 samples × 4 components each) = 26 total
    TOTAL_OUTPUTS = 26

    if not npc_display_name:
        return _create_empty_updates()

    # Find NPC ID from display name
    npc_id = await find_npc_id_by_display_name(db, npc_display_name)
    if not npc_id:
        logger.warning(f"Could not find NPC ID for display name: {npc_display_name}")
        return _create_empty_updates()

    # Fetch all data for this NPC
    data = await get_npc_display_data(db, npc_id)

    # Transform data into UI-ready format
    return await _create_populated_updates(data)


def _create_empty_updates() -> tuple[Any, ...]:
    """Create empty updates for all UI components."""
    empty_updates = [
        gr.update(value=""),  # wiki_html
        gr.update(value=""),  # wiki_markdown
        gr.update(value=""),  # profile_html
        gr.update(value=None, label="Candidate 1"),  # candidate1
        gr.update(value=None, label="Candidate 2"),  # candidate2
        gr.update(value=None, label="Candidate 3"),  # candidate3
    ]

    # Add empty updates for dialogue samples (5 samples × 4 components each)
    for _ in range(5):
        empty_updates.extend(
            [
                gr.update(visible=False),  # row
                gr.update(value="", visible=False),  # emotion_md
                gr.update(value=""),  # text_box
                gr.update(value=None),  # audio_player
            ]
        )

    return tuple(empty_updates)


async def _create_populated_updates(data: dict[str, Any]) -> tuple[Any, ...]:
    """
    Create populated updates from NPC data.

    Args:
        data: Dictionary containing NPC data from get_npc_display_data

    Returns:
        Tuple of Gradio updates
    """
    updates = []

    # Wiki HTML (fetch and display)
    wiki_url = get_wiki_url(data.get("npc"))
    wiki_html_content = await fetch_wiki_html(wiki_url)
    updates.append(gr.update(value=wiki_html_content))

    # Wiki markdown text
    wiki_text = extract_wiki_text(data.get("wiki_snapshot"))
    updates.append(gr.update(value=wiki_text))

    # Character profile HTML
    npc = data.get("npc")
    npc_name = npc.name if npc else "Unknown"
    profile_html = transform_character_profile_to_html(
        data.get("character_profile"), data.get("wiki_snapshot"), npc_name
    )
    updates.append(gr.update(value=profile_html))

    # Voice candidates
    selected_preview_id = npc.selected_preview_id if npc else None
    candidates = transform_voice_previews_to_candidates(data.get("voice_previews", []), selected_preview_id, limit=3)

    for i in range(3):
        if i < len(candidates):
            cand = candidates[i]
            updates.append(gr.update(value=cand["audio"], label=cand["label"]))
        else:
            updates.append(gr.update(value=None, label=f"Candidate {i + 1}"))

    # Dialogue samples
    samples = transform_dialogue_samples_to_ui(data.get("dialogue_samples", []))

    for i in range(5):
        if i < len(samples):
            sample = samples[i]
            updates.extend(
                [
                    gr.update(visible=True),  # row
                    gr.update(value=f"**{sample['emotion']}**", visible=True),  # emotion_md
                    gr.update(value=sample["text"]),  # text_box
                    gr.update(value=sample["audio"]),  # audio_player
                ]
            )
        else:
            updates.extend(
                [
                    gr.update(visible=False),  # row
                    gr.update(value="", visible=False),  # emotion_md
                    gr.update(value=""),  # text_box
                    gr.update(value=None),  # audio_player
                ]
            )

    return tuple(updates)

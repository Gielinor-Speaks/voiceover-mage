# ABOUTME: Data transformation utilities for converting database models to UI-ready formats

"""
Utilities for transforming raw database models into UI-ready data structures.
Similar to React's data transformation/selector patterns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from voiceover_mage.persistence.models import (
    NPC,
    CharacterProfile,
    GeneratedDialogue,
    VoicePreview,
    WikiSnapshot,
)
from voiceover_mage.utils.profile_display import render_character_profile_html


def transform_voice_previews_to_candidates(
    voice_previews: list[VoicePreview], selected_preview_id: int | None, limit: int = 3
) -> list[dict[str, Any]]:
    """
    Transform VoicePreview models into UI-ready candidate data.

    Args:
        voice_previews: List of VoicePreview models
        selected_preview_id: ID of the selected preview
        limit: Maximum number of candidates to return

    Returns:
        List of candidate dicts with audio data and selection status
    """
    candidates = []
    for idx, preview in enumerate(voice_previews[:limit], 1):
        audio_data = None
        if preview.audio_bytes and len(preview.audio_bytes) > 0:
            audio_data = preview.audio_bytes
        elif preview.audio_path and Path(preview.audio_path).exists():
            audio_data = str(Path(preview.audio_path).resolve())

        is_selected = preview.id == selected_preview_id
        candidates.append(
            {
                "index": idx,
                "audio": audio_data,
                "is_selected": is_selected,
                "label": f"Candidate {idx}" + (" (Selected)" if is_selected else ""),
            }
        )

    return candidates


def transform_dialogue_samples_to_ui(dialogue_samples: list[GeneratedDialogue]) -> list[dict[str, Any]]:
    """
    Transform GeneratedDialogue models into UI-ready sample data.

    Args:
        dialogue_samples: List of GeneratedDialogue models

    Returns:
        List of sample dicts with text, audio, and emotion labels
    """
    samples = []
    for sample in dialogue_samples:
        # Extract emotion context from metadata
        emotion_label = "Neutral"
        if sample.generation_metadata:
            # Check for animation_id or emotion info
            if "animation_id" in sample.generation_metadata:
                emotion_label = f"Animation ID: {sample.generation_metadata['animation_id']}"
            elif "emotion" in sample.generation_metadata:
                emotion_label = f"Emotion: {sample.generation_metadata['emotion']}"
            elif "emotion_vectors" in sample.generation_metadata:
                emotion_label = "Custom Emotion Vectors"

        samples.append({"text": sample.source_text, "audio": sample.audio_bytes, "emotion": emotion_label})

    return samples


def transform_character_profile_to_html(
    character_profile: CharacterProfile | None, wiki_snapshot: WikiSnapshot | None, npc_name: str
) -> str:
    """
    Transform CharacterProfile into beautiful HTML display.

    Args:
        character_profile: CharacterProfile model (optional)
        wiki_snapshot: WikiSnapshot for fallback image URLs (optional)
        npc_name: Name of the NPC for display

    Returns:
        HTML string for profile display
    """
    if not character_profile or not character_profile.profile_json:
        return "<p style='padding: 20px; color: #666;'>No character profile available</p>"

    profile_data = character_profile.profile_json

    # Get image URLs from wiki_snapshot (NPCDetails doesn't have image URL fields)
    chathead_url = profile_data.chathead_image_url
    image_url = profile_data.image_url
    
    # Render beautiful HTML portfolio layout
    return render_character_profile_html(
        profile=profile_data, chathead_url=chathead_url, image_url=image_url, npc_name=npc_name
    )


def extract_wiki_text(wiki_snapshot: WikiSnapshot | None) -> str:
    """
    Extract wiki markdown text from snapshot.

    Args:
        wiki_snapshot: WikiSnapshot model (optional)

    Returns:
        Raw markdown content or empty string
    """
    if wiki_snapshot and wiki_snapshot.raw_markdown:
        return wiki_snapshot.raw_markdown
    return ""


def get_wiki_url(npc: NPC | None) -> str:
    """
    Get wiki URL from NPC model.

    Args:
        npc: NPC model (optional)

    Returns:
        Wiki URL or empty string
    """
    return npc.wiki_url if (npc and npc.wiki_url) else ""

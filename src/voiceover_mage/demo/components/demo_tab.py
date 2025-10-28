# ABOUTME: Demo tab UI component - main demonstration interface

"""
Demo tab component for showcasing the voice generation pipeline.
Contains NPC selector, wiki data, character profile, voice candidates, and dialogue samples.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from voiceover_mage.demo.constants.html_content import (
    CHARACTER_PROFILE_HEADER,
    DIALOGUE_SAMPLES_HEADER,
    HERO_HEADER,
    PIPELINE_FLOW,
    VOICE_CANDIDATES_HEADER,
    WIKI_SOURCE_DESCRIPTION,
)


def create_demo_tab() -> dict[str, Any]:
    """
    Create the demo tab UI layout.

    Returns:
        Dictionary of Gradio components for event handler binding
    """
    components = {}

    with gr.Column():
        # Hero Header
        gr.HTML(HERO_HEADER)

        # NPC Selection Dropdown
        with gr.Row():
            npc_dropdown = gr.Dropdown(
                label="Select NPC",
                choices=[],
                value=None,
                interactive=True,
            )
            components["npc_dropdown"] = npc_dropdown

        # Pipeline Flow Visualization
        gr.HTML(PIPELINE_FLOW)

        # Wiki Data Section (Collapsible)
        with gr.Accordion(label="📖 Source: OSRS Wiki Article", open=False):
            gr.Markdown(WIKI_SOURCE_DESCRIPTION)
            with gr.Tabs():
                with gr.Tab("Wiki Page"):
                    wiki_html = gr.HTML(
                        value="<p style='padding: 20px; color: #666;'>Select an NPC to load wiki page...</p>",
                    )
                    components["wiki_html"] = wiki_html

                with gr.Tab("Extracted/Crawled Data"):
                    wiki_markdown = gr.Markdown(
                        value="",
                    )
                    components["wiki_markdown"] = wiki_markdown

        # Character Profile Section
        gr.HTML(CHARACTER_PROFILE_HEADER)
        with gr.Accordion(label="View Character Analysis", open=True):
            profile_html = gr.HTML(
                value="<p style='padding: 20px; color: #666;'>Select an NPC to view character profile...</p>",
            )
            components["profile_html"] = profile_html

        # Voice Candidates Section
        gr.HTML(VOICE_CANDIDATES_HEADER)
        with gr.Row():
            candidate1_audio = gr.Audio(label="Candidate 1", interactive=False, show_label=True)
            candidate2_audio = gr.Audio(label="Candidate 2", interactive=False, show_label=True)
            candidate3_audio = gr.Audio(label="Candidate 3", interactive=False, show_label=True)
            components["candidate1_audio"] = candidate1_audio
            components["candidate2_audio"] = candidate2_audio
            components["candidate3_audio"] = candidate3_audio

        # Dialogue Samples Section
        gr.HTML(DIALOGUE_SAMPLES_HEADER)

        # Create 5 sample slots (will be hidden if not used)
        dialogue_components = []
        for _ in range(5):
            with gr.Row(visible=False) as sample_row:
                with gr.Column(scale=3):
                    emotion_md = gr.Markdown("", visible=False)
                    text_box = gr.Textbox(
                        value="",
                        lines=2,
                        max_lines=4,
                        interactive=False,
                        show_copy_button=False,
                        show_label=False,
                    )
                with gr.Column(scale=2):
                    audio_player = gr.Audio(interactive=False, show_label=False)

            dialogue_components.append(
                {"row": sample_row, "emotion_md": emotion_md, "text_box": text_box, "audio_player": audio_player}
            )

        components["dialogue_samples"] = dialogue_components

    return components

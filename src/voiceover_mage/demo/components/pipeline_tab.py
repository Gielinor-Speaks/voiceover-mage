# ABOUTME: Voice Studio tab - unified workflow for creating and managing NPC voices

"""
Streamlined single-page interface for the complete voice creation workflow.
Progressive reveal design - sections appear as they become relevant.
"""

from __future__ import annotations

from typing import Any

import gradio as gr


def create_pipeline_tab() -> dict[str, Any]:
    """
    Create the Voice Studio tab with progressive reveal workflow.

    Returns:
        Dictionary of Gradio components for event handler binding
    """
    components = {}

    with gr.Column():
        # Header
        gr.HTML(
            """
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 36px; margin: 0;">
                    <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                 background-clip: text;">
                        🎨 Voice Studio
                    </span>
                </h1>
                <p style="color: #666; margin-top: 8px; font-size: 16px;">
                    Create and customize character voices
                </p>
            </div>
            """
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Character Selection / Creation
        # ═══════════════════════════════════════════════════════════════
        # with gr.Group(elem_classes="character-selector"):
        gr.HTML(
            """
            <div style="margin-bottom: 20px;">
                <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #f3f4f6;">
                    Character Selection / Creation
                </h2>
                <p style="margin: 8px 0 0 0; font-size: 14px; color: #d1d5db;">
                    Choose an existing character or enter a new NPC ID to begin
                </p>
            </div>
            """
        )

        # Character selection
        npc_dropdown = gr.Dropdown(
            label="🎭 Browse Characters",
            choices=[],
            value=None,
            allow_custom_value=False,
            interactive=True,
            info="Select from NPCs with existing voice data",
            elem_classes="character-dropdown",
        )
        components["npc_dropdown"] = npc_dropdown

        # OR divider
        gr.HTML(
            """
            <div style="text-align: center; margin: 20px 0; position: relative;">
                <div style="position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: rgba(156, 163, 175, 0.3);"></div>
                <span style="position: relative; background: transparent; padding: 0 16px; color: #9ca3af; font-size: 13px; font-weight: 600;">
                    OR
                </span>
            </div>
            """
        )

        # NPC ID input with integrated submit
        npc_input = gr.Textbox(
            label="🆔 Enter NPC ID",
            placeholder="e.g., 815, 2897, 3215... (press Enter to submit)",
            info="Create voice for any OSRS NPC by ID",
            elem_classes="npc-id-input",
        )
        components["npc_input"] = npc_input

        # Pipeline status display
        pipeline_status_html = gr.HTML(
            value="""
            <div style="padding: 20px; background: rgba(156, 163, 175, 0.1); border-radius: 8px; border: 2px dashed rgba(156, 163, 175, 0.3);">
                <p style="text-align: center; color: #9ca3af; margin: 0;">
                    Enter a character ID above and press Enter to begin
                </p>
            </div>
            """
        )
        components["pipeline_status_html"] = pipeline_status_html

        # Action buttons (shown based on status)
        with gr.Row(visible=False) as action_buttons_row:
            with gr.Column(scale=1):
                run_full_btn = gr.Button(
                    "🚀 Run Full Pipeline",
                    variant="primary",
                    size="lg",
                )
                components["run_full_btn"] = run_full_btn

            with gr.Column(scale=1):
                regen_voices_btn_top = gr.Button(
                    "🔄 Regenerate Voices",
                    variant="secondary",
                    size="lg",
                )
                components["regen_voices_btn_top"] = regen_voices_btn_top

        components["action_buttons_row"] = action_buttons_row

        # Live pipeline progress indicator (shown during execution)
        pipeline_progress_html = gr.HTML(
            value="",
            visible=False,
            elem_classes="pipeline-progress"
        )
        components["pipeline_progress_html"] = pipeline_progress_html

        # Results accordion (hidden by default)
        with gr.Accordion("📊 Execution Results", open=False, visible=False) as results_accordion:
            results_html = gr.HTML()
            components["results_html"] = results_html
        components["results_accordion"] = results_accordion

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: Voice Options (shown only when voices exist)
        # ═══════════════════════════════════════════════════════════════
        with gr.Column(visible=False, elem_classes="voice-section") as voice_section:
            gr.HTML(
                """
                <div style="margin: 32px 0 20px 0;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; color: #f3f4f6;">
                        🎭 Voice Options
                    </h3>
                    <p style="color: #d1d5db; margin-top: 6px; font-size: 14px;">
                        Listen to each voice and select your favorite
                    </p>
                </div>
                """
            )

            # Voice candidates grid - clean, spacious layout
            voice_candidates = []

            # Container with proper spacing
            with gr.Column(elem_classes="voice-grid-container"):
                # Create 4 rows of 3 columns each = 12 total slots
                for row_idx in range(4):
                    with gr.Row(equal_height=True):
                        for col_idx in range(3):
                            card_idx = row_idx * 3 + col_idx
                            with gr.Column(scale=1, min_width=280, visible=False) as card_col:
                                # Simple voice card - just audio + button
                                with gr.Group():
                                    # Audio player with label showing selection status
                                    audio = gr.Audio(
                                        label=f"Voice {card_idx + 1}",
                                        interactive=False,
                                        show_label=True,
                                        show_download_button=False,
                                        waveform_options=gr.WaveformOptions(
                                            waveform_color="#667eea",
                                            waveform_progress_color="#764ba2",
                                        ),
                                        elem_id=f"audio-{card_idx}"
                                    )

                                    # Compact selection button directly below
                                    select_btn = gr.Button(
                                        "Use This Voice",
                                        size="sm",
                                        variant="primary",
                                        elem_id=f"select-btn-{card_idx}"
                                    )

                                voice_candidates.append({
                                    "column": card_col,
                                    "audio": audio,
                                    "select_btn": select_btn,
                                })

            components["voice_candidates"] = voice_candidates

            # Actions
            with gr.Row():
                regenerate_btn = gr.Button(
                    "🔄 Generate More Options",
                    variant="secondary",
                )
                components["regenerate_btn"] = regenerate_btn

            voice_status = gr.Textbox(
                label="Voice Status",
                value="",
                interactive=False,
                visible=False,
                elem_classes="voice-status-text",
            )
            components["voice_status"] = voice_status

        components["voice_section"] = voice_section

        # Hidden components for state management
        hidden_npc_id = gr.State(value=None)
        components["hidden_npc_id"] = hidden_npc_id

        hidden_npc_name = gr.State(value=None)
        components["hidden_npc_name"] = hidden_npc_name

    return components

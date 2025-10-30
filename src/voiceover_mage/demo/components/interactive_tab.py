# ABOUTME: Recording Studio tab - real-time voice generation with emotion control and animation support

"""
Recording Studio tab component for user-driven voice generation.
Allows users to generate custom dialogue with selected voices, emotions, and animations.
Mirrors functionality from IndexTTS WebUI with custom styling.
"""

import gradio as gr


def create_interactive_tab() -> dict[str, gr.components.Component]:
    """
    Create the Recording Studio tab UI layout.

    Returns:
        Dictionary mapping component IDs to Gradio components for event handler wiring.
    """
    components = {}

    with gr.Column():
        gr.Markdown("# 🎙️ Recording Studio")
        gr.Markdown(
            "Generate custom voiceovers with full control over emotion, animation, and generation parameters."
        )

        # --- NPC Selection ---
        components["npc_selector"] = gr.Dropdown(
            label="Select NPC",
            choices=[],
            value=None,
            interactive=True,
            info="Only NPCs with selected voices are shown",
        )

        # --- Text Input ---
        with gr.Row():
            with gr.Column(scale=3):
                components["text_input"] = gr.TextArea(
                    label="Text to Speak",
                    placeholder="Enter the dialogue text to generate...",
                    lines=5,
                    max_lines=10,
                )
            with gr.Column(scale=1):
                components["generate_btn"] = gr.Button(
                    "🎤 Generate Speech",
                    variant="primary",
                    size="lg",
                )
                components["save_to_db_checkbox"] = gr.Checkbox(
                    label="Save to Database",
                    value=True,
                    info="Persist generated sample for RuneLite plugin",
                )

        # --- Audio Output ---
        components["audio_output"] = gr.Audio(
            label="Generated Audio",
            type="filepath",
            visible=True,
        )

        components["generation_info"] = gr.Markdown(value="", visible=False)

        # --- Emotion Control ---
        with gr.Accordion("🎭 Emotion Control", open=True):
            components["emotion_mode"] = gr.Radio(
                choices=[
                    "None (Voice Default)",
                    "Text Description",
                    "Manual Control",
                ],
                value="Text Description",
                label="Emotion Mode",
                info="How to control the emotional expression",
            )

            # Text Description Group (visible when Text Description mode selected)
            with gr.Group(visible=True) as components["emotion_description_group"]:
                components["emotion_description"] = gr.Textbox(
                    label="Emotion Description (Optional)",
                    placeholder="e.g., 'speaking while laughing heartily', 'nervous and afraid', 'calm and soothing'",
                    info="Describe how the speech should sound emotionally. Leave blank to infer emotion from the text itself.",
                    lines=2,
                    value="",
                )

            # Manual Emotion Vector (visible when Manual Control mode selected)
            with gr.Group(visible=False) as components["emotion_vector_group"]:
                gr.Markdown("### Manual Emotion Control")

                # Animation preset loader
                with gr.Row():
                    components["animation_preset_selector"] = gr.Dropdown(
                        label="Load Animation Preset",
                        choices=[],
                        value=None,
                        interactive=True,
                        filterable=True,
                        info="Optional: Load emotion values from an OSRS animation (e.g., 'CHATHAP1' or '567')",
                    )
                    components["load_preset_btn"] = gr.Button("📥 Load Preset", size="sm")

                gr.Markdown("_Adjust sliders to manually control emotional expression. Inspired by IndexTTS emotion model._")

                with gr.Row():
                    with gr.Column():
                        components["vec_happy"] = gr.Slider(
                            label="😊 Happy",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_angry"] = gr.Slider(
                            label="😠 Angry",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_sad"] = gr.Slider(
                            label="😢 Sad",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_afraid"] = gr.Slider(
                            label="😨 Afraid",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                    with gr.Column():
                        components["vec_disgusted"] = gr.Slider(
                            label="🤢 Disgusted",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_melancholic"] = gr.Slider(
                            label="😔 Melancholic",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_surprised"] = gr.Slider(
                            label="😲 Surprised",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )
                        components["vec_calm"] = gr.Slider(
                            label="😌 Calm",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.0,
                            step=0.05,
                        )

            # Emotion Weight (visible for non-None modes)
            with gr.Row(visible=True) as components["emotion_weight_row"]:
                components["emotion_weight"] = gr.Slider(
                    label="Emotion Influence Weight",
                    minimum=0.0,
                    maximum=1.0,
                    value=0.6,
                    step=0.01,
                    info="How strongly emotion affects the voice (0.0 = none, 1.0 = maximum)",
                )

        # --- Advanced Generation Parameters ---
        with gr.Accordion("⚙️ Advanced Generation Parameters", open=False):
            gr.Markdown("### GPT Sampling Settings")
            gr.Markdown(
                "_Controls diversity and quality of audio generation. See [HuggingFace Generation Strategies](https://huggingface.co/docs/transformers/main/en/generation_strategies) for details._"
            )

            with gr.Row():
                with gr.Column():
                    components["do_sample"] = gr.Checkbox(
                        label="Enable Sampling",
                        value=True,
                        info="Use probabilistic sampling (recommended)",
                    )
                    components["temperature"] = gr.Slider(
                        label="Temperature",
                        minimum=0.1,
                        maximum=2.0,
                        value=0.8,
                        step=0.1,
                        info="Higher = more random, lower = more deterministic",
                    )

                with gr.Column():
                    components["top_p"] = gr.Slider(
                        label="Top-p (Nucleus Sampling)",
                        minimum=0.0,
                        maximum=1.0,
                        value=0.8,
                        step=0.01,
                        info="Cumulative probability cutoff",
                    )
                    components["top_k"] = gr.Slider(
                        label="Top-k",
                        minimum=0,
                        maximum=100,
                        value=30,
                        step=1,
                        info="Limit to top K tokens (0 = disabled)",
                    )

            with gr.Row():
                components["num_beams"] = gr.Slider(
                    label="Num Beams",
                    minimum=1,
                    maximum=10,
                    value=3,
                    step=1,
                    info="Beam search width (higher = better quality, slower)",
                )
                components["repetition_penalty"] = gr.Slider(
                    label="Repetition Penalty",
                    minimum=0.1,
                    maximum=20.0,
                    value=10.0,
                    step=0.1,
                    info="Penalize repeated tokens",
                )
                components["length_penalty"] = gr.Slider(
                    label="Length Penalty",
                    minimum=-2.0,
                    maximum=2.0,
                    value=0.0,
                    step=0.1,
                    info="Encourage longer/shorter outputs",
                )

            gr.Markdown("### Audio Generation Settings")

            with gr.Row():
                components["max_mel_tokens"] = gr.Slider(
                    label="Max Mel Tokens",
                    minimum=50,
                    maximum=1500,
                    value=1500,
                    step=10,
                    info="Maximum audio length (too low will truncate)",
                )
                components["interval_silence"] = gr.Slider(
                    label="Interval Silence (ms)",
                    minimum=0,
                    maximum=1000,
                    value=200,
                    step=50,
                    info="Pause duration between segments",
                )

            gr.Markdown("### Text Segmentation Settings")

            with gr.Row():
                components["max_text_tokens_per_segment"] = gr.Slider(
                    label="Max Tokens per Segment",
                    minimum=20,
                    maximum=400,
                    value=200,
                    step=10,
                    info="Split long text into chunks (80-200 recommended)",
                )

            with gr.Accordion("📝 Preview Text Segmentation", open=False):
                components["segment_preview"] = gr.Dataframe(
                    headers=["Segment", "Content", "Tokens"],
                    wrap=True,
                    interactive=False,
                )

        # --- Sample History ---
        with gr.Accordion("📚 Sample History", open=False):
            gr.Markdown("### Previously Generated Samples for Selected NPC")
            components["refresh_history_btn"] = gr.Button("🔄 Refresh History")
            components["history_list"] = gr.Dataframe(
                headers=["ID", "Text", "Created", "Animation", "Size (bytes)"],
                wrap=True,
                interactive=False,
            )
            with gr.Row():
                components["selected_history_id"] = gr.Number(
                    label="Sample ID to Load",
                    value=None,
                    precision=0,
                )
                components["load_history_btn"] = gr.Button("▶️ Play Selected Sample")
            components["history_audio"] = gr.Audio(
                label="Loaded Sample",
                type="filepath",
                visible=False,
            )

    return components

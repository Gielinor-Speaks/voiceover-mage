# ABOUTME: Main Gradio application - ties together all demo components

"""
Main application entry point for the Gradio web interface.
Orchestrates components, event handlers, and database initialization.
"""

from __future__ import annotations

import argparse
import asyncio

import gradio as gr
from loguru import logger
from sqlalchemy import select

from voiceover_mage.config import get_config
from voiceover_mage.demo.components.demo_tab import create_demo_tab
from voiceover_mage.demo.components.event_handlers import handle_load_npcs, handle_npc_selection
from voiceover_mage.demo.components.interactive_tab import create_interactive_tab
from voiceover_mage.demo.components.pipeline_tab import create_pipeline_tab
from voiceover_mage.demo.components.studio_handlers import (
    handle_check_status,
    handle_create_voice,
    handle_regenerate_voices,
    handle_select_voice,
)
from voiceover_mage.demo.services.npc_data_service import get_all_npcs_for_pipeline
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import NPC


async def initialize_database(db_path: str | None = None) -> DatabaseManager:
    """
    Initialize database connection and verify connectivity.

    Args:
        db_path: Optional custom database path

    Returns:
        Initialized DatabaseManager instance

    Raises:
        Exception: If database connection fails
    """
    config = get_config()

    db_url = f"sqlite+aiosqlite:///{db_path}" if db_path else config.database_url

    logger.info(f"Connecting to database: {db_url}")

    db = DatabaseManager(db_url)
    await db.create_tables()

    # Test connectivity
    try:
        async with db.async_session() as session:
            result = await session.exec(select(NPC).limit(1))
            result.scalar_one_or_none()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    return db


def create_interface(db: DatabaseManager) -> gr.Blocks:
    """
    Create the main Gradio interface with tabs.

    Args:
        db: Initialized database manager

    Returns:
        Gradio Blocks interface
    """
    # Custom CSS for professional, polished interface
    custom_css = """
    /* ============================================
       VOICE SECTION STYLING
       ============================================ */

    /* Voice section - no border, seamless integration */
    .voice-section {
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
    }

    /* Current character display */
    .current-character-display {
        color: #d1d5db !important;
        font-size: 14px !important;
        margin-bottom: 16px !important;
    }

    .current-character-display strong {
        color: #f3f4f6 !important;
        font-weight: 600 !important;
    }

    /* Voice grid container */
    .voice-grid-container {
        padding: 8px;
        gap: 20px;
    }

    /* Row spacing in voice grid */
    .voice-grid-container .row {
        margin-bottom: 16px !important;
        gap: 16px !important;
    }

    /* Voice card labels - clean, readable styling */
    .voice-grid-container label span {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #374151 !important;
    }

    /* Voice card Group containers */
    .voice-grid-container .form {
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 16px !important;
        background: white !important;
    }

    /* Audio player styling */
    .voice-grid-container audio {
        width: 100% !important;
    }

    /* Voice card buttons - clean styling */
    .voice-grid-container button[id^="select-btn"] {
        font-weight: 500 !important;
        text-transform: none !important;
        margin-top: 8px !important;
        width: 100% !important;
    }

    /* Audio player time labels */
    .voice-grid-container .time {
        font-size: 11px !important;
        color: #6b7280 !important;
        font-weight: 400 !important;
    }

    /* Waveform styling */
    .voice-grid-container canvas {
        border-radius: 4px !important;
    }

    /* Voice status text */
    .voice-status-text label span {
        color: #f3f4f6 !important;
        font-weight: 600 !important;
    }

    .voice-status-text textarea {
        color: #d1d5db !important;
        background: rgba(55, 65, 81, 0.3) !important;
        border-color: rgba(156, 163, 175, 0.3) !important;
    }

    /* ============================================
       CHARACTER SELECTOR IMPROVEMENTS
       ============================================ */

    /* Character selector container */
    .character-selector {
        padding: 24px !important;
        border: 1px solid #374151 !important;
        border-radius: 12px !important;
        background: rgba(55, 65, 81, 0.2) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }

    /* Character dropdown styling */
    .character-dropdown label span {
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #f3f4f6 !important;
        margin-bottom: 8px !important;
    }

    /* NPC ID input styling */
    .npc-id-input label span {
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #f3f4f6 !important;
    }

    .npc-id-input input {
        font-size: 14px !important;
        font-family: 'SF Mono', 'Monaco', 'Consolas', monospace !important;
    }

    /* Info text styling */
    .character-dropdown .info,
    .npc-id-input .info {
        font-size: 13px !important;
        color: #6b7280 !important;
        margin-top: 4px !important;
    }

    /* ============================================
       GENERAL IMPROVEMENTS
       ============================================ */

    /* Status display improvements */
    .status-complete {
        color: #10b981 !important;
        font-weight: 600;
    }
    .status-pending {
        color: #6b7280 !important;
    }

    /* Button styling */
    .primary-action {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
    }

    /* Better default spacing */
    .block {
        margin-bottom: 16px;
    }

    /* Section headers - more breathing room */
    h3 {
        margin-top: 24px !important;
        margin-bottom: 16px !important;
    }

    /* Form inputs - cleaner appearance */
    input[type="text"],
    textarea,
    select {
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }

    input[type="text"]:focus,
    textarea:focus,
    select:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        outline: none !important;
    }

    /* Buttons - consistent styling */
    button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    button:hover {
        transform: translateY(-1px);
    }

    /* Audio players - consistent styling across app */
    audio {
        border-radius: 8px !important;
        margin: 12px 0 !important;
    }
    """

    with gr.Blocks(
        title="Gielinor Speaks - Voice Generation Demo",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as demo:
        with gr.Tabs():
            # Tab 1: Demo Interface
            with gr.Tab("📊 Demo & Review"):
                demo_components = create_demo_tab()

            # Tab 2: Voice Studio
            with gr.Tab("🎨 Voice Studio"):
                pipeline_components = create_pipeline_tab()

            # Tab 3: Interactive Voice Generation (placeholder)
            with gr.Tab("🎤 Interactive (Coming Soon)"):
                create_interactive_tab()

        # Wire up event handlers
        _setup_demo_event_handlers(db, demo_components, demo)
        _setup_pipeline_event_handlers(db, pipeline_components, demo)

    return demo


def _setup_demo_event_handlers(db: DatabaseManager, components: dict, demo: gr.Blocks) -> None:
    """
    Wire up event handlers for the demo tab.

    Args:
        db: Database manager instance
        components: Dictionary of Gradio components
        demo: Main Gradio Blocks instance
    """
    # Build outputs list for NPC selection
    outputs = [
        components["wiki_html"],
        components["wiki_markdown"],
        components["profile_html"],
        components["candidate1_audio"],
        components["candidate2_audio"],
        components["candidate3_audio"],
    ]

    # Add dialogue sample outputs (5 samples × 4 components each)
    for sample_comp in components["dialogue_samples"]:
        outputs.extend(
            [
                sample_comp["row"],
                sample_comp["emotion_md"],
                sample_comp["text_box"],
                sample_comp["audio_player"],
            ]
        )

    # Create wrapper functions that properly await async handlers
    async def on_npc_change(name):
        return await handle_npc_selection(name, db)

    async def on_load():
        return await handle_load_npcs(db)

    # Wire up NPC selection change event
    components["npc_dropdown"].change(
        fn=on_npc_change,
        inputs=[components["npc_dropdown"]],
        outputs=outputs,
    )

    # Load NPCs on startup
    demo.load(
        fn=on_load,
        inputs=[],
        outputs=[components["npc_dropdown"]],
    )


def _setup_pipeline_event_handlers(db: DatabaseManager, components: dict, demo: gr.Blocks) -> None:
    """
    Wire up event handlers for the Voice Studio tab (unified workflow).

    Args:
        db: Database manager instance
        components: Dictionary of Gradio components
        demo: Main Gradio Blocks instance
    """

    # Load NPCs into dropdown on startup
    async def on_load_pipeline_npcs():
        npcs = await get_all_npcs_for_pipeline(db)
        choices = [(f"{npc['display_name']} (ID: {npc['id']})", str(npc['id'])) for npc in npcs]
        return gr.update(choices=choices)

    demo.load(
        fn=on_load_pipeline_npcs,
        inputs=[],
        outputs=[components["npc_dropdown"]],
    )

    # Build outputs list for check status (used by both dropdown and manual input)
    check_status_outputs = [
        components["pipeline_status_html"],
        components["action_buttons_row"],
        components["voice_section"],
    ]
    # Add all 12 voice cards (column and audio for each)
    for card in components["voice_candidates"]:
        check_status_outputs.extend([card["column"], card["audio"]])
    check_status_outputs.extend([components["hidden_npc_id"], components["hidden_npc_name"]])

    # Check status handler (uses either dropdown or manual input)
    async def on_check_status(npc_input):
        result = await handle_check_status(npc_input, db)
        # Unpack: status_html, action_buttons, voice_section, voice_cards_updates(list), npc_id, npc_name
        status_html, action_buttons, voice_section, voice_cards_updates, npc_id, npc_name = result

        # Flatten voice_cards_updates into individual component updates
        flattened_outputs = [status_html, action_buttons, voice_section]
        for card_update in voice_cards_updates:
            flattened_outputs.append(card_update["column"])
            flattened_outputs.append(card_update["audio"])
        flattened_outputs.extend([npc_id, npc_name])

        return flattened_outputs

    # When dropdown changes, update the text input AND auto-submit
    async def on_dropdown_change(selected_id):
        if not selected_id:
            return [""] + [gr.update() for _ in check_status_outputs]

        # Auto-submit when dropdown changes
        result = await handle_check_status(selected_id, db)
        status_html, action_buttons, voice_section, voice_cards_updates, npc_id, npc_name = result

        # Flatten outputs
        flattened_outputs = [selected_id, status_html, action_buttons, voice_section]
        for card_update in voice_cards_updates:
            flattened_outputs.append(card_update["column"])
            flattened_outputs.append(card_update["audio"])
        flattened_outputs.extend([npc_id, npc_name])

        return flattened_outputs

    # Build dropdown change outputs: npc_input + all check_status outputs
    dropdown_outputs = [components["npc_input"]] + check_status_outputs

    components["npc_dropdown"].change(
        fn=on_dropdown_change,
        inputs=[components["npc_dropdown"]],
        outputs=dropdown_outputs,
    )

    # Submit on Enter key in NPC ID input
    components["npc_input"].submit(
        fn=on_check_status,
        inputs=[components["npc_input"]],
        outputs=check_status_outputs,
    )

    # Run full pipeline button
    async def on_run_full(npc_id, progress=gr.Progress()):
        if not npc_id:
            return ("", gr.update(visible=False), gr.update(visible=False),
                    None, None, None, None, None)
        result = await handle_create_voice(str(npc_id), db, progress)
        # Skip the first return value (status_text) since we removed it from UI
        _status, *rest = result
        return tuple(rest)

    components["run_full_btn"].click(
        fn=on_run_full,
        inputs=[components["hidden_npc_id"]],
        outputs=[
            components["results_html"],
            components["results_accordion"],
            components["voice_section"],
            components["voice_candidates"][0]["audio"],
            components["voice_candidates"][1]["audio"],
            components["voice_candidates"][2]["audio"],
            components["hidden_npc_id"],
            components["hidden_npc_name"],
        ],
    )

    # TODO: Wire up other action buttons (regen_wiki_btn, regen_profile_btn, regen_voices_btn_top)

    # Voice selection buttons (all 12 cards)
    for idx, candidate in enumerate(components["voice_candidates"]):

        async def on_select(npc_id, npc_name, candidate_idx=idx):
            result = await handle_select_voice(candidate_idx, npc_id, npc_name, db)
            # Unpack: voice_status, audio_label_updates(list of 12)
            voice_status, audio_label_updates = result
            return [voice_status] + audio_label_updates

        # Build outputs: voice_status, then all 12 audio labels
        select_outputs = [
            components["voice_status"],
        ]
        for card in components["voice_candidates"]:
            select_outputs.append(card["audio"])

        candidate["select_btn"].click(
            fn=on_select,
            inputs=[components["hidden_npc_id"], components["hidden_npc_name"]],
            outputs=select_outputs,
        )

    # Regenerate voices
    async def on_regenerate(npc_id, npc_name, progress=gr.Progress()):
        result = await handle_regenerate_voices(npc_id, npc_name, db, progress)
        # Unpack: voice_status, audio_updates(list of 12)
        voice_status, audio_updates = result
        return [voice_status] + audio_updates

    # Build outputs: voice_status, then all 12 audio components
    regenerate_outputs = [components["voice_status"]]
    for card in components["voice_candidates"]:
        regenerate_outputs.append(card["audio"])

    components["regenerate_btn"].click(
        fn=on_regenerate,
        inputs=[components["hidden_npc_id"], components["hidden_npc_name"]],
        outputs=regenerate_outputs,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Gielinor Speaks Web Interface")
    parser.add_argument("--port", type=int, default=7860, help="Port to run the web interface on (default: 7860)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--db-path", type=str, default=None, help="Path to SQLite database (overrides config)")
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_args()

    # Configure logging
    if args.verbose:
        logger.info("Verbose logging enabled")

    # Initialize database
    logger.info("Initializing database...")
    db = asyncio.run(initialize_database(args.db_path))

    # Create interface
    logger.info("Creating Gradio interface...")
    demo = create_interface(db)

    # Launch
    logger.info(f"Launching web interface at http://{args.host}:{args.port}")
    demo.queue(20).launch(
        server_name=args.host,
        server_port=args.port,
        show_error=True,
    )


if __name__ == "__main__":
    main()

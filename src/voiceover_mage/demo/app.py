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
            result = await session.execute(select(NPC).limit(1))
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
    with gr.Blocks(title="Gielinor Speaks - Voice Generation Demo", theme=gr.themes.Soft()) as demo:
        with gr.Tabs():
            # Tab 1: Demo Interface
            with gr.Tab("Demo & Review"):
                demo_components = create_demo_tab()

            # Tab 2: Interactive Voice Generation (placeholder)
            with gr.Tab("Interactive Voice Generation (Coming Soon)"):
                create_interactive_tab()

        # Wire up event handlers for demo tab
        _setup_demo_event_handlers(db, demo_components, demo)

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
    demo.queue(20).launch(server_name=args.host, server_port=args.port)


if __name__ == "__main__":
    main()

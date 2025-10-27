# ABOUTME: Gradio web interface for demonstrating and testing NPC voice generation
# ABOUTME: Tab 1: Demo interface for conference presentation; Tab 2: Interactive voice generation (TBD)

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

import gradio as gr
import httpx
from loguru import logger
from sqlalchemy import and_, select

from voiceover_mage.config import get_config
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import (
    NPC,
    CharacterProfile,
    GeneratedDialogue,
    VoicePreview,
    WikiSnapshot,
)
from voiceover_mage.utils.profile_display import render_character_profile_html

# ==========================================================================================
# Helper Functions
# ==========================================================================================


async def fetch_wiki_html(wiki_url: str) -> str:
    """
    Fetch the wiki page HTML and extract just the main content with proper styling.

    Removes navigation, sidebars, and applies dark theme fixes.
    """
    if not wiki_url:
        return '<p style="color: #666; padding: 20px;">No wiki URL available</p>'

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(wiki_url)
            response.raise_for_status()

            html = response.text

            # Extract just the main content div
            # The OSRS wiki uses <div class="mw-parser-output"> for the main content
            from html.parser import HTMLParser

            class ContentExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_content = False
                    self.content_html = []
                    self.depth = 0

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "div" and attrs_dict.get("id") == "content":
                        self.in_content = True
                        self.depth = 1
                    elif self.in_content:
                        self.depth += 1
                        attrs_str = " ".join([f'{k}="{v}"' for k, v in attrs])
                        self.content_html.append(f"<{tag} {attrs_str}>")

                def handle_endtag(self, tag):
                    if self.in_content:
                        self.depth -= 1
                        if self.depth == 0:
                            self.in_content = False
                        else:
                            self.content_html.append(f"</{tag}>")

                def handle_data(self, data):
                    if self.in_content and self.depth > 1:
                        self.content_html.append(data)

            parser = ContentExtractor()
            parser.feed(html)
            content = "".join(parser.content_html)

            # Wrap with styling (respects light/dark mode)
            styled_html = f'''
            <style>
                .wiki-container {{
                    font-family: sans-serif;
                    padding: 20px;
                    line-height: 1.6;
                }}
                .wiki-header {{
                    margin-bottom: 15px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid var(--border-color-primary);
                }}
                .wiki-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 14px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: transform 0.2s;
                }}
                .wiki-button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                }}
                .wiki-content a {{
                    color: var(--link-text-color) !important;
                    text-decoration: underline;
                }}
                .wiki-content a:hover {{
                    opacity: 0.8;
                }}
                .wiki-content table {{
                    border-collapse: collapse;
                    margin: 15px 0;
                    border: 1px solid var(--border-color-primary);
                }}
                .wiki-content th, .wiki-content td {{
                    border: 1px solid var(--border-color-primary);
                    padding: 8px;
                }}
                .wiki-content th {{
                    background: var(--background-fill-secondary);
                    font-weight: bold;
                }}
                .wiki-content img {{
                    max-width: 100%;
                    height: auto;
                }}
                .wiki-content .infobox {{
                    float: right;
                    margin: 0 0 10px 10px;
                    background: var(--background-fill-secondary);
                    border: 1px solid var(--border-color-primary);
                    padding: 10px;
                }}
            </style>
            <base href="{wiki_url}" target="_blank">
            <div class="wiki-container">
                <div class="wiki-header">
                    <a href="{wiki_url}" target="_blank" class="wiki-button">
                        🔗 Open on OSRS Wiki
                    </a>
                </div>
                <div class="wiki-content">
                    {content if content else "<p>Could not extract main content</p>"}
                </div>
            </div>
            '''

            return styled_html

    except Exception as e:
        logger.error(f"Failed to fetch wiki page {wiki_url}: {e}")
        return f'''
        <div style="padding: 20px;">
            <p style="color: #ff6b6b; margin-bottom: 15px;">⚠️ Failed to load wiki page: {str(e)}</p>
            <a href="{wiki_url}" target="_blank" style="
                display: inline-block;
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            ">🔗 Open on OSRS Wiki</a>
        </div>
        '''


# ==========================================================================================
# Database Query Functions for Tab 1
# ==========================================================================================


async def get_available_npcs(db: DatabaseManager) -> list[dict[str, Any]]:
    """
    Query NPCs with complete voice profiles suitable for Tab 1 demonstration.

    Returns list of dicts with 'id', 'name', and 'display_name' (name + variant if present).
    """
    async with db.async_session() as session:
        # Query NPCs with complete profiles:
        # - Has wiki snapshot with content
        # - Has character profile
        # - Has selected voice preview
        # - Has at least one dialogue sample
        stmt = (
            select(NPC)
            .join(WikiSnapshot, WikiSnapshot.npc_id == NPC.id)
            .join(CharacterProfile, CharacterProfile.npc_id == NPC.id)
            .where(
                and_(
                    NPC.selected_preview_id.is_not(None),
                    WikiSnapshot.raw_markdown.is_not(None),
                    CharacterProfile.profile_json.is_not(None),
                )
            )
        )

        result = await session.execute(stmt)
        npcs = result.scalars().unique().all()

        # Filter to only those with dialogue samples
        npc_list = []
        for npc in npcs:
            # Check if this NPC has dialogue samples
            dialogue_stmt = select(GeneratedDialogue).where(GeneratedDialogue.npc_id == npc.id).limit(1)
            dialogue_result = await session.execute(dialogue_stmt)
            if dialogue_result.scalar_one_or_none():
                display_name = npc.name
                if npc.variant:
                    display_name = f"{npc.name} ({npc.variant})"
                npc_list.append({"id": npc.id, "name": npc.name, "display_name": display_name})

        # Sort alphabetically by display name
        npc_list.sort(key=lambda x: x["display_name"])
        return npc_list


async def get_npc_display_data(db: DatabaseManager, npc_id: int) -> dict[str, Any]:
    """
    Retrieve all display information for a selected NPC.

    Returns structured dict mapping directly to UI components.
    """
    async with db.async_session() as session:
        # Load NPC with all related data
        stmt = select(NPC).where(NPC.id == npc_id)
        result = await session.execute(stmt)
        npc = result.scalar_one_or_none()

        if not npc:
            return {}

        # Load wiki snapshot
        wiki_stmt = select(WikiSnapshot).where(WikiSnapshot.npc_id == npc_id)
        wiki_result = await session.execute(wiki_stmt)
        wiki_snapshot = wiki_result.scalar_one_or_none()

        # Load character profile
        profile_stmt = select(CharacterProfile).where(CharacterProfile.npc_id == npc_id)
        profile_result = await session.execute(profile_stmt)
        character_profile = profile_result.scalar_one_or_none()

        # Load all voice previews
        preview_stmt = select(VoicePreview).where(VoicePreview.npc_id == npc_id).order_by(VoicePreview.id)
        preview_result = await session.execute(preview_stmt)
        voice_previews = list(preview_result.scalars().all())

        # Load dialogue samples (limit to first 10 for UI)
        dialogue_stmt = (
            select(GeneratedDialogue).where(GeneratedDialogue.npc_id == npc_id).order_by(GeneratedDialogue.id).limit(10)
        )
        dialogue_result = await session.execute(dialogue_stmt)
        dialogue_samples = list(dialogue_result.scalars().all())

        # Extract wiki data text and URL
        wiki_text = ""
        wiki_url = npc.wiki_url if npc else ""
        if wiki_snapshot and wiki_snapshot.raw_markdown:
            wiki_text = wiki_snapshot.raw_markdown  # Show full markdown content

        # Extract character profile data for beautiful HTML display
        profile_display = ""
        if character_profile and character_profile.profile_json:
            profile_data = character_profile.profile_json

            # Get image URLs from profile_json first (more reliable), then fall back to wiki_snapshot
            chathead_url = None
            image_url = None

            # Primary: profile_json
            if hasattr(profile_data, "chathead_image_url"):
                chathead_url = profile_data.chathead_image_url
            if hasattr(profile_data, "image_url"):
                image_url = profile_data.image_url

            # Fallback: wiki_snapshot if profile_json doesn't have images
            if not chathead_url and wiki_snapshot:
                chathead_url = wiki_snapshot.chathead_image_url
            if not image_url and wiki_snapshot:
                image_url = wiki_snapshot.image_url

            # Render beautiful HTML portfolio layout
            profile_display = render_character_profile_html(
                profile=profile_data, chathead_url=chathead_url, image_url=image_url, npc_name=npc.name
            )
        else:
            profile_display = "<p style='padding: 20px; color: #666;'>No character profile available</p>"

        # Process voice candidates with selection status
        candidates = []
        for idx, preview in enumerate(voice_previews[:3], 1):  # Limit to 3 candidates
            audio_data = None
            if preview.audio_bytes:
                audio_data = preview.audio_bytes
            elif preview.audio_path and Path(preview.audio_path).exists():
                audio_data = str(Path(preview.audio_path).resolve())

            is_selected = preview.id == npc.selected_preview_id
            candidates.append(
                {
                    "index": idx,
                    "audio": audio_data,
                    "is_selected": is_selected,
                    "label": f"Candidate {idx}" + (" (Selected)" if is_selected else ""),
                }
            )

        # Process dialogue samples
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

        return {
            "wiki_url": wiki_url,
            "wiki_text": wiki_text,
            "profile_display": profile_display,
            "candidates": candidates,
            "dialogue_samples": samples,
        }


# ==========================================================================================
# Tab 1: Demo Interface UI Components
# ==========================================================================================


def create_tab1_ui(db: DatabaseManager) -> dict[str, Any]:
    """
    Create Tab 1 demo interface UI layout.

    Returns components_dict for event handler binding.
    Must be called within a Gradio context.
    """
    components = {}

    with gr.Column():
        # Header
        gr.HTML(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <h1>Gielinor Speaks: Context-Aware Voice Generation for OSRS</h1>
                <p style="color: #666;">Demonstration of AI-powered NPC voice synthesis with emotion-aware delivery</p>
            </div>
            """
        )

        # NPC Selection
        with gr.Row():
            npc_dropdown = gr.Dropdown(
                label="Select NPC",
                choices=[],
                value=None,
                interactive=True,
            )
            components["npc_dropdown"] = npc_dropdown

        # Pipeline Flow Indicator
        gr.HTML(
            """
            <div style="text-align: center; margin: 30px 0 20px 0; padding: 20px;
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                        border-radius: 10px; border: 2px solid var(--border-color-primary);">
                <div style="display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 24px;">📖</span>
                        <span style="font-weight: bold;">Wiki Data</span>
                    </div>
                    <span style="font-size: 20px; color: #667eea;">→</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 24px;">🧠</span>
                        <span style="font-weight: bold;">AI Analysis</span>
                    </div>
                    <span style="font-size: 20px; color: #764ba2;">→</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 24px;">🎭</span>
                        <span style="font-weight: bold;">Voice Design</span>
                    </div>
                    <span style="font-size: 20px; color: #667eea;">→</span>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 24px;">🎵</span>
                        <span style="font-weight: bold;">Speech Synthesis</span>
                    </div>
                </div>
            </div>
            """
        )

        # Wiki Data Section (Collapsible)
        with gr.Accordion(label="📖 Source: OSRS Wiki Article", open=False):
            gr.Markdown(
                "*This is the raw source material extracted from the OSRS Wiki. "
                "Our AI analyzes this content to understand the character's personality, background, and traits.*"
            )
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

        # Character Profile Section (Hero Card)
        gr.HTML(
            """
            <div style="text-align: center; margin: 30px 0 15px 0;">
                <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
                           justify-content: center; gap: 10px;">
                    <span style="font-size: 32px;">🧠</span>
                    <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                 background-clip: text;">
                        AI-Generated Character Profile
                    </span>
                </h2>
                <p style="color: #666; margin-top: 8px; font-size: 14px;">
                    Personality traits, vocal characteristics, and speaking style inferred from wiki content
                </p>
            </div>
            """
        )
        with gr.Accordion(label="View Character Analysis", open=True):
            profile_html = gr.HTML(
                value="<p style='padding: 20px; color: #666;'>Select an NPC to view character profile...</p>",
            )
            components["profile_html"] = profile_html

        # Voice Candidates Section
        gr.HTML(
            """
            <div style="text-align: center; margin: 40px 0 15px 0;">
                <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
                           justify-content: center; gap: 10px;">
                    <span style="font-size: 32px;">🎭</span>
                    <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                 background-clip: text;">
                        Voice Design Candidates
                    </span>
                </h2>
                <p style="color: #666; margin-top: 8px; font-size: 14px;">
                    ElevenLabs Voice Design generates multiple voice options based on character traits
                </p>
            </div>
            """
        )
        with gr.Row():
            candidate1_audio = gr.Audio(label="Candidate 1", interactive=False, show_label=True)
            candidate2_audio = gr.Audio(label="Candidate 2", interactive=False, show_label=True)
            candidate3_audio = gr.Audio(label="Candidate 3", interactive=False, show_label=True)
            components["candidate1_audio"] = candidate1_audio
            components["candidate2_audio"] = candidate2_audio
            components["candidate3_audio"] = candidate3_audio

        # Dialogue Samples Section
        gr.HTML(
            """
            <div style="text-align: center; margin: 40px 0 15px 0;">
                <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
                           justify-content: center; gap: 10px;">
                    <span style="font-size: 32px;">🎵</span>
                    <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                 background-clip: text;">
                        Emotion-Aware Speech Synthesis
                    </span>
                </h2>
                <p style="color: #666; margin-top: 8px; font-size: 14px;">
                    Context-aware dialogue generation with dynamic emotional expression
                </p>
            </div>
            """
        )

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


# ==========================================================================================
# Tab 1: Event Handlers
# ==========================================================================================


def create_tab1_event_handlers(db: DatabaseManager, components: dict[str, Any], demo: gr.Blocks) -> None:
    """
    Wire up event handlers for Tab 1 components.
    """

    async def on_load():
        """Load available NPCs on interface startup."""
        npcs = await get_available_npcs(db)
        choices = [npc["display_name"] for npc in npcs]
        # Find Romeo if available
        default_value = None
        for npc in npcs:
            if npc["name"].lower() == "romeo":
                default_value = npc["display_name"]
                break
        if not default_value and choices:
            default_value = choices[0]

        return gr.update(choices=choices, value=default_value)

    async def on_npc_select(npc_display_name: str | None):
        """Handle NPC selection change."""
        if not npc_display_name:
            # Return empty updates
            empty_updates = [
                gr.update(value=""),  # wiki iframe
                gr.update(value=""),  # wiki markdown
                gr.update(value=""),  # profile
                gr.update(value=None, label="Candidate 1"),  # candidate1
                gr.update(value=None, label="Candidate 2"),  # candidate2
                gr.update(value=None, label="Candidate 3"),  # candidate3
            ]
            # Add empty updates for dialogue samples (5 samples x 4 components each)
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

        # Find NPC ID from display name
        npcs = await get_available_npcs(db)
        npc_id = None
        for npc in npcs:
            if npc["display_name"] == npc_display_name:
                npc_id = npc["id"]
                break

        if not npc_id:
            logger.warning(f"Could not find NPC ID for display name: {npc_display_name}")
            return tuple(
                [gr.update()] * (6 + 5 * 4)
            )  # Return empty updates (3 wiki components + 3 candidates + 5*4 dialogue)

        # Fetch display data
        data = await get_npc_display_data(db, npc_id)

        updates = []

        # Fetch and display wiki HTML (content only, dark theme)
        wiki_url = data.get("wiki_url", "")
        wiki_html_content = await fetch_wiki_html(wiki_url)
        updates.append(gr.update(value=wiki_html_content))

        # Wiki text (as markdown)
        updates.append(gr.update(value=data.get("wiki_text", "")))

        # Character profile (as markdown)
        updates.append(gr.update(value=data.get("profile_display", "")))

        # Voice candidates (3)
        candidates = data.get("candidates", [])
        for i in range(3):
            if i < len(candidates):
                cand = candidates[i]
                updates.append(gr.update(value=cand["audio"], label=cand["label"]))
            else:
                updates.append(gr.update(value=None, label=f"Candidate {i + 1}"))

        # Dialogue samples (5 slots)
        samples = data.get("dialogue_samples", [])
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

    # Build outputs list
    outputs = [
        components["wiki_html"],
        components["wiki_markdown"],
        components["profile_html"],
        components["candidate1_audio"],
        components["candidate2_audio"],
        components["candidate3_audio"],
    ]

    # Add dialogue sample outputs (5 samples x 4 components)
    for sample_comp in components["dialogue_samples"]:
        outputs.extend(
            [
                sample_comp["row"],
                sample_comp["emotion_md"],
                sample_comp["text_box"],
                sample_comp["audio_player"],
            ]
        )

    # Wire up events
    components["npc_dropdown"].change(
        fn=on_npc_select,
        inputs=[components["npc_dropdown"]],
        outputs=outputs,
    )

    # Load NPCs on startup
    demo.load(
        fn=on_load,
        inputs=[],
        outputs=[components["npc_dropdown"]],
    )


# ==========================================================================================
# Main Interface Construction
# ==========================================================================================


def create_interface(db: DatabaseManager) -> gr.Blocks:
    """
    Create the main Gradio interface with tabs.
    """
    with gr.Blocks(title="Gielinor Speaks - Voice Generation Demo", theme=gr.themes.Soft()) as demo:
        with gr.Tabs():
            # Tab 1: Demo Interface
            with gr.Tab("Demo & Review"):
                tab1_components = create_tab1_ui(db)

            # Tab 2: Interactive Voice Generation (placeholder for now)
            with gr.Tab("Interactive Voice Generation (Coming Soon)"):
                gr.Markdown("# Interactive Voice Generation\n\nThis tab will be implemented in the next phase.")

        # Wire up Tab 1 event handlers
        create_tab1_event_handlers(db, tab1_components, demo)

    return demo


# ==========================================================================================
# Command-Line Entry Point
# ==========================================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Gielinor Speaks Web Interface")
    parser.add_argument("--port", type=int, default=7860, help="Port to run the web interface on (default: 7860)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--db-path", type=str, default=None, help="Path to SQLite database (overrides config)")
    return parser.parse_args()


async def initialize_database(db_path: str | None = None) -> DatabaseManager:
    """Initialize database connection and verify connectivity."""
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


def main():
    """Main entry point."""
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

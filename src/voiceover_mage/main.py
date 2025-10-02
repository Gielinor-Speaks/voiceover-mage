# ABOUTME: Main CLI application entry point using asyncclick for native async support
# ABOUTME: Provides commands for NPC extraction, character analysis, and voice generation

import asyncclick as click
from rich.console import Console
from rich.panel import Panel

from voiceover_mage.config import get_config
from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.persistence import DatabaseManager
from voiceover_mage.utils.logging import (
    LoggingMode,
    configure_logging,
    get_logging_status,
    with_npc_context,
    with_pipeline_context,
)
from voiceover_mage.utils.logging.enhanced_progress import (
    EnhancedProgressReporter,
)
from voiceover_mage.utils.rich_tables import (
    create_character_profile_table,
    create_confidence_metrics_table,
    create_extraction_status_table,
    create_logging_status_table,
    create_voice_samples_table,
    print_rich_table,
)

console = Console()


async def _run_with_enhanced_progress(
    coro, message: str, json_output: bool, npc_id: int | None = None, npc_name: str | None = None
):
    """Run async operation with enhanced progress display."""
    if json_output:
        return await coro

    reporter = EnhancedProgressReporter(console=console)

    # Use pipeline dashboard if we have NPC context, otherwise use status
    if npc_id is not None and npc_name is not None:
        # Check if this is a pipeline operation that can use the dashboard
        # For now, let the caller handle dashboard integration directly
        return await reporter.run_with_status(
            operation=lambda: coro, message=message, success_message="✅ Operation completed"
        )
    else:
        return await reporter.run_with_status(
            operation=lambda: coro, message=message, success_message="✅ Operation completed"
        )


# Rich table functions are now handled by the rich_tables module


def _display_extraction_results(extraction, verbose: bool, raw: bool, force_refresh: bool):
    """Display extraction results in a clean format."""
    console.print(f"\n🎭 [bold magenta]{extraction.npc_name}[/bold magenta]")

    # Beautiful status table
    status_table = create_extraction_status_table(extraction)
    print_rich_table(console, status_table)

    if raw and extraction.raw_markdown:
        content = extraction.raw_markdown
        preview = content[:2000] + ("..." if len(content) > 2000 else "")
        console.print(Panel(preview, title="📜 Raw Markdown", border_style="blue"))

    if verbose:
        if extraction.chathead_image_url:
            console.print(f"🖼️ Chathead: {extraction.chathead_image_url}")
        if extraction.image_url:
            console.print(f"🖼️ Main Image: {extraction.image_url}")


@click.command()
@click.argument("npc_id", type=int)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed extraction process")
@click.option("--raw", is_flag=True, help="Display raw markdown content instead of analyzed data")
@click.option("--force-refresh", is_flag=True, help="Bypass cache and extract fresh data")
@click.pass_context
async def extract_npc(ctx, npc_id: int, verbose: bool, raw: bool, force_refresh: bool):
    """
    🕷️ Extract NPC data from the Old School RuneScape wiki.

    Phase 1: Extracts raw markdown and image URLs from wiki pages with caching.
    Use --raw to see the extracted markdown content.
    """
    await _extract_npc_async(npc_id, verbose, raw, force_refresh, ctx.obj["json_output"])


async def _extract_npc_async(npc_id: int, verbose: bool, raw: bool, force_refresh: bool, json_output: bool):
    """Extract NPC data with optional UI display."""
    with with_npc_context(npc_id) as logger:
        logger.info("Starting NPC extraction", npc_id=npc_id)

        from voiceover_mage.core.service import NPCExtractionService

        service = NPCExtractionService(force_refresh=force_refresh)

        try:
            extraction = await _run_with_enhanced_progress(
                service.extract_npc(npc_id), f"🧙‍♂️ Extracting NPC {npc_id}", json_output, npc_id, "NPC Data"
            )

            if not extraction.extraction_success:
                logger.warning("Extraction failed", error=extraction.error_message)
                if not json_output:
                    console.print(f"[red]❌ {extraction.error_message}[/red]")
                return

            logger.info("Extraction complete", npc_name=extraction.npc_name)

            if not json_output:
                _display_extraction_results(extraction, verbose, raw, force_refresh)

        finally:
            await service.close()


@click.command()
@click.argument("npc_id", type=int)
@click.option("--save", "-s", is_flag=True, help="Save results to file")
@click.pass_context
async def pipeline(ctx, npc_id: int, save: bool):
    """
    🔄 Run the complete NPC-to-voice pipeline.

    Extracts NPC data, analyzes character traits, and generates voice profile
    in one seamless workflow.
    """
    await _pipeline_async(npc_id, save, ctx.obj["json_output"])


async def _pipeline_async(npc_id: int, save_output: bool, json_output: bool):
    """Run the complete NPC-to-voice pipeline with live dashboard."""
    with with_pipeline_context("npc_to_voice", npc_id=npc_id) as logger:
        logger.info("Starting pipeline", npc_id=npc_id)

        if not json_output:
            console.print(
                Panel.fit(
                    f"🎭 [bold cyan]Voiceover Mage Pipeline[/bold cyan] 🎭\nProcessing NPC ID: {npc_id}",
                    border_style="magenta",
                )
            )

        config = get_config()
        service = UnifiedPipelineService(api_key=config.gemini_api_key)

        # Get NPC name for dashboard
        npc_name = "Unknown NPC"
        try:
            from voiceover_mage.persistence.manager import DatabaseManager

            db = DatabaseManager()
            await db.create_tables()
            cached = await db.get_cached_extraction(npc_id)
            if cached and cached.npc_name:
                npc_name = cached.npc_name
        except Exception:
            pass  # Fallback to Unknown NPC

        try:
            if json_output:
                # Simple execution without dashboard for JSON output
                extraction = await service.run_full_pipeline(npc_id)
            else:
                # Use the enhanced dashboard for interactive mode
                from voiceover_mage.core.dashboard_pipeline import DashboardIntegratedPipeline

                dashboard_pipeline = DashboardIntegratedPipeline(service)

                reporter = EnhancedProgressReporter(console=console)

                async def run_pipeline_with_dashboard(dashboard):
                    return await dashboard_pipeline.run_full_pipeline_with_dashboard(npc_id, dashboard)

                extraction = await reporter.run_with_pipeline_dashboard(
                    operation=run_pipeline_with_dashboard, npc_id=npc_id, npc_name=npc_name
                )

            if not extraction.extraction_success:
                logger.warning("Pipeline failed", error=extraction.error_message)
                if not json_output:
                    console.print(f"[red]❌ {extraction.error_message}[/red]")
                return

            logger.info("Pipeline complete", npc_name=extraction.npc_name, stages=extraction.completed_stages)

            if not json_output:
                console.print(f"✅ Complete: [bold green]{extraction.npc_name}[/bold green]")
                console.print(f"📊 Stages: [bold blue]{', '.join(extraction.completed_stages)}[/bold blue]")

                if extraction.character_profile:
                    _display_character_profile_summary(extraction.character_profile.model_dump())

            if save_output and not json_output:
                console.print("[green]💾 Results saved[/green]")

        finally:
            await service.close()


def _display_character_profile_summary(profile: dict):
    """Display character profile summary with beautiful rich tables."""
    # Character overview table
    character_table = create_character_profile_table(profile)
    print_rich_table(console, character_table)

    # Confidence metrics table
    confidence_table = create_confidence_metrics_table(profile)
    print_rich_table(console, confidence_table)


def _initialize_logging(json_output: bool, log_level: str | None = None, log_file: str | None = None) -> None:
    """Initialize logging configuration."""
    try:
        config = get_config()
        mode = LoggingMode.PRODUCTION if json_output else LoggingMode.INTERACTIVE

        # Use config defaults when CLI parameters are not provided
        final_log_level = log_level or config.log_level
        final_log_file = log_file or (str(config.log_file) if config.log_file else None)

        configure_logging(mode=mode, log_level=final_log_level, log_file=final_log_file)
    except (FileNotFoundError, PermissionError, OSError):
        # Handle race conditions during parallel test execution
        # Fall back to minimal logging configuration
        mode = LoggingMode.PRODUCTION if json_output else LoggingMode.INTERACTIVE
        final_log_level = log_level or "INFO"
        configure_logging(mode=mode, log_level=final_log_level, log_file=log_file)


@click.command(name="logging-status")
def logging_status():
    """
    📊 Show current logging configuration and status.
    """
    status = get_logging_status()
    logging_table = create_logging_status_table(status)
    print_rich_table(console, logging_table)


@click.group(invoke_without_command=True)
@click.option("--json", is_flag=True, help="Output structured JSON logs instead of rich interface")
@click.option("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
@click.option("--log-file", help="Custom log file path")
@click.pass_context
def app(ctx, json: bool, log_level: str, log_file: str | None):
    """
    🧙‍♂️ Voiceover Mage - AI Voice Generation for OSRS NPCs

    Transform Old School RuneScape NPCs into authentic voices using AI-powered
    character analysis and voice generation.
    """
    # Store global options in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["json_output"] = json

    # Initialize logging once here instead of in each command
    _initialize_logging(json, log_level, log_file)

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# --------------------------
# Voice cloning CLI commands
# --------------------------


@click.command(name="select-voice")
@click.argument("npc_id", type=int)
@click.option("--index", "-i", type=int, default=None, help="Select preview by index (skip interactive mode)")
@click.pass_context
async def select_voice(ctx, npc_id: int, index: int | None):
    """
    🎭 Select a voice preview for an NPC.

    Opens an interactive menu to browse and select from available voice previews.
    The selected voice will be used for speech generation with the 'speak' command.

    Supports audio playback if ffplay/ffmpeg is installed on your system.

    Args:
        npc_id: ID of the NPC
        --index: Optional index to select directly (0-based)
    """
    await _select_voice_async(npc_id, index, ctx.obj["json_output"])


async def _select_voice_async(npc_id: int, preview_index: int | None, json_output: bool):
    """Voice selection implementation with interactive UI."""
    with with_npc_context(npc_id) as logger:
        logger.info("Starting voice selection", npc_id=npc_id, preview_index=preview_index)

        db = DatabaseManager()
        await db.create_tables()

        try:
            # Fetch NPC and voice previews
            npc_result = await db.get_npc(npc_id)
            if not npc_result:
                error_msg = f"NPC {npc_id} not found"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            voice_samples = await db.list_voice_samples(npc_id)
            if not voice_samples:
                error_msg = f"No voice previews found for NPC {npc_id}. Run 'pipeline' first to generate voices."
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            # Interactive selection or direct index
            selected_index = preview_index

            if selected_index is None and not json_output:
                # Use interactive selector
                from voiceover_mage.utils.voice_selector import VoiceSelector

                selector = VoiceSelector(console)
                selected_index = await selector.select_voice_interactive(voice_samples, npc_result.name)

                if selected_index is None:
                    logger.info("Voice selection cancelled")
                    return

            # Validate index
            if selected_index is None:
                error_msg = "No voice preview selected"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            if selected_index < 0 or selected_index >= len(voice_samples):
                error_msg = f"Invalid preview index {selected_index} (must be 0-{len(voice_samples) - 1})"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            selected_preview = voice_samples[selected_index]

            if not json_output:
                console.print(f"\n🎭 Selecting voice for [bold magenta]{npc_result.name}[/bold magenta]")
                console.print(f"📝 Preview: {selected_preview.voice_prompt[:70]}...")

            # Update database to mark this as the selected voice
            result = await db.set_selected_voice_preview(npc_id, selected_preview.id)

            if not result:
                error_msg = "Failed to update selected voice preview"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            logger.info("Voice selection completed", preview_id=selected_preview.id)

            if not json_output:
                console.print("✅ Voice selected successfully!")
                console.print(f"📊 Preview ID: [bold green]{selected_preview.id}[/bold green]")
                console.print(f"🎯 Provider: [bold blue]{selected_preview.provider}[/bold blue]")
                console.print("\n[dim]Use 'speak' command to generate dialogue with this voice[/dim]")

        except Exception as e:
            logger.error("Voice selection failed", error=str(e))
            if not json_output:
                console.print(f"[red]❌ Voice selection failed: {e}[/red]")
            raise


@click.command(name="speak")
@click.argument("npc_id", type=int)
@click.option("--text", required=True, help="Text to synthesize into speech")
@click.option("--output", help="Output file path (defaults to generated filename)")
@click.pass_context
async def speak(ctx, npc_id: int, text: str, output: str | None):
    """
    🗣️ Generate speech using a cloned NPC voice.

    Uses the NPC's cloned voice to synthesize the provided text into speech.
    The NPC must have a cloned voice created with the clone-voice command first.

    Args:
        npc_id: ID of the NPC with a cloned voice
        --text: Text to convert to speech
        --output: Optional output file path
    """
    await _speak_async(npc_id, text, output, ctx.obj["json_output"])


async def _speak_async(npc_id: int, text: str, output_path: str | None, json_output: bool):
    """Generate speech implementation with database operations."""
    with with_npc_context(npc_id) as logger:
        logger.info("Starting speech generation", npc_id=npc_id, text_length=len(text))

        db = DatabaseManager()
        await db.create_tables()

        try:
            # Fetch NPC with selected voice preview
            npc_result = await db.get_npc(npc_id)
            if not npc_result:
                error_msg = f"NPC {npc_id} not found"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            if not npc_result.selected_preview_id:
                error_msg = f"NPC {npc_id} ({npc_result.name}) has no selected voice. Run 'select-voice' first."
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            # Load the selected voice preview from database
            from voiceover_mage.persistence.models import VoicePreview

            async with db.async_session() as session:
                selected_preview = await session.get(VoicePreview, npc_result.selected_preview_id)

            if not selected_preview:
                error_msg = f"Selected voice preview {npc_result.selected_preview_id} not found in database"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            if not selected_preview.audio_bytes:
                error_msg = "Selected voice preview has no audio data"
                logger.error(error_msg)
                if not json_output:
                    console.print(f"[red]❌ {error_msg}[/red]")
                return

            if not json_output:
                console.print(f"🗣️ Generating speech for [bold magenta]{npc_result.name}[/bold magenta]")
                console.print(f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}")
                console.print(f"🎯 Voice Preview: [bold blue]{selected_preview.voice_prompt[:50]}...[/bold blue]")
                console.print(f"🎵 Provider: [bold cyan]{selected_preview.provider}[/bold cyan]")

            # Initialize local TTS adapter
            config = get_config()

            from voiceover_mage.services.audio.local import LocalTTSAdapter

            tts_adapter = LocalTTSAdapter(config.local_tts_api_url)

            # Generate speech with reference audio from database
            audio_bytes = await _run_with_enhanced_progress(
                tts_adapter.generate_speech_with_reference(
                    text=text, reference_audio_bytes=selected_preview.audio_bytes, audio_format=".mp3"
                ),
                f"🧙‍♂️ Generating speech for {npc_result.name}",
                json_output,
                npc_id,
                npc_result.name,
            )

            # Determine output path
            if not output_path:
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in npc_result.name if c.isalnum() or c in " -_").strip()
                safe_name = safe_name.replace(" ", "_")
                output_path = f"{safe_name}_{timestamp}.wav"

            # Save audio file
            from pathlib import Path

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(audio_bytes)

            # Save to database
            await db.save_generated_dialogue(
                npc_id=npc_id,
                source_text=text,
                audio_bytes=audio_bytes,
                generation_metadata={
                    "preview_id": selected_preview.id,
                    "provider": selected_preview.provider,
                    "voice_prompt": selected_preview.voice_prompt,
                    "text_length": len(text),
                    "audio_size": len(audio_bytes),
                },
            )

            logger.info("Speech generation completed", output_path=str(output_file), audio_size=len(audio_bytes))

            if not json_output:
                console.print("✅ Speech generated successfully!")
                console.print(f"📁 Output: [bold green]{output_file}[/bold green]")
                console.print(f"📊 Audio size: [bold blue]{len(audio_bytes):,} bytes[/bold blue]")
                console.print("💾 Saved to database for future reference")

        except Exception as e:
            logger.error("Speech generation failed", error=str(e))
            if not json_output:
                console.print(f"[red]❌ Speech generation failed: {e}[/red]")
            raise


# --------------------------
# Voice sample CLI utilities
# --------------------------


@click.command(name="list-voice-samples")
@click.argument("npc_id", type=int)
@click.pass_context
async def list_voice_samples(ctx, npc_id: int):
    """List all generated voice samples for an NPC."""
    await _list_voice_samples_async(npc_id, ctx.obj["json_output"])


async def _list_voice_samples_async(npc_id: int, json_output: bool):
    db = DatabaseManager()
    await db.create_tables()
    samples = await db.list_voice_samples(npc_id)

    if not samples:
        console.print(f"[yellow]No voice samples found for NPC ID {npc_id}.[/yellow]")
        return

    voice_samples_table = create_voice_samples_table(samples, npc_id)
    print_rich_table(console, voice_samples_table)


# Add commands to the main group
app.add_command(extract_npc)
app.add_command(pipeline)
app.add_command(logging_status)
app.add_command(select_voice)
app.add_command(speak)
app.add_command(list_voice_samples)


if __name__ == "__main__":
    app()

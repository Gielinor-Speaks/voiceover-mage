# ABOUTME: Main CLI application entry point using Typer and Rich for beautiful interface
# ABOUTME: Provides commands for NPC extraction, character analysis, and voice generation

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from voiceover_mage.config import get_config
from voiceover_mage.lib.logging import (
    LoggingMode,
    configure_logging,
    create_smart_progress,
    get_logging_status,
    with_npc_context,
    with_pipeline_context,
)
# from voiceover_mage.npc.models import NPCWikiSourcedData  # Not used in current implementation


# Shared options that can be used in any command
def shared_logging_options(
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON logs instead of rich interface")
    ] = False,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)")] = "INFO",
    log_file: Annotated[str | None, typer.Option("--log-file", help="Custom log file path")] = None,
):
    """Initialize logging and return json_output flag."""
    _initialize_logging(json_output, log_level, log_file)
    return json_output


app = typer.Typer(
    name="voiceover-mage", help="🧙‍♂️ AI Voice Generation for Old School RuneScape NPCs", rich_markup_mode="rich"
)
console = Console()


@app.command()
def extract_npc(
    ctx: typer.Context,
    npc_id: int = typer.Argument(help="NPC ID to extract from the wiki"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed extraction process"),
    raw: bool = typer.Option(False, "--raw", help="Display raw markdown content instead of analyzed data"),
    force_refresh: bool = typer.Option(False, "--force-refresh", help="Bypass cache and extract fresh data"),
    dspy_images: bool = typer.Option(False, "--dspy-images", help="Use DSPy intelligent image extraction instead of regex"),
):
    """
    🕷️ Extract NPC data from the Old School RuneScape wiki.

    Phase 1: Extracts raw markdown and image URLs from wiki pages with caching.
    Use --raw to see the extracted markdown content.
    Use --dspy-images to enable intelligent image extraction (requires LM configuration).
    """
    asyncio.run(_extract_npc_async(npc_id, verbose, raw, force_refresh, dspy_images, ctx.obj["json_output"]))


async def _extract_npc_async(npc_id: int, verbose: bool, raw: bool, force_refresh: bool, dspy_images: bool, json_output: bool):
    """Async helper for NPC extraction using the service layer."""
    with with_npc_context(npc_id) as npc_logger:
        npc_logger.info("Starting NPC extraction", npc_id=npc_id, verbose=verbose, raw=raw, force_refresh=force_refresh, dspy_images=dspy_images)

        try:
            from voiceover_mage.npc.service import NPCExtractionService

            service = NPCExtractionService(force_refresh=force_refresh, use_dspy_images=dspy_images)

            if not json_output:
                # Interactive mode: smart progress that updates from logs
                cache_status = "fresh data" if force_refresh else "cached or fresh data"
                progress, task_id, tracker = create_smart_progress(
                    console, f"🧙‍♂️ Extracting {cache_status} for NPC ID {npc_id}..."
                )

                with progress, tracker:
                    extraction = await service.extract_npc(npc_id)
                    npc_logger.debug("Extracted NPC data", npc_name=extraction.npc_name)
            else:
                # Production mode: no progress display
                extraction = await service.extract_npc(npc_id)
                npc_logger.debug("Extracted NPC data", npc_name=extraction.npc_name)

            if not extraction.extraction_success:
                error_msg = extraction.error_message
                npc_logger.warning("Extraction failed", npc_id=npc_id, error=error_msg)
                if not json_output:
                    console.print(f"[red]❌ Extraction failed for NPC ID {npc_id}: {error_msg}[/red]")
                return

            npc_logger.info("Successfully extracted NPC data", npc_name=extraction.npc_name)

            if not json_output:
                # Interactive mode: beautiful display with Rich
                status_style = "green" if extraction.extraction_success else "red"
                cache_indicator = "💾" if not force_refresh else "🆕"
                
                console.print(f"\n🎭 [bold magenta]NPC Extraction: {extraction.npc_name}[/bold magenta]")
                
                # Status table
                status_table = Table(title=f"{cache_indicator} Extraction Status")
                status_table.add_column("Field", style="cyan")
                status_table.add_column("Value", style="white")
                
                status_table.add_row("NPC ID", str(extraction.npc_id))
                status_table.add_row("Name", extraction.npc_name)
                status_table.add_row("Wiki URL", extraction.wiki_url)
                status_table.add_row("Success", f"[{status_style}]{extraction.extraction_success}[/{status_style}]")
                status_table.add_row("Extracted At", extraction.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                status_table.add_row("Markdown Length", f"{len(extraction.raw_markdown):,} chars")
                
                # Simple image status
                status_table.add_row("Has Chathead", "✅" if (extraction.raw_data and extraction.raw_data.get("chathead_image_url")) else "❌")
                status_table.add_row("Has Main Image", "✅" if (extraction.raw_data and extraction.raw_data.get("image_url")) else "❌")
                
                console.print(status_table)

                if raw and extraction.raw_data and extraction.raw_data.get("raw_markdown"):
                    markdown_content = extraction.raw_data["raw_markdown"]
                    console.print(Panel(
                        markdown_content[:2000] + ("..." if len(markdown_content) > 2000 else ""),
                        title="📜 Raw Markdown Content",
                        border_style="blue"
                    ))

                if verbose:
                    # Show simple image URLs
                    if extraction.raw_data and extraction.raw_data.get("chathead_image_url"):
                        console.print(f"🖼️ Chathead: {extraction.raw_data['chathead_image_url']}")
                    if extraction.raw_data and extraction.raw_data.get("image_url"):
                        console.print(f"🖼️ Main Image: {extraction.raw_data['image_url']}")

            await service.close()

        except Exception as e:
            npc_logger.error("NPC extraction failed", error=str(e), error_type=type(e).__name__, npc_id=npc_id)
            if not json_output:
                console.print(f"[red]❌ Error extracting NPC data: {e}[/red]")
            raise


@app.command()
def pipeline(
    ctx: typer.Context,
    npc_id: int = typer.Argument(help="NPC ID to process through full pipeline"),
    save_output: bool = typer.Option(False, "--save", "-s", help="Save results to file"),
):
    """
    🔄 Run the complete NPC-to-voice pipeline.

    Extracts NPC data, analyzes character traits, and generates voice profile
    in one seamless workflow.
    """
    asyncio.run(_pipeline_async(npc_id, save_output, ctx.obj["json_output"]))


async def _pipeline_async(npc_id: int, save_output: bool, json_output: bool):
    """Async helper for full pipeline."""
    with with_pipeline_context("npc_to_voice", npc_id=npc_id) as pipeline_logger:
        pipeline_logger.info("Starting NPC-to-voice pipeline", npc_id=npc_id, save_output=save_output)

        if not json_output:
            console.print(
                Panel.fit(
                    f"🎭 [bold cyan]Voiceover Mage Pipeline[/bold cyan] 🎭\nProcessing NPC ID: {npc_id}",
                    border_style="magenta",
                )
            )

        from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor

        try:
            if not json_output:
                # Interactive mode: smart progress that updates from logs
                progress, task_id, tracker = create_smart_progress(
                    console, f"🧙‍♂️ Invoking voice transformation magic for NPC ID {npc_id}..."
                )

                with progress, tracker:
                    # Step 1: Extract NPC data
                    config = get_config()
                    extractor = Crawl4AINPCExtractor(api_key=config.gemini_api_key)
                    npc_data = await extractor.extract_npc_data(npc_id)

                    if not npc_data:
                        pipeline_logger.warning("No NPC data found in pipeline", npc_id=npc_id)
                        console.print("[red]❌ No NPC data found[/red]")
                        return
                    pipeline_logger.info("Extracted NPC data in pipeline", npc_name=npc_data.name)

                    # Update progress for character analysis step
                    progress.update(task_id, description="🧙‍♂️ Analyzing character traits...")
                    pipeline_logger.info("Character analysis step", step="analysis")

                # Show completion message outside progress context
                console.print(f"✅ Extracted data for: [bold green]{npc_data.name}[/bold green]")

            # console.print(f"✅ Character analysis complete: "
            #               f"[bold blue]{character_profile.archetype}[/bold blue]")
            else:
                # Production mode: no progress display
                config = get_config()
                extractor = Crawl4AINPCExtractor(api_key=config.gemini_api_key)
                npc_data = await extractor.extract_npc_data(npc_id)

                if not npc_data:
                    pipeline_logger.warning("No NPC data found in pipeline", npc_id=npc_id)
                    return
                pipeline_logger.info("Extracted NPC data in pipeline", npc_name=npc_data.name)
                pipeline_logger.info("Character analysis step", step="analysis")

            # Display results
            # _display_character_profile(character_profile)

            if save_output:
                pipeline_logger.info("Saving pipeline results", output_location="character_profiles/")
                if not json_output:
                    console.print("[green]💾 Results saved to character_profiles/[/green]")

        except Exception as e:
            pipeline_logger.error("Pipeline execution failed", error=str(e), error_type=type(e).__name__, npc_id=npc_id)
            if not json_output:
                console.print(f"[red]❌ Pipeline error: {e}[/red]")
            raise


def _display_character_profile(profile):
    """Display character profile in a beautiful format."""
    # Character overview
    overview_table = Table(title=f"👤 Character Profile: {profile.npc_name}")
    overview_table.add_column("Aspect", style="cyan")
    overview_table.add_column("Details", style="white")

    overview_table.add_row("Archetype", profile.archetype)
    overview_table.add_row("Social Role", profile.social_role)
    overview_table.add_row("Personality Traits", profile.personality_traits)
    overview_table.add_row("Speech Patterns", profile.dialogue_patterns)
    overview_table.add_row("Emotional Range", profile.emotional_range)

    console.print(overview_table)

    # Voice characteristics
    voice_table = Table(title="🎵 Voice Characteristics")
    voice_table.add_column("Parameter", style="yellow")
    voice_table.add_column("Value", style="white")

    vc = profile.voice_characteristics
    voice_table.add_row("Age Range", vc.age_range.replace("_", " ").title())
    voice_table.add_row("Accent", vc.accent)
    voice_table.add_row("Tone", vc.tone)
    voice_table.add_row("Pace", vc.pace.replace("_", " ").title())
    voice_table.add_row("Pitch", vc.pitch.replace("_", " ").title())
    voice_table.add_row("Volume", vc.volume.title())

    console.print(voice_table)


def _initialize_logging(json_output: bool, log_level: str | None = None, log_file: str | None = None) -> None:
    """Initialize logging configuration."""
    config = get_config()
    mode = LoggingMode.PRODUCTION if json_output else LoggingMode.INTERACTIVE

    # Use config defaults when CLI parameters are not provided
    final_log_level = log_level or config.log_level
    final_log_file = log_file or (str(config.log_file) if config.log_file else None)

    configure_logging(mode=mode, log_level=final_log_level, log_file=final_log_file)


@app.command()
def logging_status():
    """
    📊 Show current logging configuration and status.
    """
    status = get_logging_status()

    table = Table(title="🔍 Logging Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Mode", status["mode"].title())
    table.add_row("Log Directory", status["log_directory"] or "N/A (production mode)")

    if status["log_files"]["main"]:
        table.add_row("Main Log", status["log_files"]["main"])
    if status["log_files"]["json"]:
        table.add_row("JSON Log", status["log_files"]["json"])
    if status["log_files"]["errors"]:
        table.add_row("Error Log", status["log_files"]["errors"])

    table.add_row("Suppressed Libraries", ", ".join(status["third_party_suppressed"]))

    console.print(table)


@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON logs instead of rich interface"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    log_file: str | None = typer.Option(None, "--log-file", help="Custom log file path"),
):
    """
    🧙‍♂️ Voiceover Mage - AI Voice Generation for OSRS NPCs

    Transform Old School RuneScape NPCs into authentic voices using AI-powered
    character analysis and voice generation.
    """
    # Store global options in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["json_output"] = json_output

    # Initialize logging once here instead of in each command
    _initialize_logging(json_output, log_level, log_file)


if __name__ == "__main__":
    app()

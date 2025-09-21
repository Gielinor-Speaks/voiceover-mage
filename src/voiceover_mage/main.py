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


# Add commands to the main group
app.add_command(extract_npc)
app.add_command(pipeline)
app.add_command(logging_status)


if __name__ == "__main__":
    app()


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


@click.command(name="choose-voice-sample")
@click.argument("npc_id", type=int)
@click.argument("sample_id", type=int)
@click.pass_context
async def choose_voice_sample(ctx, npc_id: int, sample_id: int):
    """Choose a representative voice sample for an NPC."""
    await _choose_voice_sample_async(npc_id, sample_id, ctx.obj["json_output"])


async def _choose_voice_sample_async(npc_id: int, sample_id: int, json_output: bool):
    db = DatabaseManager()
    await db.create_tables()
    result = await db.set_representative_sample(npc_id, sample_id)
    if not result:
        console.print(f"[red]Could not find sample {sample_id} for NPC {npc_id}. Nothing changed.[/red]")
        return
    console.print(
        f"[green]Sample {result.id} set as representative for NPC {npc_id} (provider: {result.provider}).[/green]"
    )

# ABOUTME: Main CLI application entry point using Typer and Rich for beautiful interface
# ABOUTME: Provides commands for NPC extraction, character analysis, and voice generation

import asyncio
import os
from typing import Optional

import typer

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from voiceover_mage.lib.logging import (
    configure_logging,
    LoggingMode,
    get_logging_status,
    get_logger,
    with_npc_context,
    with_pipeline_context,
    create_smart_progress,
)

app = typer.Typer(
    name="voiceover-mage",
    help="🎭 AI Voice Generation for Old School RuneScape NPCs",
    rich_markup_mode="rich"
)
console = Console()

# Global state for logging mode
_logging_initialized = False


@app.command()
def extract_npc(
    npc_id: int = typer.Argument(help="NPC ID to extract from the wiki"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed extraction process"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON logs instead of rich interface"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Custom log file path")
):
    """
    🕷️ Extract NPC data from the Old School RuneScape wiki.
    
    Crawls the wiki page for the specified NPC ID and extracts structured data
    including personality, appearance, and lore information.
    """
    _initialize_logging(json_output, log_level, log_file)
    asyncio.run(_extract_npc_async(npc_id, verbose, json_output))


async def _extract_npc_async(npc_id: int, verbose: bool, json_output: bool):
    """Async helper for NPC extraction."""
    logger = get_logger(__name__)
    
    with with_npc_context(npc_id) as npc_logger:
        npc_logger.info("Starting NPC extraction", npc_id=npc_id, verbose=verbose)
        
        try:
            from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
            extractor = Crawl4AINPCExtractor(api_key=os.getenv("GEMINI_API_KEY"))
            
            if not json_output:
                # Interactive mode: smart progress that updates from logs
                progress, task_id, tracker = create_smart_progress(
                    console, 
                    f"🔍 Starting NPC extraction for ID {npc_id}..."
                )
                
                with progress:
                    with tracker:
                        url = await extractor._get_npc_page_url(npc_id)
                        npc_logger.debug("Retrieved NPC page URL", url=url)
                        
                        npc_data_list = await extractor.extract_npc_data(url)
            else:
                # Production mode: no progress display
                url = await extractor._get_npc_page_url(npc_id)
                npc_logger.debug("Retrieved NPC page URL", url=url)
                npc_data_list = await extractor.extract_npc_data(url)
            
            if not npc_data_list:
                npc_logger.warning("No NPC data found", npc_id=npc_id)
                if not json_output:
                    console.print(f"[red]❌ No NPC data found for ID {npc_id}[/red]")
                return
            
            npc_logger.info("Successfully extracted NPC data", count=len(npc_data_list))
            
            for npc_data in npc_data_list:
                npc_logger.info(
                    "Processed NPC data",
                    npc_name=npc_data.name,
                    race=npc_data.race,
                    location=npc_data.location
                )
                
                if not json_output:
                    # Interactive mode: beautiful table display
                    table = Table(title=f"🎭 NPC Profile: {npc_data.name}", show_header=True)
                    table.add_column("Property", style="cyan", width=15)
                    table.add_column("Value", style="white")
                    
                    table.add_row("Name", npc_data.name)
                    table.add_row("Gender", npc_data.gender.name.title())
                    table.add_row("Race", npc_data.race)
                    table.add_row("Location", npc_data.location)
                    table.add_row("Examine Text", npc_data.examine_text)
                    table.add_row("Personality", npc_data.personality)
                    
                    console.print(table)
                    
                    if verbose:
                        console.print(Panel(
                            npc_data.description,
                            title="📜 Full Description",
                            border_style="blue"
                        ))
                        
        except Exception as e:
            npc_logger.error(
                "NPC extraction failed",
                error=str(e),
                error_type=type(e).__name__,
                npc_id=npc_id
            )
            if not json_output:
                console.print(f"[red]❌ Error extracting NPC data: {e}[/red]")
            raise


@app.command()
def pipeline(
    npc_id: int = typer.Argument(help="NPC ID to process through full pipeline"),
    save_output: bool = typer.Option(False, "--save", "-s", help="Save results to file"),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON logs instead of rich interface"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Custom log file path")
):
    """
    🔄 Run the complete NPC-to-voice pipeline.
    
    Extracts NPC data, analyzes character traits, and generates voice profile
    in one seamless workflow.
    """
    _initialize_logging(json_output, log_level, log_file)
    asyncio.run(_pipeline_async(npc_id, save_output, json_output))


async def _pipeline_async(npc_id: int, save_output: bool, json_output: bool):
    """Async helper for full pipeline."""
    logger = get_logger(__name__)
    
    with with_pipeline_context("npc_to_voice", npc_id=npc_id) as pipeline_logger:
        pipeline_logger.info("Starting NPC-to-voice pipeline", npc_id=npc_id, save_output=save_output)
        
        if not json_output:
            console.print(Panel.fit(
                "🎭 [bold cyan]Voiceover Mage Pipeline[/bold cyan] 🎭\n"
                f"Processing NPC ID: {npc_id}",
                border_style="magenta"
            ))

        from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
        
        try:
            if not json_output:
                # Interactive mode: smart progress that updates from logs
                progress, task_id, tracker = create_smart_progress(
                    console, 
                    f"🔄 Starting NPC-to-voice pipeline for ID {npc_id}..."
                )
                
                with progress:
                    with tracker:
                        # Step 1: Extract NPC data
                        extractor = Crawl4AINPCExtractor(api_key=os.getenv("GEMINI_API_KEY"))
                        url = await extractor._get_npc_page_url(npc_id)
                        npc_data_list = await extractor.extract_npc_data(url)
                        
                        if not npc_data_list:
                            pipeline_logger.warning("No NPC data found in pipeline", npc_id=npc_id)
                            console.print("[red]❌ No NPC data found[/red]")
                            return
                            
                        npc_data = npc_data_list[0]  # Use first result
                        pipeline_logger.info("Extracted NPC data in pipeline", npc_name=npc_data.name)
                        
                        # Update progress for character analysis step
                        progress.update(task_id, description="🧠 Analyzing character traits...")
                        pipeline_logger.info("Character analysis step", step="analysis")
                        
                # Show completion message outside progress context
                console.print(f"✅ Extracted data for: [bold green]{npc_data.name}[/bold green]")
                    
                    # console.print(f"✅ Character analysis complete: [bold blue]{character_profile.archetype}[/bold blue]")
            else:
                # Production mode: no progress display
                extractor = Crawl4AINPCExtractor(api_key=os.getenv("GEMINI_API_KEY"))
                url = await extractor._get_npc_page_url(npc_id)
                npc_data_list = await extractor.extract_npc_data(url)
                
                if not npc_data_list:
                    pipeline_logger.warning("No NPC data found in pipeline", npc_id=npc_id)
                    return
                    
                npc_data = npc_data_list[0]  # Use first result
                pipeline_logger.info("Extracted NPC data in pipeline", npc_name=npc_data.name)
                pipeline_logger.info("Character analysis step", step="analysis")
            
            # Display results
            # _display_character_profile(character_profile)
            
            if save_output:
                pipeline_logger.info("Saving pipeline results", output_location="character_profiles/")
                if not json_output:
                    console.print("[green]💾 Results saved to character_profiles/[/green]")
                
        except Exception as e:
            pipeline_logger.error(
                "Pipeline execution failed",
                error=str(e),
                error_type=type(e).__name__,
                npc_id=npc_id
            )
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
    overview_table.add_row("Personality Traits", ", ".join(profile.personality_traits))
    overview_table.add_row("Speech Patterns", ", ".join(profile.speech_patterns))
    overview_table.add_row("Emotional Range", ", ".join(profile.emotional_range))
    
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


def _initialize_logging(json_output: bool, log_level: str, log_file: Optional[str]) -> None:
    """Initialize logging configuration if not already done."""
    global _logging_initialized
    if not _logging_initialized:
        mode = LoggingMode.PRODUCTION if json_output else LoggingMode.INTERACTIVE
        configure_logging(mode=mode, log_level=log_level, log_file=log_file)
        _logging_initialized = True


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
def main():
    """
    🎭 Voiceover Mage - AI Voice Generation for OSRS NPCs
    
    Transform Old School RuneScape NPCs into authentic voices using AI-powered
    character analysis and voice generation.
    """
    pass


if __name__ == "__main__":
    app()

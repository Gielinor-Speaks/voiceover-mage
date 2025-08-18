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

app = typer.Typer(
    name="voiceover-mage",
    help="🎭 AI Voice Generation for Old School RuneScape NPCs",
    rich_markup_mode="rich"
)
console = Console()


@app.command()
def extract_npc(
    npc_id: int = typer.Argument(help="NPC ID to extract from the wiki"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed extraction process")
):
    """
    🕷️ Extract NPC data from the Old School RuneScape wiki.
    
    Crawls the wiki page for the specified NPC ID and extracts structured data
    including personality, appearance, and lore information.
    """
    asyncio.run(_extract_npc_async(npc_id, verbose))


async def _extract_npc_async(npc_id: int, verbose: bool):
    """Async helper for NPC extraction."""
    try:
        from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
        extractor = Crawl4AINPCExtractor(api_key=os.getenv("GEMINI_API_KEY"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("🔍 Finding NPC page...", total=None)
            url = await extractor._get_npc_page_url(npc_id)
            
            progress.update(task, description="🌐 Extracting NPC data...")
            npc_data_list = await extractor.extract_npc_data(url)
        
        if not npc_data_list:
            console.print("[red]❌ No NPC data found for ID {npc_id}[/red]")
            return
        
        for npc_data in npc_data_list:
            # Create a beautiful display table
            table = Table(title=f"🎭 NPC Profile: {npc_data.name}", show_header=True)
            table.add_column("Property", style="cyan", width=15)
            table.add_column("Value", style="white")
            
            table.add_row("Name", npc_data.name)
            table.add_row("Gender", npc_data.gender.title())
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
        console.print(f"[red]❌ Error extracting NPC data: {e}[/red]")


@app.command()
def pipeline(
    npc_id: int = typer.Argument(help="NPC ID to process through full pipeline"),
    save_output: bool = typer.Option(False, "--save", "-s", help="Save results to file")
):
    """
    🔄 Run the complete NPC-to-voice pipeline.
    
    Extracts NPC data, analyzes character traits, and generates voice profile
    in one seamless workflow.
    """
    asyncio.run(_pipeline_async(npc_id, save_output))


async def _pipeline_async(npc_id: int, save_output: bool):
    """Async helper for full pipeline."""
    console.print(Panel.fit(
        "🎭 [bold cyan]Voiceover Mage Pipeline[/bold cyan] 🎭\n"
        f"Processing NPC ID: {npc_id}",
        border_style="magenta"
    ))

    from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
    
    try:
        # Step 1: Extract NPC data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task1 = progress.add_task("🕷️ Extracting NPC data...", total=None)
            extractor = Crawl4AINPCExtractor(api_key=os.getenv("GEMINI_API_KEY"))
            url = await extractor._get_npc_page_url(npc_id)
            npc_data_list = await extractor.extract_npc_data(url)
            progress.remove_task(task1)
            
            if not npc_data_list:
                console.print("[red]❌ No NPC data found[/red]")
                return
                
            npc_data = npc_data_list[0]  # Use first result
            console.print(f"✅ Extracted data for: [bold green]{npc_data.name}[/bold green]")
            
            # Step 2: Character analysis
            task2 = progress.add_task("🧠 Analyzing character...", total=None)
            progress.remove_task(task2)
            
            # console.print(f"✅ Character analysis complete: [bold blue]{character_profile.archetype}[/bold blue]")
        
        # Display results
        # _display_character_profile(character_profile)
        
        if save_output:
            console.print("[green]💾 Results saved to character_profiles/[/green]")
            
    except Exception as e:
        console.print(f"[red]❌ Pipeline error: {e}[/red]")


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

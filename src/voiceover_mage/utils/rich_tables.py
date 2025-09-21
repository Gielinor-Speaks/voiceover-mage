# ABOUTME: Beautiful rich table utilities to replace tabulate with styled, colorful displays
# ABOUTME: Provides pre-configured table generators for common data display patterns

from typing import Any

from rich.box import ROUNDED, SIMPLE
from rich.console import Console
from rich.table import Table


def create_key_value_table(
    title: str,
    data: dict[str, str],
    title_style: str = "bold cyan",
    key_style: str = "bold blue",
    value_style: str = "green",
    box_style=ROUNDED,
) -> Table:
    """Create a beautiful key-value table to replace _print_key_value_table.

    Args:
        title: Table title with emoji/styling
        data: Dictionary of key-value pairs to display
        title_style: Style for the table title
        key_style: Style for the key column
        value_style: Style for the value column
        box_style: Border style for the table

    Returns:
        Formatted Rich table ready for printing
    """
    table = Table(
        title=f"[{title_style}]{title}[/{title_style}]",
        box=box_style,
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
        title_justify="left",
        expand=False,
    )

    table.add_column("Field", style=key_style, width=None, no_wrap=False)
    table.add_column("Value", style=value_style, width=None, no_wrap=False)

    for key, value in data.items():
        table.add_row(key, str(value))

    return table


def create_multi_column_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    title_style: str = "bold cyan",
    header_style: str = "bold magenta",
    alternate_row_styles: list[str] | None = None,
    box_style=ROUNDED,
) -> Table:
    """Create a beautiful multi-column table to replace _print_multi_column_table.

    Args:
        title: Table title with emoji/styling
        columns: List of (column_name, column_style) tuples
        rows: List of row data
        title_style: Style for the table title
        header_style: Style for column headers
        alternate_row_styles: Alternating row styles for zebra striping
        box_style: Border style for the table

    Returns:
        Formatted Rich table ready for printing
    """
    table = Table(
        title=f"[{title_style}]{title}[/{title_style}]",
        box=box_style,
        show_header=True,
        header_style=header_style,
        border_style="cyan",
        title_justify="left",
        row_styles=alternate_row_styles or ["", "dim"],
        expand=True,
    )

    # Add columns with their styles
    for name, style in columns:
        table.add_column(name, style=style)

    # Add rows
    for row in rows:
        table.add_row(*row)

    return table


def create_extraction_status_table(extraction: Any) -> Table:
    """Create a styled table for NPC extraction status display.

    Args:
        extraction: NPCPipelineState object with extraction data

    Returns:
        Beautiful status table with icons and color coding
    """
    # Determine cache indicator
    cache_indicator = "💾 Cached" if hasattr(extraction, "cached") and extraction.cached else "🆕 Fresh"

    status_data = {
        "🆔 NPC ID": str(extraction.id),
        "📛 Name": extraction.npc_name,
        "🌐 Wiki URL": extraction.wiki_url or "Not available",
        "📅 Extracted At": extraction.created_at.strftime("%Y-%m-%d %H:%M:%S") if extraction.created_at else "Unknown",
        "📄 Markdown Length": f"{len(extraction.raw_markdown):,} chars" if extraction.raw_markdown else "0 chars",
        "🖼️ Chathead": "✅ Available" if extraction.chathead_image_url else "❌ Missing",
        "🖼️ Main Image": "✅ Available" if extraction.image_url else "❌ Missing",
    }

    return create_key_value_table(
        title=f"{cache_indicator} Extraction Status",
        data=status_data,
        title_style="bold magenta",
        key_style="cyan",
        value_style="white",
    )


def create_character_profile_table(profile: dict[str, Any]) -> Table:
    """Create a styled table for character profile summary.

    Args:
        profile: Character profile dictionary

    Returns:
        Beautiful character overview table
    """

    def _truncate(text: str, length: int) -> str:
        return text[:length] + "..." if len(text) > length else text

    def _join_parts(*parts) -> str:
        return ", ".join(p for p in parts if p) or "Not analyzed"

    npc_name = profile.get("npc_name", "Unknown")

    character_data = {
        "🎭 Personality": _truncate(profile.get("personality_traits", ""), 150) or "Not analyzed",
        "💼 Occupation": profile.get("occupation", "") or "Not specified",
        "💬 Speech Style": _truncate(profile.get("dialogue_patterns", ""), 120) or "Not analyzed",
        "👤 Appearance": _join_parts(
            profile.get("age_category", ""), profile.get("build_type", ""), profile.get("attire_style", "")
        ),
        "🎨 Archetype": profile.get("visual_archetype", "") or "Not specified",
    }

    return create_key_value_table(
        title=f"👤 {npc_name}",
        data=character_data,
        title_style="bold yellow",
        key_style="bold blue",
        value_style="white",
    )


def create_confidence_metrics_table(profile: dict[str, Any]) -> Table:
    """Create a confidence metrics table with progress-style indicators.

    Args:
        profile: Character profile dictionary with confidence metrics

    Returns:
        Styled confidence table with percentage bars
    """
    confidence_data = {}

    for metric, key in [
        ("Overall", "overall_confidence"),
        ("Text Analysis", "text_confidence"),
        ("Visual Analysis", "visual_confidence"),
    ]:
        value = profile.get(key, 0)
        if value:
            percentage = f"{value:.1%}"
            # Add color coding based on confidence level
            if value >= 0.8:
                styled_percentage = f"[bold green]{percentage}[/bold green] ✅"
            elif value >= 0.6:
                styled_percentage = f"[bold yellow]{percentage}[/bold yellow] ⚠️"
            else:
                styled_percentage = f"[bold red]{percentage}[/bold red] ❌"
            confidence_data[metric] = styled_percentage
        else:
            confidence_data[metric] = "[dim]Unknown[/dim]"

    return create_key_value_table(
        title="🎵 Analysis Confidence",
        data=confidence_data,
        title_style="bold cyan",
        key_style="blue",
        value_style="white",
    )


def create_voice_samples_table(samples: list[Any], npc_id: int) -> Table:
    """Create a beautiful table for voice samples display.

    Args:
        samples: List of voice sample objects
        npc_id: NPC ID for the table title

    Returns:
        Styled voice samples table
    """
    columns = [
        ("ID", "cyan"),
        ("Created", "white"),
        ("Provider", "magenta"),
        ("Model", "green"),
        ("Size (KB)", "yellow"),
        ("Representative", "blue"),
        ("Prompt (truncated)", "dim white"),
    ]

    rows = []
    for s in samples:
        size_kb = f"{(len(s.audio_bytes) / 1024):.1f}" if s.audio_bytes else "0.0"
        prompt_short = (s.voice_prompt[:60] + "...") if len(s.voice_prompt) > 60 else s.voice_prompt

        # Style the representative column
        representative = "[bold green]✅[/bold green]" if s.is_representative else ""

        rows.append(
            [
                str(s.id or "-"),
                s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                s.provider,
                s.model,
                size_kb,
                representative,
                prompt_short,
            ]
        )

    return create_multi_column_table(
        title=f"🎵 Voice Samples for NPC {npc_id}",
        columns=columns,
        rows=rows,
        alternate_row_styles=["", "dim"],
    )


def create_logging_status_table(status: dict[str, Any]) -> Table:
    """Create a logging configuration status table.

    Args:
        status: Logging status dictionary

    Returns:
        Styled logging configuration table
    """
    logging_data = {
        "🔧 Mode": status["mode"].title(),
        "📁 Log Directory": status["log_directory"] or "N/A (production mode)",
        "🔇 Suppressed Libraries": ", ".join(status["third_party_suppressed"]),
    }

    # Add log files if they exist
    if status["log_files"]["main"]:
        logging_data["📝 Main Log"] = status["log_files"]["main"]
    if status["log_files"]["json"]:
        logging_data["📊 JSON Log"] = status["log_files"]["json"]
    if status["log_files"]["errors"]:
        logging_data["🚨 Error Log"] = status["log_files"]["errors"]

    return create_key_value_table(
        title="🔍 Logging Configuration",
        data=logging_data,
        title_style="bold green",
        key_style="blue",
        value_style="white",
    )


def create_pipeline_summary_table(extraction: Any) -> Table:
    """Create a pipeline completion summary table.

    Args:
        extraction: NPCPipelineState with completed stages

    Returns:
        Beautiful pipeline summary table
    """
    summary_data = {
        "🆔 NPC": f"{extraction.id} - {extraction.npc_name}",
        "📊 Completed Stages": ", ".join(extraction.completed_stages) if extraction.completed_stages else "None",
        "✅ Success": "Yes" if extraction.extraction_success else "No",
    }

    if hasattr(extraction, "character_profile") and extraction.character_profile:
        profile = extraction.character_profile
        if hasattr(profile, "overall_confidence"):
            confidence = getattr(profile, "overall_confidence", 0)
            summary_data["🎯 Confidence"] = f"{confidence:.1%}" if confidence else "Unknown"

    return create_key_value_table(
        title="🔄 Pipeline Summary",
        data=summary_data,
        title_style="bold green",
        key_style="cyan",
        value_style="white",
        box_style=SIMPLE,
    )


def print_rich_table(console: Console, table: Table) -> None:
    """Print a rich table with consistent spacing and style.

    Args:
        console: Rich console instance
        table: Configured table to print
    """
    console.print()  # Add spacing before
    console.print(table)
    console.print()  # Add spacing after

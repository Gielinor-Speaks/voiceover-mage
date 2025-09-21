# ABOUTME: Enhanced rich-based progress reporting with beautiful async operation dashboards
# ABOUTME: Replaces tabulate tables with rich styling and provides real-time pipeline visualization

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

from rich.box import ROUNDED
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

T = TypeVar("T")


class PipelineStage(Enum):
    """Pipeline stages for NPC processing."""

    RAW_EXTRACTION = "raw_extraction"
    LLM_EXTRACTION = "llm_extraction"
    INTELLIGENT_ANALYSIS = "intelligent_analysis"
    VOICE_GENERATION = "voice_generation"


class StageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class StageInfo:
    """Information about a pipeline stage."""

    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    @property
    def duration(self) -> timedelta | None:
        """Get stage duration if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def elapsed_time(self) -> timedelta | None:
        """Get elapsed time since stage started."""
        if self.start_time:
            end = self.end_time or datetime.now()
            return end - self.start_time
        return None


class PipelineDashboard:
    """Live dashboard for pipeline progress with real-time updates."""

    def __init__(self, console: Console, npc_id: int, npc_name: str):
        self.console = console
        self.npc_id = npc_id
        self.npc_name = npc_name
        self.pipeline_start = datetime.now()
        self.stages: dict[PipelineStage, StageInfo] = {stage: StageInfo(stage=stage) for stage in PipelineStage}

    def start_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as started."""
        self.stages[stage].status = StageStatus.IN_PROGRESS
        self.stages[stage].start_time = datetime.now()

    def complete_stage(self, stage: PipelineStage, data: dict[str, Any] | None = None) -> None:
        """Mark a stage as completed with optional data."""
        stage_info = self.stages[stage]
        stage_info.status = StageStatus.COMPLETED
        stage_info.end_time = datetime.now()
        if data:
            stage_info.data.update(data)

    def error_stage(self, stage: PipelineStage, error: str) -> None:
        """Mark a stage as errored."""
        stage_info = self.stages[stage]
        stage_info.status = StageStatus.ERROR
        stage_info.end_time = datetime.now()
        stage_info.error_message = error

    def skip_stage(self, stage: PipelineStage, reason: str) -> None:
        """Mark a stage as skipped."""
        stage_info = self.stages[stage]
        stage_info.status = StageStatus.SKIPPED
        stage_info.data["skip_reason"] = reason

    def update_stage_data(self, stage: PipelineStage, data: dict[str, Any]) -> None:
        """Update stage data without changing status."""
        self.stages[stage].data.update(data)

    def create_renderable(self) -> Panel:
        """Create a progressive rich renderable for the live dashboard."""
        # Calculate elapsed time
        elapsed = datetime.now() - self.pipeline_start
        elapsed_str = f"{elapsed.seconds // 60:02d}:{elapsed.seconds % 60:02d}"

        # Create main content table
        content = Table.grid(padding=(0, 1), expand=True)
        content.add_column(justify="left")

        # Header with NPC info
        header_text = (
            f"🧙‍♂️ [bold cyan]NPC {self.npc_id}:[/bold cyan] [bold magenta]{self.npc_name}[/bold magenta] | "
            f"⏱️ [yellow]{elapsed_str}[/yellow]"
        )
        content.add_row(header_text)
        content.add_row("")  # Spacing

        # Progressive stages display - show more details as we progress
        stages_display = self._create_progressive_stages_display()
        content.add_row(stages_display)
        content.add_row("")  # Spacing

        # Summary footer with key metrics
        summary = self._create_summary_footer()
        content.add_row(summary)

        return Panel(content, title="🎭 Voiceover Mage Pipeline", border_style="magenta", padding=(1, 2))

    def _create_progressive_stages_display(self) -> Table:
        """Create a progressive display that shows more details as stages complete."""
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column("Stage", width=None)

        stage_order = [
            PipelineStage.RAW_EXTRACTION,
            PipelineStage.LLM_EXTRACTION,
            PipelineStage.INTELLIGENT_ANALYSIS,
            PipelineStage.VOICE_GENERATION,
        ]

        for stage in stage_order:
            info = self.stages[stage]
            stage_row = self._format_progressive_stage(stage, info)
            table.add_row(stage_row)

        return table

    def _format_progressive_stage(self, stage: PipelineStage, info: StageInfo) -> Text:
        """Format a stage for progressive display - more details as we progress."""
        # Status icons
        status_icons = {
            StageStatus.PENDING: "⏳",
            StageStatus.IN_PROGRESS: "🔄",
            StageStatus.COMPLETED: "✅",
            StageStatus.ERROR: "❌",
            StageStatus.SKIPPED: "⏭️",
        }

        # Full stage names
        stage_names = {
            PipelineStage.RAW_EXTRACTION: "Raw Data Extraction",
            PipelineStage.LLM_EXTRACTION: "LLM Enhancement",
            PipelineStage.INTELLIGENT_ANALYSIS: "Character Analysis",
            PipelineStage.VOICE_GENERATION: "Voice Generation",
        }

        icon = status_icons[info.status]
        name = stage_names[stage]

        # Create rich text with progressive detail
        text = Text()
        text.append(f"{icon} ", style="bold")

        # Stage name with status-based styling
        if info.status == StageStatus.COMPLETED:
            text.append(name, style="bold green")
        elif info.status == StageStatus.IN_PROGRESS:
            text.append(name, style="bold yellow")
        elif info.status == StageStatus.ERROR:
            text.append(name, style="bold red")
        else:
            text.append(name, style="dim")

        # Add progressive details based on stage completion
        details = self._get_progressive_stage_details(stage, info)
        if details:
            text.append(f"\n    {details}", style="dim cyan")

        return text

    def _get_progressive_stage_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get progressive details that expand as stages complete."""
        if info.status == StageStatus.ERROR and info.error_message:
            return f"⚠️ Error: {info.error_message}"

        if info.status == StageStatus.SKIPPED:
            reason = info.data.get("skip_reason", "No reason provided")
            return f"⏭️ Skipped: {reason}"

        if info.status == StageStatus.IN_PROGRESS:
            # Show current operation
            progress_details = {
                PipelineStage.RAW_EXTRACTION: "🌐 Fetching NPC data from OSRS Wiki...",
                PipelineStage.LLM_EXTRACTION: "🧠 Enhancing raw data with LLM analysis...",
                PipelineStage.INTELLIGENT_ANALYSIS: "🎭 Extracting character traits and personality...",
                PipelineStage.VOICE_GENERATION: "🎵 Creating voice samples with ElevenLabs...",
            }
            return progress_details.get(stage, "⚡ Processing...")

        if info.status == StageStatus.COMPLETED:
            return self._get_completed_progressive_details(stage, info)

        # Pending stages - show what they'll do
        pending_details = {
            PipelineStage.RAW_EXTRACTION: "📋 Will extract NPC data, dialogue, and images",
            PipelineStage.LLM_EXTRACTION: "🔍 Will enhance data with contextual analysis",
            PipelineStage.INTELLIGENT_ANALYSIS: "🎯 Will analyze personality for voice generation",
            PipelineStage.VOICE_GENERATION: "🎤 Will create multiple voice sample options",
        }
        return pending_details.get(stage, "⏸️ Waiting...")

    def _get_completed_progressive_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get detailed completion information for progressive display."""
        data = info.data
        duration = f"({info.duration.total_seconds():.1f}s)" if info.duration else ""

        if stage == PipelineStage.RAW_EXTRACTION:
            chars = data.get("markdown_chars", 0)
            has_images = data.get("has_images", False)
            extraction_success = data.get("extraction_success", True)
            has_structured_data = data.get("has_structured_data", False)

            image_text = "📸 Chat head image found" if has_images else "📄 Text only"
            validation_icons = []

            if extraction_success:
                validation_icons.append("✅ Valid NPC")
            if has_structured_data:
                validation_icons.append("🏗️ Structured data")

            validation_text = " • ".join(validation_icons)
            main_text = f"✓ {chars:,} characters extracted • {image_text}"

            if validation_text:
                return f"{main_text} • {validation_text} {duration}"
            return f"{main_text} {duration}"

        elif stage == PipelineStage.LLM_EXTRACTION:
            # Look ahead to see if we have LLM data
            return f"✓ Data enhanced with contextual information {duration}"

        elif stage == PipelineStage.INTELLIGENT_ANALYSIS:
            confidence = data.get("confidence", 0)
            traits_count = len(data.get("personality_traits", []))
            confidence_text = f"🎯 {confidence:.1%} confidence" if confidence else "🎯 Analysis complete"
            traits_text = f"• {traits_count} traits identified" if traits_count else ""

            # Store latest confidence for footer
            if confidence:
                self._latest_confidence = confidence

            return f"✓ {confidence_text} {traits_text} {duration}"

        elif stage == PipelineStage.VOICE_GENERATION:
            samples = data.get("voice_samples", 0)
            best_sample = data.get("selected_sample")
            samples_text = f"🎵 {samples} samples generated" if samples else "🎵 Voice created"
            selection_text = f"• Sample #{best_sample} selected" if best_sample else ""
            return f"✓ {samples_text} {selection_text} {duration}"

        return f"✓ Complete {duration}"

    def _create_summary_footer(self) -> Text:
        """Create a summary footer with key metrics."""
        # Progress counts - debug the stage statuses
        error_count = sum(1 for s in self.stages.values() if s.status == StageStatus.ERROR)
        skipped_count = sum(1 for s in self.stages.values() if s.status == StageStatus.SKIPPED)
        total_stages = len(self.stages)

        # Debug: Force refresh the counts by checking actual stage statuses
        actual_completed = 0
        for _stage, info in self.stages.items():
            if info.status == StageStatus.COMPLETED:
                actual_completed += 1

        # Create summary text
        summary = Text()

        # Use the actual completed count instead of the calculated one
        display_completed = actual_completed

        # Progress indicator - build with proper Text styling
        summary.append("📊 Progress: ", style="default")

        if error_count > 0:
            summary.append(f"{display_completed}/{total_stages}", style="bold red")
            error_suffix = f" ({error_count} errors"
            if skipped_count > 0:
                error_suffix += f", {skipped_count} skipped"
            error_suffix += ")"
            summary.append(error_suffix, style="default")
        elif skipped_count > 0:
            summary.append(f"{display_completed}/{total_stages}", style="bold yellow")
            summary.append(f" stages ({skipped_count} skipped)", style="default")
        else:
            summary.append(f"{display_completed}/{total_stages}", style="bold green")
            summary.append(" stages complete", style="default")

        # Add confidence if available
        if hasattr(self, "_latest_confidence") and self._latest_confidence:
            summary.append("  |  🎯 Character Confidence: ", style="default")
            summary.append(f"{self._latest_confidence:.1%}", style="bold green")

        # Add circuit breaker status
        raw_extraction_stage = self.stages.get(PipelineStage.RAW_EXTRACTION)
        if raw_extraction_stage and raw_extraction_stage.status == StageStatus.COMPLETED:
            extraction_success = raw_extraction_stage.data.get("extraction_success", True)
            if not extraction_success:
                summary.append("  |  ⚠️ ", style="default")
                summary.append("Invalid NPC detected", style="bold red")

        return summary

    def _create_compact_stages_table(self) -> Table:
        """Create a compact table showing all stages in a single row."""
        table = Table.grid(padding=(0, 2))

        # Add columns for each stage
        for _ in PipelineStage:
            table.add_column()

        # Create stage displays
        stage_displays = []
        stage_order = [
            PipelineStage.RAW_EXTRACTION,
            PipelineStage.LLM_EXTRACTION,
            PipelineStage.INTELLIGENT_ANALYSIS,
            PipelineStage.VOICE_GENERATION,
        ]

        for stage in stage_order:
            info = self.stages[stage]
            display = self._format_compact_stage(stage, info)
            stage_displays.append(display)

        table.add_row(*stage_displays)
        return table

    def _format_compact_stage(self, stage: PipelineStage, info: StageInfo) -> Text:
        """Format a stage for compact display."""
        # Status icons
        status_icons = {
            StageStatus.PENDING: "⏳",
            StageStatus.IN_PROGRESS: "🔄",
            StageStatus.COMPLETED: "✅",
            StageStatus.ERROR: "❌",
            StageStatus.SKIPPED: "⏭️",
        }

        # Short stage names
        stage_names = {
            PipelineStage.RAW_EXTRACTION: "Extract",
            PipelineStage.LLM_EXTRACTION: "Enhance",
            PipelineStage.INTELLIGENT_ANALYSIS: "Analyze",
            PipelineStage.VOICE_GENERATION: "Voice",
        }

        icon = status_icons[info.status]
        name = stage_names[stage]

        # Create compact text
        text = Text()
        text.append(f"{icon} ", style="bold")

        # Stage name with status-based styling
        if info.status == StageStatus.COMPLETED:
            text.append(name, style="bold green")
        elif info.status == StageStatus.IN_PROGRESS:
            text.append(name, style="bold yellow")
        elif info.status == StageStatus.ERROR:
            text.append(name, style="bold red")
        else:
            text.append(name, style="dim")

        # Add brief data on next line
        details = self._get_compact_stage_details(stage, info)
        if details:
            text.append(f"\n{details}", style="dim cyan")

        return text

    def _get_compact_stage_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get brief details for compact display."""
        if info.status == StageStatus.ERROR and info.error_message:
            return f"⚠️ {info.error_message[:20]}..."

        if info.status == StageStatus.SKIPPED:
            return "⏭️ Skipped"

        if info.status == StageStatus.IN_PROGRESS:
            return "⚡ Working..."

        if info.status == StageStatus.COMPLETED:
            data = info.data
            if stage == PipelineStage.RAW_EXTRACTION:
                chars = data.get("markdown_chars", 0)
                return f"📄 {chars:,} chars"
            elif stage == PipelineStage.INTELLIGENT_ANALYSIS:
                confidence = data.get("confidence", 0)
                if confidence:
                    # Store latest confidence for footer
                    self._latest_confidence = confidence
                    return f"🎯 {confidence:.0%}"
                return "✓ Done"
            elif stage == PipelineStage.VOICE_GENERATION:
                samples = data.get("voice_samples", 0)
                return f"🎵 {samples} samples" if samples else "✓ Done"
            else:
                return "✓ Done"

        return ""

    def _create_stages_panel(self) -> Panel:
        """Create the stages progress panel."""
        layout = Layout()
        layout.split_row(Layout(name="left"), Layout(name="right"))

        # Left side - Raw and LLM extraction
        left_stages = [PipelineStage.RAW_EXTRACTION, PipelineStage.LLM_EXTRACTION]
        left_table = self._create_stage_table(left_stages)
        layout["left"].update(left_table)

        # Right side - Analysis and Voice generation
        right_stages = [PipelineStage.INTELLIGENT_ANALYSIS, PipelineStage.VOICE_GENERATION]
        right_table = self._create_stage_table(right_stages)
        layout["right"].update(right_table)

        return Panel(layout, title="🔄 Pipeline Stages", border_style="cyan")

    def _create_stage_table(self, stages: list[PipelineStage]) -> Table:
        """Create a table for specific stages."""
        table = Table(box=ROUNDED, expand=True, show_header=False)
        table.add_column("Stage", style="bold", width=None)

        for stage in stages:
            stage_info = self.stages[stage]
            stage_text = self._format_stage_display(stage, stage_info)
            table.add_row(stage_text)

        return table

    def _format_stage_display(self, stage: PipelineStage, info: StageInfo) -> Text:
        """Format a stage for display with status and data."""
        # Status icon
        status_icons = {
            StageStatus.PENDING: "⏳",
            StageStatus.IN_PROGRESS: "🔄",
            StageStatus.COMPLETED: "✅",
            StageStatus.ERROR: "❌",
            StageStatus.SKIPPED: "⏭️",
        }

        # Stage names
        stage_names = {
            PipelineStage.RAW_EXTRACTION: "Raw Extraction",
            PipelineStage.LLM_EXTRACTION: "LLM Extraction",
            PipelineStage.INTELLIGENT_ANALYSIS: "Intelligent Analysis",
            PipelineStage.VOICE_GENERATION: "Voice Generation",
        }

        icon = status_icons[info.status]
        name = stage_names[stage]

        # Create rich text with styling
        text = Text()
        text.append(f"{icon} ", style="bold")

        # Stage name with status-based styling
        if info.status == StageStatus.COMPLETED:
            text.append(name, style="bold green")
        elif info.status == StageStatus.IN_PROGRESS:
            text.append(name, style="bold yellow")
        elif info.status == StageStatus.ERROR:
            text.append(name, style="bold red")
        else:
            text.append(name, style="dim")

        text.append("\n")

        # Add stage-specific data
        details = self._get_stage_details(stage, info)
        if details:
            text.append(f"    └─ {details}", style="dim cyan")

        return text

    def _get_stage_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get formatted details for a stage."""
        if info.status == StageStatus.ERROR and info.error_message:
            return f"Error: {info.error_message}"

        if info.status == StageStatus.SKIPPED:
            reason = info.data.get("skip_reason", "No reason provided")
            return f"Skipped: {reason}"

        if info.status == StageStatus.IN_PROGRESS:
            return self._get_in_progress_details(stage, info)

        if info.status == StageStatus.COMPLETED:
            return self._get_completed_details(stage, info)

        return "Pending..."

    def _get_in_progress_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get details for in-progress stages."""
        details_map = {
            PipelineStage.RAW_EXTRACTION: "Scraping wiki data...",
            PipelineStage.LLM_EXTRACTION: "Enhancing with LLM analysis...",
            PipelineStage.INTELLIGENT_ANALYSIS: "Analyzing character traits...",
            PipelineStage.VOICE_GENERATION: "Generating voice samples...",
        }
        return details_map.get(stage, "Processing...")

    def _get_completed_details(self, stage: PipelineStage, info: StageInfo) -> str:
        """Get details for completed stages."""
        data = info.data

        if stage == PipelineStage.RAW_EXTRACTION:
            chars = data.get("markdown_chars", 0)
            images = "with images" if data.get("has_images") else "no images"
            return f"Markdown: {chars:,} chars, {images}"

        elif stage == PipelineStage.LLM_EXTRACTION:
            return "Enhanced data loaded"

        elif stage == PipelineStage.INTELLIGENT_ANALYSIS:
            confidence = data.get("confidence", 0)
            return f"Confidence: {confidence:.1%}" if confidence else "Analysis complete"

        elif stage == PipelineStage.VOICE_GENERATION:
            samples = data.get("voice_samples", 0)
            return f"{samples} voice samples generated" if samples else "Voice generated"

        return "Complete"


def create_rich_table(
    title: str,
    columns: list[str] | list[tuple[str, str]],
    rows: list[list[str]],
    style: str | None = None,
    box_style=ROUNDED,
) -> Table:
    """Create a beautiful rich table to replace tabulate tables.

    Args:
        title: Table title
        columns: Column definitions - can be strings or (name, style) tuples
        rows: Table row data
        style: Overall table style
        box_style: Border style

    Returns:
        Formatted Rich table
    """
    table = Table(
        title=title,
        box=box_style,
        style=style,  # type: ignore[arg-type]
        show_header=True,
        header_style="bold magenta",
    )

    # Add columns with optional styling
    for col in columns:
        if isinstance(col, tuple):
            name, col_style = col
            table.add_column(name, style=col_style)
        else:
            table.add_column(col)

    # Add rows
    for row in rows:
        table.add_row(*row)

    return table


def create_stage_status_table(stages: dict[PipelineStage, StageInfo]) -> Table:
    """Create a status table for pipeline stages."""
    table = Table(title="🔄 Pipeline Status", box=ROUNDED, show_header=True, header_style="bold cyan")

    table.add_column("Stage", style="bold", width=20)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Details", style="dim")

    stage_names = {
        PipelineStage.RAW_EXTRACTION: "Raw Extraction",
        PipelineStage.LLM_EXTRACTION: "LLM Extraction",
        PipelineStage.INTELLIGENT_ANALYSIS: "Analysis",
        PipelineStage.VOICE_GENERATION: "Voice Generation",
    }

    status_styles = {
        StageStatus.PENDING: ("⏳ Pending", "dim"),
        StageStatus.IN_PROGRESS: ("🔄 Running", "yellow"),
        StageStatus.COMPLETED: ("✅ Done", "green"),
        StageStatus.ERROR: ("❌ Error", "red"),
        StageStatus.SKIPPED: ("⏭️ Skipped", "blue"),
    }

    for stage, info in stages.items():
        name = stage_names.get(stage, stage.value)
        status_text, status_style = status_styles[info.status]

        details = ""
        if info.status == StageStatus.ERROR and info.error_message:
            details = info.error_message
        elif info.status == StageStatus.COMPLETED and info.duration:
            details = f"Completed in {info.duration.total_seconds():.1f}s"
        elif info.status == StageStatus.IN_PROGRESS and info.elapsed_time:
            details = f"Running for {info.elapsed_time.total_seconds():.1f}s"

        table.add_row(name, f"[{status_style}]{status_text}[/{status_style}]", details)

    return table


class EnhancedProgressReporter:
    """Enhanced progress reporter with beautiful rich displays."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    async def run_with_pipeline_dashboard(
        self,
        operation: Callable[[PipelineDashboard], Awaitable[T]],
        npc_id: int,
        npc_name: str,
        refresh_rate: float = 0.25,
    ) -> T:
        """Run an async operation with a live pipeline dashboard.

        Args:
            operation: Async operation that takes a dashboard and returns a result
            npc_id: NPC ID being processed
            npc_name: NPC name for display
            refresh_rate: Dashboard refresh rate in seconds

        Returns:
            Result from the operation
        """
        dashboard = PipelineDashboard(console=self.console, npc_id=npc_id, npc_name=npc_name)

        with Live(
            dashboard.create_renderable(),
            console=self.console,
            refresh_per_second=1 / refresh_rate,
            transient=False,
        ) as live:
            # Update the live display as the dashboard changes
            async def wrapped_operation():
                result = await operation(dashboard)
                # Final update
                live.update(dashboard.create_renderable())
                return result

            # Periodically update the display
            import asyncio

            async def update_display():
                while True:
                    live.update(dashboard.create_renderable())
                    await asyncio.sleep(refresh_rate)

            # Run operation and display updates concurrently
            update_task = asyncio.create_task(update_display())
            try:
                result = await wrapped_operation()
            finally:
                update_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await update_task

            return result

    async def run_with_status(
        self,
        operation: Callable[[], Awaitable[T]],
        message: str,
        success_message: str | None = None,
        spinner: str = "dots",
    ) -> T:
        """Run an async operation with a rich status indicator.

        Args:
            operation: Async operation to run
            message: Status message to display
            success_message: Message to show on success
            spinner: Spinner style

        Returns:
            Result from the operation
        """
        with self.console.status(message, spinner=spinner):
            result = await operation()

        if success_message:
            self.console.print(success_message)

        return result

    def create_progress_with_context(self, description: str, show_elapsed: bool = True) -> Progress:
        """Create a rich progress bar with contextual information.

        Args:
            description: Progress description
            show_elapsed: Whether to show elapsed time

        Returns:
            Configured Progress instance
        """
        columns = [SpinnerColumn(), TextColumn("[progress.description]{task.description}")]

        if show_elapsed:
            columns.append(TimeElapsedColumn())

        return Progress(*columns, console=self.console, transient=True)


# Convenience functions for backward compatibility and ease of use


def create_smart_progress(
    console: Console, initial_description: str = "🪄 Invoking magical operations..."
) -> tuple[Progress, Any, SimpleProgressTracker]:
    """Create enhanced smart progress with better styling.

    This maintains API compatibility while providing enhanced visuals.
    """
    progress = Progress(
        SpinnerColumn(style="magenta"),
        TextColumn("[bold blue][progress.description]{task.description}[/bold blue]"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )

    task_id = progress.add_task(initial_description, total=None)
    tracker = SimpleProgressTracker(progress, task_id)

    return progress, task_id, tracker


class SimpleProgressTracker:
    """Enhanced progress tracker with better visual feedback."""

    def __init__(self, progress: Progress, task_id: Any):
        self.progress = progress
        self.task_id = task_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def update_description(self, description: str) -> None:
        """Update the progress description."""
        self.progress.update(self.task_id, description=description)

    def update_with_data(self, description: str, **data) -> None:
        """Update progress with contextual data."""
        data_str = ", ".join(f"{k}: {v}" for k, v in data.items())
        full_description = f"{description} ({data_str})" if data_str else description
        self.update_description(full_description)

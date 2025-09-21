# ABOUTME: Simplified progress tracking using Rich's built-in capabilities
# ABOUTME: Replaces complex log interception with simple spinner progress

from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn


class SimpleProgressTracker:
    """Simple progress tracker with Rich spinner."""

    def __init__(self, progress: Progress, task_id: Any):
        self.progress = progress
        self.task_id = task_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def create_smart_progress(
    console, initial_description: str = "🪄 Invoking magical operations..."
) -> tuple[Progress, Any, SimpleProgressTracker]:
    """Create a simple progress display with spinner.

    Args:
        console: Rich console instance
        initial_description: Initial progress description

    Returns:
        Tuple of (progress, task_id, tracker)
    """
    progress = Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True
    )

    task_id = progress.add_task(initial_description, total=None)
    tracker = SimpleProgressTracker(progress, task_id)

    return progress, task_id, tracker

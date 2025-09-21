# ABOUTME: Tests for simplified progress tracking functionality
# ABOUTME: Validates create_smart_progress function and basic tracker

from rich.console import Console
from rich.progress import Progress

from voiceover_mage.utils.logging.progress import (
    SimpleProgressTracker,
    create_smart_progress,
)


class TestCreateSmartProgress:
    """Test the create_smart_progress function."""

    def test_create_smart_progress(self):
        """Test creation of smart progress system."""
        console = Console()
        initial_description = "🔍 Testing..."

        progress, task_id, tracker = create_smart_progress(console, initial_description)

        assert isinstance(progress, Progress)
        assert task_id is not None
        assert isinstance(tracker, SimpleProgressTracker)
        assert tracker.progress == progress
        assert tracker.task_id == task_id

    def test_create_smart_progress_default_description(self):
        """Test creation with default description."""
        console = Console()

        progress, task_id, tracker = create_smart_progress(console)

        assert isinstance(progress, Progress)
        assert isinstance(tracker, SimpleProgressTracker)

    def test_context_manager(self):
        """Test tracker as context manager."""
        console = Console()
        progress, task_id, tracker = create_smart_progress(console)

        with tracker as ctx_tracker:
            assert ctx_tracker == tracker

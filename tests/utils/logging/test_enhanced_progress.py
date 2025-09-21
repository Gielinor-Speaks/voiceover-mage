# ABOUTME: Tests for enhanced rich-based progress reporting and pipeline dashboard
# ABOUTME: Validates beautiful async operation reporting with real data display

from unittest.mock import Mock, patch

import pytest
from rich.console import Console
from rich.table import Table

from voiceover_mage.utils.logging.enhanced_progress import (
    EnhancedProgressReporter,
    PipelineDashboard,
    PipelineStage,
    StageInfo,
    StageStatus,
    create_rich_table,
    create_stage_status_table,
)


class TestCreateRichTable:
    """Test rich table creation utilities."""

    def test_create_rich_table_basic(self):
        """Test basic rich table creation."""
        table = create_rich_table(
            title="Test Table",
            columns=["Name", "Value"],
            rows=[["Test", "123"]],
        )

        assert isinstance(table, Table)
        assert table.title == "Test Table"
        assert len(table.columns) == 2

    def test_create_rich_table_with_styling(self):
        """Test rich table with custom styling."""
        table = create_rich_table(
            title="🎭 Styled Table",
            columns=[("Name", "cyan"), ("Value", "green")],
            rows=[["Test", "123"]],
            style="bold blue",
        )

        assert isinstance(table, Table)
        assert table.title == "🎭 Styled Table"


class TestPipelineDashboard:
    """Test the pipeline dashboard for live async operation reporting."""

    def test_dashboard_initialization(self):
        """Test dashboard creates with correct initial state."""
        console = Console()
        dashboard = PipelineDashboard(console=console, npc_id=3105, npc_name="Wise Old Man")

        assert dashboard.npc_id == 3105
        assert dashboard.npc_name == "Wise Old Man"
        assert dashboard.console == console
        assert len(dashboard.stages) == 4  # Should have 4 pipeline stages

    def test_stage_progression(self):
        """Test updating stage status and progression."""
        console = Console()
        dashboard = PipelineDashboard(console=console, npc_id=3105, npc_name="Wise Old Man")

        # Start first stage
        dashboard.start_stage(PipelineStage.RAW_EXTRACTION)
        stage = dashboard.stages[PipelineStage.RAW_EXTRACTION]
        assert stage.status == StageStatus.IN_PROGRESS

        # Complete with data
        dashboard.complete_stage(PipelineStage.RAW_EXTRACTION, data={"markdown_chars": 2847, "has_images": True})
        stage = dashboard.stages[PipelineStage.RAW_EXTRACTION]
        assert stage.status == StageStatus.COMPLETED
        assert stage.data["markdown_chars"] == 2847

    def test_stage_error_handling(self):
        """Test stage error state handling."""
        console = Console()
        dashboard = PipelineDashboard(console=console, npc_id=3105, npc_name="Wise Old Man")

        dashboard.start_stage(PipelineStage.VOICE_GENERATION)
        dashboard.error_stage(PipelineStage.VOICE_GENERATION, error="API rate limit exceeded")

        stage = dashboard.stages[PipelineStage.VOICE_GENERATION]
        assert stage.status == StageStatus.ERROR
        assert stage.error_message == "API rate limit exceeded"

    def test_create_dashboard_renderable(self):
        """Test dashboard creates proper renderable for live display."""
        console = Console()
        dashboard = PipelineDashboard(console=console, npc_id=3105, npc_name="Wise Old Man")

        # Set up some stage data
        dashboard.complete_stage(PipelineStage.RAW_EXTRACTION, data={"markdown_chars": 2847})
        dashboard.start_stage(PipelineStage.INTELLIGENT_ANALYSIS)

        renderable = dashboard.create_renderable()
        assert renderable is not None


class TestEnhancedProgressReporter:
    """Test the enhanced progress reporter for async operations."""

    def test_reporter_initialization(self):
        """Test reporter initializes correctly."""
        console = Console()
        reporter = EnhancedProgressReporter(console=console)
        assert reporter.console == console

    @pytest.mark.asyncio
    async def test_run_with_pipeline_dashboard(self):
        """Test running async operation with pipeline dashboard."""
        console = Console()
        reporter = EnhancedProgressReporter(console=console)

        async def mock_pipeline_operation(dashboard):
            """Mock pipeline operation that updates dashboard."""
            dashboard.start_stage(PipelineStage.RAW_EXTRACTION)
            dashboard.complete_stage(PipelineStage.RAW_EXTRACTION, data={"markdown_chars": 1234})
            return "success"

        with patch("voiceover_mage.utils.logging.enhanced_progress.Live") as mock_live:
            mock_live_instance = Mock()
            mock_live.return_value.__enter__.return_value = mock_live_instance
            mock_live.return_value.__exit__.return_value = None

            result = await reporter.run_with_pipeline_dashboard(
                operation=mock_pipeline_operation, npc_id=3105, npc_name="Test NPC"
            )

            assert result == "success"
            mock_live.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_status(self):
        """Test running operation with rich status display."""
        console = Console()
        reporter = EnhancedProgressReporter(console=console)

        async def mock_operation():
            return "completed"

        with patch.object(console, "status") as mock_status:
            result = await reporter.run_with_status(
                operation=mock_operation, message="🔍 Processing...", success_message="✅ Complete"
            )

            assert result == "completed"
            mock_status.assert_called_once()


class TestStageStatusTable:
    """Test stage status table creation."""

    def test_create_stage_status_table(self):
        """Test creating status table for pipeline stages."""
        mock_duration = Mock()
        mock_duration.total_seconds.return_value = 2.5

        mock_elapsed = Mock()
        mock_elapsed.total_seconds.return_value = 1.2

        stages = {
            PipelineStage.RAW_EXTRACTION: StageInfo(
                stage=PipelineStage.RAW_EXTRACTION,
                status=StageStatus.COMPLETED,
                data={"markdown_chars": 2847},
                error_message=None,
            ),
            PipelineStage.INTELLIGENT_ANALYSIS: StageInfo(
                stage=PipelineStage.INTELLIGENT_ANALYSIS,
                status=StageStatus.IN_PROGRESS,
                data={},
                error_message=None,
            ),
            PipelineStage.VOICE_GENERATION: StageInfo(
                stage=PipelineStage.VOICE_GENERATION,
                status=StageStatus.ERROR,
                data={},
                error_message="API Error",
            ),
        }

        table = create_stage_status_table(stages)
        assert isinstance(table, Table)
        assert len(table.columns) == 3  # Stage, Status, Details

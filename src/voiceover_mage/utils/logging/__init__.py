# ABOUTME: Logging configuration, progress tracking, and output formatting
# ABOUTME: Provides rich console output and structured logging for the pipeline

# Import from local files in utils/logging
from .config import LoggingMode, configure_logging, get_logging_status, suppress_library_output
from .enhanced_progress import (
    EnhancedProgressReporter,
    PipelineDashboard,
    PipelineStage,
    StageStatus,
    create_smart_progress,
)
from .progress import SimpleProgressTracker
from .utils import get_logger, log_api_call, log_extraction_step, with_npc_context, with_pipeline_context

__all__ = [
    # Configuration
    "LoggingMode",
    "configure_logging",
    "get_logging_status",
    "suppress_library_output",
    # Enhanced Progress Reporting
    "EnhancedProgressReporter",
    "PipelineDashboard",
    "PipelineStage",
    "StageStatus",
    "create_smart_progress",
    # Legacy Progress (for compatibility)
    "SimpleProgressTracker",
    # Utilities
    "get_logger",
    "log_api_call",
    "log_extraction_step",
    "with_npc_context",
    "with_pipeline_context",
]

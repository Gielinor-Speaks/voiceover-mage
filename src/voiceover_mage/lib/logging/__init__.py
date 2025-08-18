# ABOUTME: Logging infrastructure for dual-mode (interactive/production) operation
# ABOUTME: Exports main components for structured logging and progress tracking

from .config import LoggingMode, configure_logging, get_logging_status, suppress_library_output
from .progress import ProgressLogInterceptor, SmartProgressTracker, create_smart_progress
from .utils import get_logger, log_api_call, log_extraction_step, with_npc_context, with_pipeline_context

__all__ = [
    # Configuration
    "LoggingMode",
    "configure_logging", 
    "get_logging_status",
    "suppress_library_output",
    
    # Progress tracking
    "ProgressLogInterceptor",
    "SmartProgressTracker", 
    "create_smart_progress",
    
    # Utilities
    "get_logger",
    "log_api_call",
    "log_extraction_step", 
    "with_npc_context",
    "with_pipeline_context",
]
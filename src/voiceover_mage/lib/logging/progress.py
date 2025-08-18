# ABOUTME: Smart progress system that intercepts crawl4ai logs for real-time status updates
# ABOUTME: Bridges structured logging with Rich progress displays for beautiful CLI feedback

import logging
import re
from collections.abc import Callable
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn


class ProgressLogInterceptor(logging.Handler):
    """Logging handler that intercepts specific log messages and updates progress displays."""
    
    def __init__(self, progress_callback: Callable[[str, dict[str, Any]], None]):
        """Initialize the interceptor.
        
        Args:
            progress_callback: Function to call with (status_message, context) when progress updates
        """
        super().__init__()
        self.progress_callback = progress_callback
        self._processing = True
        
        # Pattern matching for different operation stages
        self.status_patterns = {
            'lookup': {
                'pattern': r'Looking up NPC page URL',
                'message': '🔍 Finding NPC page...',
                'stage': 'lookup'
            },
            'url_retrieved': {
                'pattern': r'Retrieved NPC page URL',
                'message': '🌐 Found NPC page',
                'stage': 'url_found'
            },
            'configuring_llm': {
                'pattern': r'Configuring LLM extraction strategy',
                'message': '🪄 Configuring AI extraction',
                'stage': 'llm_config'
            },
            'starting_crawl': {
                'pattern': r'Starting web crawling',
                'message': '🕷️ Crawling wiki page',
                'stage': 'crawling'
            },
            'crawling_success': {
                'pattern': r'Crawling successful, parsing extracted content',
                'message': '📝 Processing extracted data',
                'stage': 'processing'
            },
            'parsing_data': {
                'pattern': r'Successfully parsed extraction data',
                'message': '✅ Parsing complete',
                'stage': 'parsed'
            },
            'validating': {
                'pattern': r'Validated NPC data object',
                'message': '🔍 Validating NPC data',
                'stage': 'validating'
            },
            'extraction_complete': {
                'pattern': r'Extraction completed successfully',
                'message': '🎉 Extraction complete!',
                'stage': 'complete'
            },
            'api_success': {
                'pattern': r'API call to crawl4ai succeeded',
                'message': '✅ Operation successful',
                'stage': 'success'
            },
            'extraction_step_start': {
                'pattern': r'Starting extraction step',
                'message': '🔧 Starting extraction',
                'stage': 'starting'
            },
            'extraction_step_complete': {
                'pattern': r'Completed extraction step',
                'message': '✅ Extraction completed',
                'stage': 'completed'
            },
        }
    
    def emit(self, record: logging.LogRecord) -> None:
        """Handle a logging record by checking for progress-relevant messages."""
        if not self._processing:
            return
            
        try:
            # Only process records from our modules
            if not record.name.startswith('voiceover_mage'):
                return
                
            message = self.format(record)
            
            # DEBUG: Uncomment to see all intercepted messages
            # print(f"[INTERCEPTED] {record.name}: {message}")
            
            # Extract context from the structured log message
            context = self._extract_context(message)
            
            # Check each pattern for matches
            matched = False
            for status_name, status_info in self.status_patterns.items():
                if re.search(status_info['pattern'], message):
                    # Found a matching status, notify the progress callback
                    self.progress_callback(status_info['message'], {
                        'stage': status_info['stage'],
                        'status_name': status_name,
                        'level': record.levelname,
                        'module': record.name,
                        **context
                    })
                    matched = True
                    break
            
            # If no pattern matched but it's an interesting message, show a generic update
            # Show generic progress for unmatched messages that look important
            if (
                not matched
                and record.levelname in ['INFO', 'DEBUG']
                and any(
                    keyword in message.lower()
                    for keyword in [
                        'start',
                        'processing',
                        'extract',
                        'crawl',
                        'configur'
                    ]
                )
            ):
                self.progress_callback(
                    f"🔄 {message[:50]}...",
                    {
                        'stage': 'processing',
                        'status_name': 'generic',
                        'level': record.levelname,
                        'module': record.name,
                        **context
                    }
                )
                    
        except Exception:
            # Don't let progress interceptor break the logging system
            pass
    
    def _extract_context(self, message: str) -> dict[str, Any]:
        """Extract useful context from the log record."""
        context = {}
        
        # Extract NPC name if present
        npc_name_match = re.search(r'npc_name[=:]([^\s,}]+)', message)
        if npc_name_match:
            context['npc_name'] = npc_name_match.group(1).strip('\'"')
        
        # Extract duration if present
        duration_match = re.search(r'duration_seconds[=:]([0-9.]+)', message)
        if duration_match:
            context['duration'] = float(duration_match.group(1))
        
        # Extract URLs
        url_match = re.search(r'https?://[^\s,}]+', message)
        if url_match:
            context['url'] = url_match.group(0)
        
        # Extract any numeric IDs
        id_match = re.search(r'npc_id[=:]([0-9]+)', message)
        if id_match:
            context['npc_id'] = int(id_match.group(1))
            
        return context
    
    def stop(self):
        """Stop processing log messages."""
        self._processing = False


class SmartProgressTracker:
    """Progress tracker that updates based on intercepted log messages."""
    
    def __init__(self, progress: Progress, task_id: Any, update_delay: float = 0.3):
        """Initialize the tracker.
        
        Args:
            progress: Rich Progress instance
            task_id: Task ID from the progress instance
            update_delay: Delay in seconds between progress updates (default 0.3s)
        """
        self.progress = progress
        self.task_id = task_id
        self.update_delay = update_delay
        self.current_stage = None
        self.interceptor = None
        
        # Stage progression for better UX
        self.stage_order = [
            'lookup', 'url_found', 'llm_config', 'crawling', 
            'processing', 'parsed', 'validating', 'complete', 'success'
        ]
        
    def start_intercepting(self):
        """Start intercepting log messages for progress updates."""
        if self.interceptor:
            return
            
        self.interceptor = ProgressLogInterceptor(self._update_progress)
        
        # Add to the root voiceover_mage logger to catch all messages from our modules
        voiceover_logger = logging.getLogger('voiceover_mage')
        voiceover_logger.addHandler(self.interceptor)
        
    def stop_intercepting(self):
        """Stop intercepting log messages."""
        if not self.interceptor:
            return
            
        self.interceptor.stop()
        
        # Remove from the logger we added to
        voiceover_logger = logging.getLogger('voiceover_mage')
        voiceover_logger.removeHandler(self.interceptor)
        
        self.interceptor = None
    
    def _update_progress(self, status_message: str, context: dict[str, Any]):
        """Update the progress display with new status."""
        try:
            import time
            stage = context.get('stage', 'unknown')
            
            # Build a rich status message with context
            display_message = status_message
            
            # Add NPC name if available
            if 'npc_name' in context:
                display_message = f"{status_message} ({context['npc_name']})"
            
            # Add duration for completion stages
            if 'duration' in context and stage in ['complete', 'success']:
                duration = context['duration']
                display_message = f"{status_message} ({duration:.1f}s)"
            
            # Update the progress task
            self.progress.update(
                self.task_id,
                description=display_message
            )
            
            # Add a configurable delay so users can see intermediate progress states
            # Only delay for non-completion stages to keep final result snappy
            if stage not in ['complete', 'success', 'completed'] and self.update_delay > 0:
                time.sleep(self.update_delay)
            
            # Track stage progression
            self.current_stage = stage
            
        except Exception:
            # Don't break progress display on errors
            pass
    
    def __enter__(self):
        """Context manager entry."""
        self.start_intercepting()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_intercepting()


def create_smart_progress(
    console, initial_description: str = "🪄 Invoking magical operations..."
) -> tuple[Progress, Any, SmartProgressTracker]:
    """Create a smart progress display with log interception.
    
    Args:
        console: Rich console instance
        initial_description: Initial progress description
        
    Returns:
        Tuple of (progress, task_id, tracker)
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )
    
    task_id = progress.add_task(initial_description, total=None)
    tracker = SmartProgressTracker(progress, task_id, update_delay=0.3)
    
    return progress, task_id, tracker
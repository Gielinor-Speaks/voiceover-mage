# ABOUTME: Tests for progress tracking and log interception functionality
# ABOUTME: Validates smart progress system and log message pattern matching

import logging
from unittest.mock import Mock, patch

import pytest
from rich.console import Console
from rich.progress import Progress

from voiceover_mage.lib.logging.progress import (
    ProgressLogInterceptor,
    SmartProgressTracker,
    create_smart_progress,
)


class TestProgressLogInterceptor:
    """Test the ProgressLogInterceptor class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.callback_mock = Mock()
        self.interceptor = ProgressLogInterceptor(self.callback_mock)
    
    def test_init(self):
        """Test interceptor initialization."""
        assert self.interceptor.progress_callback == self.callback_mock
        assert self.interceptor._processing is True
        assert len(self.interceptor.status_patterns) > 0
    
    def test_pattern_matching_lookup(self):
        """Test pattern matching for NPC lookup stage."""
        record = logging.LogRecord(
            name="voiceover_mage.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Looking up NPC page URL",
            args=(),
            exc_info=None
        )
        
        self.interceptor.emit(record)
        
        self.callback_mock.assert_called_once()
        args, kwargs = self.callback_mock.call_args
        assert args[0] == "🔍 Finding NPC page..."
        assert args[1]["stage"] == "lookup"
    
    def test_pattern_matching_url_retrieved(self):
        """Test pattern matching for URL retrieved stage."""
        record = logging.LogRecord(
            name="voiceover_mage.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Retrieved NPC page URL npc_name=Hans npc_id=3105",
            args=(),
            exc_info=None
        )
        
        self.interceptor.emit(record)
        
        self.callback_mock.assert_called_once()
        args, kwargs = self.callback_mock.call_args
        assert args[0] == "🌐 Found NPC page"
        assert args[1]["stage"] == "url_found"
        assert args[1]["npc_name"] == "Hans"
        assert args[1]["npc_id"] == 3105
    
    def test_pattern_matching_extraction_complete(self):
        """Test pattern matching for extraction complete stage."""
        record = logging.LogRecord(
            name="voiceover_mage.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Extraction completed successfully duration_seconds=5.42",
            args=(),
            exc_info=None
        )
        
        self.interceptor.emit(record)
        
        self.callback_mock.assert_called_once()
        args, kwargs = self.callback_mock.call_args
        assert args[0] == "🎉 Extraction complete!"
        assert args[1]["stage"] == "complete"
        assert args[1]["duration"] == 5.42
    
    def test_ignore_non_voiceover_mage_modules(self):
        """Test that non-voiceover_mage modules are ignored."""
        record = logging.LogRecord(
            name="other.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Looking up NPC page URL",
            args=(),
            exc_info=None
        )
        
        self.interceptor.emit(record)
        
        self.callback_mock.assert_not_called()
    
    def test_extract_context_npc_name(self):
        """Test context extraction for NPC name."""
        message = "Retrieved NPC page URL npc_name=Hans"
        context = self.interceptor._extract_context(message)
        assert context["npc_name"] == "Hans"
    
    def test_extract_context_duration(self):
        """Test context extraction for duration."""
        message = "Operation completed duration_seconds=3.14"
        context = self.interceptor._extract_context(message)
        assert context["duration"] == 3.14
    
    def test_extract_context_url(self):
        """Test context extraction for URL."""
        message = "Found page at https://example.com/test"
        context = self.interceptor._extract_context(message)
        assert context["url"] == "https://example.com/test"
    
    def test_extract_context_npc_id(self):
        """Test context extraction for NPC ID."""
        message = "Processing npc_id=1234"
        context = self.interceptor._extract_context(message)
        assert context["npc_id"] == 1234
    
    def test_stop_processing(self):
        """Test stopping the interceptor."""
        self.interceptor.stop()
        assert self.interceptor._processing is False
        
        record = logging.LogRecord(
            name="voiceover_mage.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Looking up NPC page URL",
            args=(),
            exc_info=None
        )
        
        self.interceptor.emit(record)
        self.callback_mock.assert_not_called()
    
    def test_exception_handling(self):
        """Test that exceptions in emit() don't break the system."""
        # Create interceptor with broken callback
        broken_callback = Mock(side_effect=Exception("Test exception"))
        interceptor = ProgressLogInterceptor(broken_callback)
        
        record = logging.LogRecord(
            name="voiceover_mage.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Looking up NPC page URL",
            args=(),
            exc_info=None
        )
        
        # Should not raise exception
        interceptor.emit(record)


class TestSmartProgressTracker:
    """Test the SmartProgressTracker class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.progress_mock = Mock(spec=Progress)
        self.task_id = "test_task"
        self.tracker = SmartProgressTracker(self.progress_mock, self.task_id)
    
    def test_init(self):
        """Test tracker initialization."""
        assert self.tracker.progress == self.progress_mock
        assert self.tracker.task_id == self.task_id
        assert self.tracker.current_stage is None
        assert self.tracker.interceptor is None
    
    @patch('logging.getLogger')
    def test_start_intercepting(self, mock_get_logger):
        """Test starting log interception."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        self.tracker.start_intercepting()
        
        assert self.tracker.interceptor is not None
        assert mock_logger.addHandler.called
    
    @patch('logging.getLogger')
    def test_stop_intercepting(self, mock_get_logger):
        """Test stopping log interception."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # First start intercepting
        self.tracker.start_intercepting()
        interceptor = self.tracker.interceptor
        
        # Then stop
        self.tracker.stop_intercepting()
        
        assert self.tracker.interceptor is None
        assert mock_logger.removeHandler.called
        assert interceptor._processing is False
    
    def test_update_progress_basic(self):
        """Test basic progress update."""
        status_message = "🔍 Finding NPC page..."
        context = {"stage": "lookup", "status_name": "lookup"}
        
        self.tracker._update_progress(status_message, context)
        
        self.progress_mock.update.assert_called_once_with(
            self.task_id,
            description=status_message
        )
        assert self.tracker.current_stage == "lookup"
    
    def test_update_progress_with_npc_name(self):
        """Test progress update with NPC name context."""
        status_message = "🌐 Found NPC page"
        context = {"stage": "url_found", "npc_name": "Hans"}
        
        self.tracker._update_progress(status_message, context)
        
        expected_message = "🌐 Found NPC page (Hans)"
        self.progress_mock.update.assert_called_once_with(
            self.task_id,
            description=expected_message
        )
    
    def test_update_progress_with_duration(self):
        """Test progress update with duration context."""
        status_message = "🎉 Extraction complete!"
        context = {"stage": "complete", "duration": 5.42}
        
        self.tracker._update_progress(status_message, context)
        
        expected_message = "🎉 Extraction complete! (5.4s)"
        self.progress_mock.update.assert_called_once_with(
            self.task_id,
            description=expected_message
        )
    
    def test_update_progress_exception_handling(self):
        """Test that progress update exceptions are handled gracefully."""
        self.progress_mock.update.side_effect = Exception("Test exception")
        
        status_message = "🔍 Finding NPC page..."
        context = {"stage": "lookup"}
        
        # Should not raise exception
        self.tracker._update_progress(status_message, context)
    
    @patch('logging.getLogger')
    def test_context_manager(self, mock_get_logger):
        """Test tracker as context manager."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with self.tracker as tracker:
            assert tracker == self.tracker
            assert self.tracker.interceptor is not None
        
        assert self.tracker.interceptor is None


class TestCreateSmartProgress:
    """Test the create_smart_progress function."""
    
    def test_create_smart_progress(self):
        """Test creation of smart progress system."""
        console = Console()
        initial_description = "🔍 Testing..."
        
        progress, task_id, tracker = create_smart_progress(console, initial_description)
        
        assert isinstance(progress, Progress)
        assert task_id is not None
        assert isinstance(tracker, SmartProgressTracker)
        assert tracker.progress == progress
        assert tracker.task_id == task_id
    
    def test_create_smart_progress_default_description(self):
        """Test creation with default description."""
        console = Console()
        
        progress, task_id, tracker = create_smart_progress(console)
        
        assert isinstance(progress, Progress)
        assert isinstance(tracker, SmartProgressTracker)


class TestIntegration:
    """Integration tests for the progress system."""
    
    @patch('logging.getLogger')
    def test_full_progress_flow(self, mock_get_logger):
        """Test complete progress flow from log message to UI update."""
        console = Console()
        progress, task_id, tracker = create_smart_progress(console, "🧙‍♂️ Invoking magical operations...")
        
        # Mock the logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch.object(progress, 'update') as mock_update, tracker:
            # Simulate log message
            interceptor = tracker.interceptor
            record = logging.LogRecord(
                name="voiceover_mage.test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Looking up NPC page URL npc_name=TestNPC",
                args=(),
                exc_info=None
            )
            
            interceptor.emit(record)
            
            # Verify progress was updated
            mock_update.assert_called()
            call_args = mock_update.call_args
            assert "Finding NPC page" in call_args[1]["description"]
            assert "(TestNPC)" in call_args[1]["description"]
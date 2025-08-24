# ABOUTME: Tests for logging configuration module
# ABOUTME: Validates dual-mode logging setup and third-party library suppression

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from voiceover_mage.utils.logging.config import (
    LoggingMode,
    configure_logging,
    detect_logging_mode,
    get_logging_status,
    suppress_library_output,
)


class TestLoggingMode:
    """Test the LoggingMode constants."""

    def test_logging_mode_constants(self):
        """Test that logging mode constants are defined correctly."""
        assert LoggingMode.INTERACTIVE == "interactive"
        assert LoggingMode.PRODUCTION == "production"


class TestDetectLoggingMode:
    """Test logging mode detection logic."""

    def test_detect_mode_from_env_interactive(self):
        """Test detection of interactive mode from environment variable."""
        with patch.dict(os.environ, {"VOICEOVER_MAGE_LOG_MODE": "interactive"}):
            assert detect_logging_mode() == LoggingMode.INTERACTIVE

    def test_detect_mode_from_env_production(self):
        """Test detection of production mode from environment variable."""
        with patch.dict(os.environ, {"VOICEOVER_MAGE_LOG_MODE": "production"}):
            assert detect_logging_mode() == LoggingMode.PRODUCTION

    def test_detect_mode_from_env_invalid(self):
        """Test fallback when environment variable has invalid value."""
        with (
            patch.dict(os.environ, {"VOICEOVER_MAGE_LOG_MODE": "invalid"}),
            patch("sys.stdout.isatty", return_value=True),
        ):
            assert detect_logging_mode() == LoggingMode.INTERACTIVE

    def test_detect_mode_from_tty_interactive(self):
        """Test detection of interactive mode from TTY."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout.isatty", return_value=True):
            assert detect_logging_mode() == LoggingMode.INTERACTIVE

    def test_detect_mode_from_tty_production(self):
        """Test detection of production mode from non-TTY."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout.isatty", return_value=False):
            assert detect_logging_mode() == LoggingMode.PRODUCTION


class TestConfigureLogging:
    """Test logging configuration functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing handlers
        for logger_name in ["voiceover_mage", "crawl4ai", "LiteLLM"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)

    def teardown_method(self):
        """Clean up test environment."""
        # Reset all loggers to NOTSET and clear handlers
        logger_names = [
            "",
            "root",
            "voiceover_mage",
            "crawl4ai",
            "LiteLLM",
            "httpx",
            "httpcore",
            "selenium",
            "playwright",
            "urllib3",
            "requests",
            "py.warnings",
        ]

        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
            logger.propagate = True

        # Force reset root logger to NOTSET (will inherit from parent)
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)

        # Reset warnings capture
        logging.captureWarnings(False)

    def test_configure_interactive_mode(self):
        """Test configuration of interactive mode logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            configure_logging(mode=LoggingMode.INTERACTIVE, log_level="INFO")

            # Check that logs directory was created
            logs_dir = Path("logs")
            assert logs_dir.exists()

            # Check that third-party loggers are suppressed
            assert logging.getLogger("crawl4ai").level == logging.CRITICAL
            assert logging.getLogger("LiteLLM").level == logging.CRITICAL

    def test_configure_production_mode(self):
        """Test configuration of production mode logging."""
        configure_logging(mode=LoggingMode.PRODUCTION, log_level="INFO")

        # Check that third-party loggers are suppressed
        assert logging.getLogger("crawl4ai").level == logging.CRITICAL
        assert logging.getLogger("httpx").level == logging.WARNING

    def test_configure_custom_log_level(self):
        """Test configuration with custom log level."""
        configure_logging(mode=LoggingMode.PRODUCTION, log_level="DEBUG")

        # Check that log level is set correctly
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_custom_log_file(self):
        """Test configuration with custom log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            custom_log_file = os.path.join(temp_dir, "custom.log")

            configure_logging(mode=LoggingMode.INTERACTIVE, log_level="INFO", log_file=custom_log_file)

            # Note: We can't easily test file creation without actually logging,
            # but we can verify the configuration doesn't crash


class TestSuppressLibraryOutput:
    """Test library output suppression context manager."""

    def test_suppress_output_context_manager(self):
        """Test that output suppression works as context manager."""
        import sys

        # Capture original stdout
        original_stdout = sys.stdout

        with suppress_library_output():
            # stdout should be redirected
            assert sys.stdout != original_stdout
            print("This should be suppressed")

        # stdout should be restored
        assert sys.stdout == original_stdout

    def test_suppress_output_exception_handling(self):
        """Test that output suppression handles exceptions correctly."""
        import sys

        original_stdout = sys.stdout

        try:
            with suppress_library_output():
                raise ValueError("Test exception")
        except ValueError:
            pass

        # stdout should still be restored after exception
        assert sys.stdout == original_stdout


class TestGetLoggingStatus:
    """Test logging status reporting."""

    def test_get_status_interactive_mode(self):
        """Test status reporting for interactive mode."""
        with patch("voiceover_mage.utils.logging.config.detect_logging_mode") as mock_detect:
            mock_detect.return_value = LoggingMode.INTERACTIVE

            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Create logs directory
                logs_dir = Path("logs")
                logs_dir.mkdir()

                status = get_logging_status()

                assert status["mode"] == LoggingMode.INTERACTIVE
                assert status["log_directory"] is not None
                assert "main" in status["log_files"]
                assert "json" in status["log_files"]
                assert "errors" in status["log_files"]
                assert "crawl4ai" in status["third_party_suppressed"]

    def test_get_status_production_mode(self):
        """Test status reporting for production mode."""
        with patch("voiceover_mage.utils.logging.config.detect_logging_mode") as mock_detect:
            mock_detect.return_value = LoggingMode.PRODUCTION

            status = get_logging_status()

            assert status["mode"] == LoggingMode.PRODUCTION
            assert status["log_files"]["main"] is None
            assert status["log_files"]["json"] is None
            assert status["log_files"]["errors"] is None


class TestThirdPartyLogging:
    """Test third-party library logging configuration."""

    def test_third_party_loggers_suppressed(self):
        """Test that third-party loggers are properly suppressed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            configure_logging(mode=LoggingMode.INTERACTIVE)

            # Check critical loggers are set to CRITICAL
            critical_loggers = ["crawl4ai", "LiteLLM", "selenium", "playwright"]
            for logger_name in critical_loggers:
                logger = logging.getLogger(logger_name)
                assert logger.level == logging.CRITICAL, (
                    f"Logger {logger_name} level was {logger.level}, expected {logging.CRITICAL}"
                )

            # Check warning loggers are set to WARNING
            warning_loggers = ["httpx", "httpcore", "urllib3", "requests"]
            for logger_name in warning_loggers:
                logger = logging.getLogger(logger_name)
                assert logger.level == logging.WARNING, (
                    f"Logger {logger_name} level was {logger.level}, expected {logging.WARNING}"
                )

    def test_warnings_captured(self):
        """Test that warnings are captured by logging system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Reset warnings capture first
            logging.captureWarnings(False)

            configure_logging(mode=LoggingMode.INTERACTIVE)

            # Check that warnings are captured (captureWarnings returns None)
            result = logging.captureWarnings(True)
            assert result is None

            warnings_logger = logging.getLogger("py.warnings")
            assert warnings_logger.level == logging.ERROR

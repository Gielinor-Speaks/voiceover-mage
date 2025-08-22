"""Basic tests for voiceover-mage main module."""

from unittest.mock import Mock

import pytest
import typer
from src.voiceover_mage.main import main


def test_main_function_exists():
    """Test that the main function exists and is callable."""
    assert callable(main)


def test_main_function_output(capsys):
    """Test that main function produces expected output."""
    # Create a mock context
    ctx = Mock(spec=typer.Context)
    ctx.ensure_object = Mock(return_value=dict())
    ctx.obj = {}

    # Call main with production mode to avoid creating log directories during tests
    main(ctx, json_output=True, log_level="INFO", log_file=None)
    captured = capsys.readouterr()
    # Main function is a callback that doesn't output directly
    assert captured.out == ""


def test_main_function_no_exceptions():
    """Test that main function runs without raising exceptions."""
    # Create a mock context
    ctx = Mock(spec=typer.Context)
    ctx.ensure_object = Mock(return_value=dict())
    ctx.obj = {}

    try:
        # Call main with production mode to avoid creating log directories during tests
        main(ctx, json_output=True, log_level="INFO", log_file=None)
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")


def test_main_returns_none():
    """Test that main function returns None (standard for main functions)."""
    # Create a mock context
    ctx = Mock(spec=typer.Context)
    ctx.ensure_object = Mock(return_value=dict())
    ctx.obj = {}

    # Call main with production mode to avoid creating log directories during tests
    result = main(ctx, json_output=True, log_level="INFO", log_file=None)
    assert result is None

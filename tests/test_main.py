"""Basic tests for voiceover-mage main module."""

import pytest
from src.voiceover_mage.main import main


def test_main_function_exists():
    """Test that the main function exists and is callable."""
    assert callable(main)


def test_main_function_output(capsys):
    """Test that main function produces expected output."""
    main()
    captured = capsys.readouterr()
    assert "Hello from voiceover-mage!" in captured.out


def test_main_function_no_exceptions():
    """Test that main function runs without raising exceptions."""
    try:
        main()
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")


def test_main_returns_none():
    """Test that main function returns None (standard for main functions)."""
    result = main()
    assert result is None
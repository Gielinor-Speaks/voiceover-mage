"""Basic tests for voiceover-mage main module."""

import pytest

from voiceover_mage.main import mage as main


def test_main_function_exists():
    """Test that the main function exists and is callable."""
    assert callable(main)


@pytest.mark.asyncio
async def test_main_command_help():
    """Test that main command can show help."""
    # Test using the Click testing framework
    from asyncclick.testing import CliRunner

    runner = CliRunner()
    result = await runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Voiceover Mage" in result.output


@pytest.mark.asyncio
async def test_main_with_system_status():
    """Test that system status command works."""
    from asyncclick.testing import CliRunner

    runner = CliRunner()
    result = await runner.invoke(main, ["system", "status"])

    assert result.exit_code == 0
    assert "Logging" in result.output or "System" in result.output

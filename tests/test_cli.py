"""Tests for the `cli` module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from insiders._internal import cli, debug

if TYPE_CHECKING:
    import pytest


def test_main() -> None:
    """Basic CLI test."""
    assert cli.main([]) == 2


def test_show_help(capsys: pytest.CaptureFixture) -> None:
    """Show help.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert cli.main(["-h"]) == 0
    captured = capsys.readouterr()
    assert "insiders" in captured.out


def test_show_version(capsys: pytest.CaptureFixture) -> None:
    """Show version.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert cli.main(["-V"]) == 0
    captured = capsys.readouterr()
    assert debug.get_version() in captured.out


def test_show_debug_info(capsys: pytest.CaptureFixture) -> None:
    """Show debug information.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    assert cli.main(["--debug-info"]) == 0
    captured = capsys.readouterr().out.lower()
    assert "python" in captured
    assert "system" in captured
    assert "environment" in captured
    assert "packages" in captured

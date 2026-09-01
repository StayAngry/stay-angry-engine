"""Unit and integration test suite for SAE CLI entrypoint."""

import pytest
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Helper to execute CLI directly via subprocess."""
    cmd = [sys.executable, "sae_cli.py", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_menu():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "Cinematic Video Intelligence & Autonomous Editing Engine CLI" in result.stdout
    assert "analyze" in result.stdout
    assert "process" in result.stdout
    assert "verify" in result.stdout


def test_cli_analyze_help():
    result = run_cli("analyze", "--help")
    assert result.returncode == 0
    assert "media_path" in result.stdout


def test_cli_analyze_missing_file():
    result = run_cli("analyze", "non_existent_video_file.mp4")
    assert result.returncode == 1
    assert "Asset not found" in result.stderr


def test_cli_process_help():
    result = run_cli("process", "--help")
    assert result.returncode == 0
    assert "--look" in result.stdout
    assert "--format" in result.stdout
    assert "--duration" in result.stdout


def test_cli_process_missing_file():
    result = run_cli("process", "missing_input.mp4")
    assert result.returncode == 1
    assert "Asset not found" in result.stderr


def test_cli_verify_help():
    result = run_cli("verify", "--help")
    assert result.returncode == 0
    assert "rendered_file" in result.stdout
    assert "--width" in result.stdout
    assert "--height" in result.stdout
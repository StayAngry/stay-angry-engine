"""Test suite validating CLI direct orchestration command."""

import subprocess
import sys


def test_cli_help_displays_direct_command():
    res = subprocess.run(
        [sys.executable, "sae_cli.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "direct" in res.stdout
    assert "DirectorPipeline" in res.stdout


def test_cli_direct_mock_execution():
    cmd = [
        sys.executable,
        "sae_cli.py",
        "direct",
        "--title", "CLI Smoke Test Reel",
        "--duration", "4.0",
        "--style", "DARK_MANHWA",
        "--transcript", "UNLEASH", "SHADOWS",
        "--mock-render",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "[+] Direct synthesis complete!" in res.stdout
    assert "Pipeline ID: dir_" in res.stdout
    assert "Loudness Calibrated: True" in res.stdout

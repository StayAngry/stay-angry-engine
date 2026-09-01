"""CLI integration test suite verifying end-to-end command execution."""

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "sae_cli.py", *args],
        capture_output=True,
        text=True,
    )


def test_cli_help() -> None:
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "Cinematic Video Intelligence & Autonomous Editing Engine CLI" in proc.stdout
    assert "export" in proc.stdout


def test_cli_export_davinci_dry_run() -> None:
    proc = run_cli("export", "--target", "davinci", "--title", "CLI Resolve Test", "--dry-run")
    assert proc.returncode == 0
    assert "Dry run export successful" in proc.stdout


def test_cli_export_premiere_file(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    proc = run_cli("export", "--target", "premiere", "--title", "CLI Premiere Test", "--output-dir", str(export_dir))
    assert proc.returncode == 0
    assert "Project successfully exported to" in proc.stdout

    exported_files = list(export_dir.glob("*.xml"))
    assert len(exported_files) == 1
    assert exported_files[0].exists()
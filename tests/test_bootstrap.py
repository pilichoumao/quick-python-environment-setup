from __future__ import annotations

import subprocess
import sys


def test_module_help_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "quick_env_setup", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: quick-env-setup [-h]" in result.stdout


def test_cli_parser_identity() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from quick_env_setup.cli import build_parser; print(build_parser().prog)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "quick-env-setup"

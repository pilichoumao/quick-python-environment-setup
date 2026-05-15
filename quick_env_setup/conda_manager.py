from __future__ import annotations

from pathlib import Path

from quick_env_setup.mirror_manager import pip_args_for_mirror
from quick_env_setup.models import MirrorConfig


def build_conda_create_command(env_name: str, python_version: str) -> list[str]:
    return ["conda", "create", "-n", env_name, f"python={python_version}", "-y"]


def build_conda_pip_install_command(
    env_name: str,
    requirements_file: Path,
    mirror_config: MirrorConfig | None = None,
) -> list[str]:
    command = [
        "conda",
        "run",
        "-n",
        env_name,
        "python",
        "-m",
        "pip",
        "install",
    ]
    command.extend(pip_args_for_mirror(mirror_config))
    command.extend(["-r", str(requirements_file)])
    return command

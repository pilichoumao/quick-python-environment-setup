from __future__ import annotations

from pathlib import Path

from quick_env_setup.mirror_manager import pip_args_for_mirror
from quick_env_setup.models import MirrorConfig, OsName


def build_venv_create_command(
    env_path: Path,
    python_executable: str = "python3",
) -> list[str]:
    return [python_executable, "-m", "venv", str(env_path)]


def compose_venv_python_path(env_path: Path, os_name: OsName) -> Path:
    if os_name == "windows":
        return env_path / "Scripts" / "python.exe"
    return env_path / "bin" / "python"


def compose_venv_pip_path(env_path: Path, os_name: OsName) -> Path:
    if os_name == "windows":
        return env_path / "Scripts" / "pip.exe"
    return env_path / "bin" / "pip"


def build_venv_pip_install_command(
    env_path: Path,
    requirements_file: Path,
    os_name: OsName,
    mirror_config: MirrorConfig | None = None,
) -> list[str]:
    command = [
        str(compose_venv_python_path(env_path, os_name=os_name)),
        "-m",
        "pip",
        "install",
    ]
    command.extend(pip_args_for_mirror(mirror_config))
    command.extend(["-r", str(requirements_file)])
    return command

from __future__ import annotations

import platform
import shutil
from typing import Callable

from quick_env_setup.models import OsName, SystemInfo


WhichFunction = Callable[[str], str | None]


def map_os_name(raw_system: str) -> OsName:
    normalized = raw_system.strip().lower()
    mapping = {
        "darwin": "macos",
        "linux": "linux",
        "windows": "windows",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported operating system: {raw_system}") from exc


def detect_architecture(raw_machine: str) -> str:
    normalized = raw_machine.strip().lower()
    if normalized in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if normalized in {"arm64", "aarch64"}:
        return "arm64"
    return normalized


def detect_apple_silicon(os_name: str, arch: str) -> bool:
    return os_name == "macos" and arch == "arm64"


def command_exists(command: str, which: WhichFunction = shutil.which) -> bool:
    return which(command) is not None


def detect_git_presence(which: WhichFunction = shutil.which) -> bool:
    return command_exists("git", which=which)


def detect_conda_presence(which: WhichFunction = shutil.which) -> bool:
    return command_exists("conda", which=which)


def detect_system_info(
    *,
    system_name: str | None = None,
    machine: str | None = None,
    which: WhichFunction = shutil.which,
    python_executables: list[str] | None = None,
) -> SystemInfo:
    resolved_os = map_os_name(system_name or platform.system())
    resolved_arch = detect_architecture(machine or platform.machine())
    return SystemInfo(
        os_name=resolved_os,
        arch=resolved_arch,
        is_apple_silicon=detect_apple_silicon(resolved_os, resolved_arch),
        has_conda=detect_conda_presence(which=which),
        has_git=detect_git_presence(which=which),
        python_executables=list(python_executables or []),
    )

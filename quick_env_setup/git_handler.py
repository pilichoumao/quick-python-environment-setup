from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from quick_env_setup.models import SourceSpec


def derive_clone_directory_name(source: SourceSpec) -> str:
    normalized = source.normalized.rstrip("/")
    if source.source_type != "git_url":
        raise ValueError("Clone directory name requires a git_url source")

    if normalized.startswith("git@"):
        name = normalized.rsplit("/", 1)[-1]
    else:
        name = Path(urlparse(normalized).path).name

    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        raise ValueError(f"Could not derive repository name from {source.normalized}")
    return name


def select_clone_target_path(source: SourceSpec, parent_directory: Path) -> Path:
    return parent_directory / derive_clone_directory_name(source)


def detect_clone_conflict(target_path: Path) -> str | None:
    if target_path.exists():
        return str(target_path)
    return None


def build_clone_command(repo_url: str, target_path: Path) -> list[str]:
    return ["git", "clone", repo_url, str(target_path)]

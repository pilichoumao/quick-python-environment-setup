from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


LOG_DIR_NAME = ".env_setup_logs"


def ensure_log_dir(base_dir: Path) -> Path:
    log_dir = base_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def artifact_path(base_dir: Path, filename: str) -> Path:
    return ensure_log_dir(base_dir) / filename


def append_command_log_line(
    log_path: Path,
    command_line: str,
    *,
    timestamp: datetime | None = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    when = timestamp or datetime.now(timezone.utc)
    line = f"{when.isoformat()} {command_line}\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)

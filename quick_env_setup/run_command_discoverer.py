from __future__ import annotations

import re
from pathlib import Path

from quick_env_setup.models import ProjectScanResult


README_COMMAND_RE = re.compile(
    r"^\s*(python(?:3)?\s+[^\n#]+|python(?:3)?\s+-m\s+[^\n#]+|uvicorn\s+[^\n#]+|streamlit\s+run\s+[^\n#]+|gradio\s+[^\n#]+)\s*$",
    re.IGNORECASE,
)
LIKELY_ENTRYPOINT_NAMES = {
    "app.py",
    "main.py",
    "run.py",
    "serve.py",
    "demo.py",
    "infer.py",
    "inference.py",
    "train.py",
    "cli.py",
}


def discover_run_candidates(project_scan: ProjectScanResult) -> list[str]:
    candidates: list[str] = []
    candidates.extend(_discover_from_readme(project_scan.readme_path))
    candidates.extend(_discover_from_entrypoints(project_scan))
    return _dedupe_preserving_order(candidates)


def _discover_from_readme(readme_path: Path | None) -> list[str]:
    if readme_path is None:
        return []

    try:
        text = readme_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    matches: list[str] = []
    for raw_line in text.splitlines():
        match = README_COMMAND_RE.match(raw_line)
        if match is not None:
            matches.append(match.group(1).strip())
    return matches


def _discover_from_entrypoints(project_scan: ProjectScanResult) -> list[str]:
    candidates: list[str] = []
    for entrypoint in project_scan.python_entry_candidates:
        normalized = entrypoint.replace("\\", "/")
        if normalized.endswith("/__main__.py"):
            package_name = _package_name_for_main(normalized)
            if package_name:
                candidates.append(f"python -m {package_name}")
            continue

        basename = Path(normalized).name
        if basename in LIKELY_ENTRYPOINT_NAMES:
            candidates.append(f"python {normalized}")
    return candidates


def _package_name_for_main(relative_path: str) -> str | None:
    path = Path(relative_path)
    parts = path.parts[:-1]
    if not parts:
        return None
    if len(parts) >= 2 and parts[0] == "src":
        parts = parts[1:]
    if not parts or any(not part.isidentifier() for part in parts):
        return None
    return ".".join(parts)


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from quick_env_setup.models import ProjectScanResult


IGNORED_DIRECTORIES = {".git", ".venv", ".env_setup_logs", "__pycache__", "node_modules"}
DEPENDENCY_FILE_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.in",
    "environment.yml",
    "environment.yaml",
    "conda.yml",
    "conda.yaml",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
}
README_FILE_NAMES = {"readme.md", "readme.rst", "readme.txt"}
ENTRYPOINT_FILE_NAMES = {
    "app.py",
    "cli.py",
    "main.py",
    "manage.py",
    "run.py",
    "serve.py",
    "train.py",
}
KEYWORD_MARKERS: dict[str, tuple[str, ...]] = {
    "torch": ("torch",),
    "pytorch": ("pytorch",),
    "training": ("train.py", "training", "trainer", "fit("),
    "fastapi": ("fastapi",),
    "flask": ("flask",),
    "django": ("django",),
    "uvicorn": ("uvicorn",),
    "jupyter": ("jupyter",),
    "notebook": (".ipynb", "notebook"),
    "streamlit": ("streamlit",),
    "gradio": ("gradio",),
    "package": ("pyproject.toml", "setup.cfg", "setup.py", "build-system"),
    "setuptools": ("setuptools",),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
}


def scan_project(root: Path) -> ProjectScanResult:
    project_root = root.expanduser().resolve()
    detected_files: list[Path] = []
    dependency_files: list[Path] = []
    notebook_paths: list[Path] = []
    python_entry_candidates: list[str] = []
    keywords: set[str] = set()
    readme_path: Path | None = None
    dependency_packages: set[str] = set()

    for path in _iter_project_files(project_root):
        detected_files.append(path)
        relative_name = path.relative_to(project_root).as_posix()
        lower_name = path.name.lower()

        if lower_name in README_FILE_NAMES and readme_path is None:
            readme_path = path

        if lower_name in DEPENDENCY_FILE_NAMES:
            dependency_files.append(path)
            dependency_packages.update(_extract_dependency_packages(path))

        if path.suffix == ".ipynb":
            notebook_paths.append(path)

        if path.suffix == ".py" and _is_python_entry_candidate(path, project_root):
            python_entry_candidates.append(relative_name)

        keywords.update(_detect_keywords(relative_name, _read_text_if_reasonable(path)))

    keywords.update(dependency_packages)
    if "torch" in keywords:
        keywords.add("pytorch")

    parsed_dependency_hints: dict[str, Any] = {
        "packages": sorted(dependency_packages),
        "has_pyproject": any(path.name == "pyproject.toml" for path in dependency_files),
        "has_requirements_txt": any(path.name == "requirements.txt" for path in dependency_files),
    }

    return ProjectScanResult(
        root=project_root,
        detected_files=sorted(detected_files),
        dependency_files=sorted(dependency_files),
        readme_path=readme_path,
        python_entry_candidates=sorted(python_entry_candidates),
        notebook_paths=sorted(notebook_paths),
        keywords=keywords,
        parsed_dependency_hints=parsed_dependency_hints,
    )


def _iter_project_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in root.walk():
        dirnames[:] = sorted(
            name for name in dirnames if name not in IGNORED_DIRECTORIES
        )
        for filename in sorted(filenames):
            files.append(current_root / filename)
    return files


def _is_python_entry_candidate(path: Path, root: Path) -> bool:
    if path.name == "__main__.py":
        return True
    if path.name in ENTRYPOINT_FILE_NAMES:
        return True
    return path.parent == root and path.suffix == ".py"


def _read_text_if_reasonable(path: Path) -> str:
    if path.suffix not in {".py", ".pyi", ".txt", ".md", ".rst", ".toml", ".cfg", ".yml", ".yaml", ".ipynb"}:
        return ""
    try:
        if path.stat().st_size > 200_000:
            return ""
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _detect_keywords(relative_name: str, text: str) -> set[str]:
    haystack = f"{relative_name.lower()}\n{text.lower()}"
    found = {
        keyword
        for keyword, markers in KEYWORD_MARKERS.items()
        if any(marker in haystack for marker in markers)
    }
    return found


def _extract_dependency_packages(path: Path) -> set[str]:
    if path.name == "pyproject.toml":
        return _extract_pyproject_dependency_packages(path)

    text = _read_text_if_reasonable(path)
    packages: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if path.name == "pyproject.toml" and "=" not in line and "[" in line:
            continue
        candidate = _normalize_requirement_name(line)
        if candidate:
            packages.add(candidate)
    return packages


def _extract_pyproject_dependency_packages(path: Path) -> set[str]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return set()

    project = data.get("project")
    if not isinstance(project, dict):
        return set()

    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        return set()

    packages: set[str] = set()
    for item in dependencies:
        if isinstance(item, str):
            candidate = _normalize_requirement_name(item)
            if candidate:
                packages.add(candidate)
    return packages


def _normalize_requirement_name(line: str) -> str | None:
    if line.startswith("-"):
        return None
    normalized = line.strip().strip("\"'").lower()
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", ",", "="):
        if separator in normalized:
            normalized = normalized.split(separator, 1)[0].strip()
            break
    normalized = normalized.replace("_", "-")
    if not normalized:
        return None
    if any(character.isspace() for character in normalized):
        normalized = normalized.split()[0]
    if not normalized.replace("-", "").replace(".", "").isalnum():
        return None
    return normalized

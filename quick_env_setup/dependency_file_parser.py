from __future__ import annotations

from configparser import ConfigParser, Error as ConfigParserError
from dataclasses import dataclass
from pathlib import Path
import re
import tomllib

from quick_env_setup.models import PythonRequirementSource


_PYTHON_VERSION_RE = re.compile(r"(?<!\d)(3(?:\.\d+){1,2})(?!\d)")
_README_PATTERNS = (
    re.compile(
        r"requires?\s+python\s*[:>= ]+\s*v?(3(?:\.\d+){1,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:needs|supports?|tested\s+with|compatible\s+with|works\s+with)\s+python\s*[:>= ]+\s*v?(3(?:\.\d+){1,2})",
        re.IGNORECASE,
    ),
)


@dataclass(slots=True)
class ParsedDependencyFile:
    path: Path
    source: PythonRequirementSource
    packages: list[str]
    python_version: str | None
    rationale: str | None


def parse_dependency_files(paths: list[Path]) -> list[ParsedDependencyFile]:
    return [parsed for path in paths if (parsed := parse_dependency_file(path)) is not None]


def parse_dependency_file(path: Path) -> ParsedDependencyFile | None:
    parser = _PARSERS_BY_NAME.get(path.name.lower())
    if parser is None:
        return None
    return parser(path)


def parse_readme_python_version(path: Path) -> str | None:
    text = _read_text(path)
    if not text:
        return None
    for pattern in _README_PATTERNS:
        match = pattern.search(text)
        if match:
            return _normalize_python_version(match.group(1))
    return None


def _parse_requirements_txt(path: Path) -> ParsedDependencyFile:
    packages: list[str] = []
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if package := _normalize_package_name(line):
            packages.append(package)
    return ParsedDependencyFile(
        path=path,
        source="default",
        packages=sorted(set(packages)),
        python_version=None,
        rationale=None,
    )


def _parse_conda_environment_file(path: Path) -> ParsedDependencyFile:
    packages: list[str] = []
    python_version: str | None = None

    for raw_line in _read_text(path).splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        dependency = _extract_yaml_list_item(raw_line)
        if dependency is None:
            continue
        if dependency.startswith("pip:"):
            continue
        if python_version is None and _is_project_python_dependency(dependency):
            python_version = _extract_python_version_from_constraint(dependency)
        if package := _normalize_package_name(dependency):
            packages.append(package)

    source: PythonRequirementSource = "environment_yml"
    if path.name.lower().startswith("conda."):
        source = "conda_yml"

    rationale = None
    if python_version is not None:
        rationale = f"{path.name} declares python dependency {python_version}"

    return ParsedDependencyFile(
        path=path,
        source=source,
        packages=sorted(set(packages)),
        python_version=python_version,
        rationale=rationale,
    )


def _parse_pyproject_toml(path: Path) -> ParsedDependencyFile:
    try:
        data = tomllib.loads(_read_text(path))
    except tomllib.TOMLDecodeError:
        data = {}

    packages: list[str] = []
    python_version: str | None = None
    rationale: str | None = None

    project = data.get("project")
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if isinstance(dependency, str) and (
                    package := _normalize_package_name(dependency)
                ):
                    packages.append(package)
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str):
            python_version = _extract_python_version_from_constraint(requires_python)
            if python_version is not None:
                rationale = (
                    f"{path.name} project.requires-python specifies {requires_python}"
                )

    return ParsedDependencyFile(
        path=path,
        source="pyproject_toml",
        packages=sorted(set(packages)),
        python_version=python_version,
        rationale=rationale,
    )


def _parse_setup_cfg(path: Path) -> ParsedDependencyFile:
    parser = ConfigParser()
    try:
        parser.read_string(_read_text(path))
    except ConfigParserError:
        parser = ConfigParser()

    python_requires = parser.get("options", "python_requires", fallback=None)
    python_version = _extract_python_version_from_constraint(python_requires)
    rationale = None
    if python_version is not None and python_requires is not None:
        rationale = f"{path.name} options.python_requires specifies {python_requires}"

    packages: list[str] = []
    install_requires = parser.get("options", "install_requires", fallback="")
    for raw_line in install_requires.splitlines():
        if package := _normalize_package_name(raw_line.strip()):
            packages.append(package)

    return ParsedDependencyFile(
        path=path,
        source="setup_cfg",
        packages=sorted(set(packages)),
        python_version=python_version,
        rationale=rationale,
    )


def _parse_setup_py(path: Path) -> ParsedDependencyFile:
    text = _read_text(path)
    python_requires_match = re.search(
        r"python_requires\s*=\s*['\"]([^'\"]+)['\"]",
        text,
    )
    python_requires = (
        python_requires_match.group(1) if python_requires_match is not None else None
    )
    python_version = _extract_python_version_from_constraint(python_requires)
    rationale = None
    if python_version is not None and python_requires is not None:
        rationale = f"{path.name} python_requires specifies {python_requires}"

    return ParsedDependencyFile(
        path=path,
        source="setup_py",
        packages=[],
        python_version=python_version,
        rationale=rationale,
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _extract_yaml_list_item(raw_line: str) -> str | None:
    stripped = raw_line.strip()
    if not stripped.startswith("- "):
        return None
    return stripped[2:].strip()


def _normalize_package_name(requirement: str) -> str | None:
    value = requirement.strip().strip("\"'")
    if not value:
        return None
    if value.startswith(("python", "pip:")):
        return None
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", ",", "="):
        if separator in value:
            value = value.split(separator, 1)[0].strip()
            break
    if not value:
        return None
    value = value.lower().replace("_", "-")
    if not value.replace("-", "").replace(".", "").isalnum():
        return None
    return value


def _is_project_python_dependency(requirement: str) -> bool:
    normalized = requirement.strip().strip("\"'").lower()
    return normalized == "python" or normalized.startswith("python=")


def _extract_python_version_from_constraint(constraint: str | None) -> str | None:
    if not constraint:
        return None
    match = _PYTHON_VERSION_RE.search(constraint)
    if match is None:
        return None
    return _normalize_python_version(match.group(1))


def _normalize_python_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return version


_PARSERS_BY_NAME = {
    "requirements.txt": _parse_requirements_txt,
    "requirements-dev.txt": _parse_requirements_txt,
    "requirements.in": _parse_requirements_txt,
    "environment.yml": _parse_conda_environment_file,
    "environment.yaml": _parse_conda_environment_file,
    "conda.yml": _parse_conda_environment_file,
    "conda.yaml": _parse_conda_environment_file,
    "pyproject.toml": _parse_pyproject_toml,
    "setup.cfg": _parse_setup_cfg,
    "setup.py": _parse_setup_py,
}

from __future__ import annotations

from quick_env_setup.dependency_file_parser import (
    ParsedDependencyFile,
    parse_dependency_files,
    parse_readme_python_version,
)
from quick_env_setup.models import ProjectScanResult, PythonRequirement


DEFAULT_PYTHON_VERSION = "3.10"
_SOURCE_PRECEDENCE = (
    "environment_yml",
    "conda_yml",
    "pyproject_toml",
    "setup_cfg",
    "setup_py",
)


def resolve_python_requirement(
    project_scan: ProjectScanResult,
    user_override: str | None = None,
) -> PythonRequirement:
    if user_override:
        return PythonRequirement(
            version=user_override,
            source="user_override",
            rationale=f"Using user override for Python {user_override}.",
        )

    parsed_files = parse_dependency_files(project_scan.dependency_files)
    if resolved := _resolve_from_dependency_files(parsed_files):
        return resolved

    if project_scan.readme_path is not None:
        if readme_version := parse_readme_python_version(project_scan.readme_path):
            return PythonRequirement(
                version=readme_version,
                source="readme",
                rationale=(
                    f"{project_scan.readme_path.name} mentions Python {readme_version}."
                ),
            )

    return PythonRequirement(
        version=DEFAULT_PYTHON_VERSION,
        source="default",
        rationale=f"No Python version found; defaulting conservatively to {DEFAULT_PYTHON_VERSION}.",
    )


def resolve_python_version(
    project_scan: ProjectScanResult,
    user_override: str | None = None,
) -> PythonRequirement:
    return resolve_python_requirement(project_scan, user_override=user_override)


def _resolve_from_dependency_files(
    parsed_files: list[ParsedDependencyFile],
) -> PythonRequirement | None:
    for source in _SOURCE_PRECEDENCE:
        for parsed_file in parsed_files:
            if parsed_file.source != source or parsed_file.python_version is None:
                continue
            return PythonRequirement(
                version=parsed_file.python_version,
                source=parsed_file.source,
                rationale=parsed_file.rationale
                or f"{parsed_file.path.name} indicates Python {parsed_file.python_version}.",
            )
    return None

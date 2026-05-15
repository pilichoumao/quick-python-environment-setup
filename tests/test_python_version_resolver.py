from __future__ import annotations

from pathlib import Path

from quick_env_setup.project_scanner import scan_project
from quick_env_setup.python_version_resolver import resolve_python_requirement


def test_resolve_python_requirement_prefers_environment_yml_over_pyproject(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "conda-project"
    project_root.mkdir()
    (project_root / "environment.yml").write_text(
        "\n".join(
            [
                "name: demo",
                "dependencies:",
                "  - python=3.11",
                '  - pip',
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'requires-python = ">=3.9"',
            ]
        ),
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.11"
    assert requirement.source == "environment_yml"
    assert "environment.yml" in requirement.rationale


def test_resolve_python_requirement_prefers_pyproject_over_setup_cfg(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "package-project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'requires-python = ">=3.10"',
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "setup.cfg").write_text(
        "\n".join(
            [
                "[metadata]",
                "name = demo",
                "",
                "[options]",
                "python_requires = >=3.8",
            ]
        ),
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.10"
    assert requirement.source == "pyproject_toml"
    assert "pyproject.toml" in requirement.rationale


def test_resolve_python_requirement_falls_back_to_readme(tmp_path: Path) -> None:
    project_root = tmp_path / "readme-project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "Requires Python 3.9 or newer to run this project.\n",
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.9"
    assert requirement.source == "readme"
    assert "README.md" in requirement.rationale


def test_resolve_python_requirement_defaults_to_python_3_10(tmp_path: Path) -> None:
    project_root = tmp_path / "empty-project"
    project_root.mkdir()
    (project_root / "script.py").write_text("print('hello')\n", encoding="utf-8")

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.10"
    assert requirement.source == "default"
    assert "3.10" in requirement.rationale


def test_resolve_python_requirement_uses_user_override_when_supplied(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "override-project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "demo"',
                'version = "0.1.0"',
                'requires-python = ">=3.9"',
            ]
        ),
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(
        scan_project(project_root),
        user_override="3.12",
    )

    assert requirement.version == "3.12"
    assert requirement.source == "user_override"
    assert "override" in requirement.rationale.lower()


def test_resolve_python_requirement_prefers_setup_cfg_over_setup_py(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "setuptools-project"
    project_root.mkdir()
    (project_root / "setup.cfg").write_text(
        "\n".join(
            [
                "[metadata]",
                "name = demo",
                "",
                "[options]",
                "python_requires = >=3.11",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "setup.py").write_text(
        "\n".join(
            [
                "from setuptools import setup",
                "",
                'setup(name=\"demo\", python_requires=\">=3.8\")',
            ]
        ),
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.11"
    assert requirement.source == "setup_cfg"
    assert "setup.cfg" in requirement.rationale


def test_resolve_python_requirement_ignores_python_abi_in_environment_yml(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "conda-abi-project"
    project_root.mkdir()
    (project_root / "environment.yml").write_text(
        "\n".join(
            [
                "name: demo",
                "dependencies:",
                "  - python_abi=3.11",
                "  - numpy",
            ]
        ),
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.10"
    assert requirement.source == "default"


def test_resolve_python_requirement_ignores_incidental_readme_python_mentions(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "incidental-readme-project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "This guide compares Python 3.11 and Python 3.12 performance notes.\n",
        encoding="utf-8",
    )

    requirement = resolve_python_requirement(scan_project(project_root))

    assert requirement.version == "3.10"
    assert requirement.source == "default"

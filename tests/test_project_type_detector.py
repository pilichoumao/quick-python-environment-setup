from __future__ import annotations

from pathlib import Path

from quick_env_setup.project_scanner import scan_project
from quick_env_setup.project_type_detector import detect_project_profile


FIXTURES_ROOT = Path(__file__).parent / "fixtures"


def test_scan_project_collects_markers_and_ignores_noisy_directories() -> None:
    scan = scan_project(FIXTURES_ROOT / "deep_learning_project")

    assert scan.root == FIXTURES_ROOT / "deep_learning_project"
    assert scan.readme_path == FIXTURES_ROOT / "deep_learning_project" / "README.md"
    assert scan.dependency_files == [
        FIXTURES_ROOT / "deep_learning_project" / "requirements.txt"
    ]
    assert "torch" in scan.keywords
    assert "pytorch" in scan.keywords
    assert "training" in scan.keywords
    assert scan.python_entry_candidates == ["train.py"]
    assert scan.notebook_paths == []
    assert all(".venv" not in str(path) for path in scan.detected_files)


def test_scan_project_ignores_node_modules_in_web_fixture() -> None:
    scan = scan_project(FIXTURES_ROOT / "web_project")

    assert all("node_modules" not in str(path) for path in scan.detected_files)


def test_scan_project_ignores_generated_env_setup_logs(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    logs_dir = project_root / ".env_setup_logs"
    logs_dir.mkdir(parents=True)
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (logs_dir / "install_plan.json").write_text(
        '{"needs_pytorch": true, "run_candidates": ["python demo.py"]}\n',
        encoding="utf-8",
    )

    scan = scan_project(project_root)

    detected = {path.relative_to(project_root).as_posix() for path in scan.detected_files}
    assert "app.py" in detected
    assert ".env_setup_logs/install_plan.json" not in detected


def test_scan_project_detects_notebooks_and_dependency_files() -> None:
    scan = scan_project(FIXTURES_ROOT / "notebook_project")

    assert scan.dependency_files == [
        FIXTURES_ROOT / "notebook_project" / "requirements.txt"
    ]
    assert scan.notebook_paths == [
        FIXTURES_ROOT / "notebook_project" / "notebooks" / "analysis.ipynb"
    ]
    assert "jupyter" in scan.keywords
    assert "notebook" in scan.keywords


def test_scan_project_parses_pyproject_dependency_hints_conservatively() -> None:
    scan = scan_project(FIXTURES_ROOT / "package_project")

    assert scan.dependency_files == [
        FIXTURES_ROOT / "package_project" / "pyproject.toml"
    ]
    assert scan.parsed_dependency_hints["packages"] == ["requests"]
    assert "demo-package" not in scan.keywords
    assert "build-backend" not in scan.keywords
    assert "setuptools.build-meta" not in scan.keywords


def test_scan_project_collects_nested_dunder_main_as_entry_candidate() -> None:
    scan = scan_project(FIXTURES_ROOT / "package_project")

    assert "src/demo_package/__main__.py" in scan.python_entry_candidates


def test_detect_project_profile_identifies_deep_learning_project() -> None:
    profile = detect_project_profile(scan_project(FIXTURES_ROOT / "deep_learning_project"))

    assert profile.project_type == "deep_learning"
    assert profile.confidence >= 0.8
    assert profile.needs_pytorch is True
    assert profile.recommended_env_manager == "conda"
    assert profile.editable_install_recommended is False


def test_detect_project_profile_identifies_web_project() -> None:
    profile = detect_project_profile(scan_project(FIXTURES_ROOT / "web_project"))

    assert profile.project_type == "web"
    assert profile.confidence >= 0.75
    assert profile.needs_pytorch is False
    assert profile.recommended_env_manager == "venv"
    assert profile.editable_install_recommended is False


def test_detect_project_profile_identifies_notebook_project() -> None:
    profile = detect_project_profile(scan_project(FIXTURES_ROOT / "notebook_project"))

    assert profile.project_type == "notebook"
    assert profile.confidence >= 0.75
    assert profile.needs_pytorch is False
    assert profile.recommended_env_manager == "conda"
    assert profile.editable_install_recommended is False


def test_detect_project_profile_identifies_python_package() -> None:
    profile = detect_project_profile(scan_project(FIXTURES_ROOT / "package_project"))

    assert profile.project_type == "python_package"
    assert profile.confidence >= 0.8
    assert profile.needs_pytorch is False
    assert profile.recommended_env_manager == "venv"
    assert profile.editable_install_recommended is True


def test_detect_project_profile_falls_back_to_uncertain_for_ambiguous_project() -> None:
    profile = detect_project_profile(scan_project(FIXTURES_ROOT / "broken_project"))

    assert profile.project_type == "uncertain"
    assert profile.confidence <= 0.4
    assert profile.needs_pytorch is False
    assert profile.recommended_env_manager == "venv"
    assert profile.editable_install_recommended is False

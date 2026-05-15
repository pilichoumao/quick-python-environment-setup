from __future__ import annotations

from quick_env_setup.models import ProjectProfile, ProjectScanResult, ProjectType


def detect_project_profile(scan: ProjectScanResult) -> ProjectProfile:
    scores = {
        "deep_learning": _score_deep_learning(scan),
        "python_package": _score_python_package(scan),
        "web": _score_web(scan),
        "notebook": _score_notebook(scan),
        "cli_tool": _score_cli_tool(scan),
        "data_analysis": _score_data_analysis(scan),
    }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 3:
        return ProjectProfile(
            project_type="uncertain",
            confidence=0.3,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        )

    return ProjectProfile(
        project_type=best_type,
        confidence=_confidence_from_score(best_score),
        needs_pytorch=best_type == "deep_learning",
        recommended_env_manager=_recommended_env_manager(best_type),
        editable_install_recommended=_editable_install_recommended(best_type, scan),
    )


def _score_deep_learning(scan: ProjectScanResult) -> int:
    score = 0
    keywords = scan.keywords
    if {"torch", "pytorch"} & keywords:
        score += 3
    if "training" in keywords:
        score += 2
    if any(name.endswith("train.py") for name in scan.python_entry_candidates):
        score += 2
    return score


def _score_web(scan: ProjectScanResult) -> int:
    score = 0
    keywords = scan.keywords
    if {"fastapi", "flask", "django", "streamlit", "gradio"} & keywords:
        score += 3
    if "uvicorn" in keywords:
        score += 1
    if any(name.endswith(("app.py", "main.py", "manage.py")) for name in scan.python_entry_candidates):
        score += 1
    return score


def _score_notebook(scan: ProjectScanResult) -> int:
    score = 0
    if scan.notebook_paths:
        score += 3
    if {"jupyter", "notebook"} & scan.keywords:
        score += 2
    return score


def _score_python_package(scan: ProjectScanResult) -> int:
    score = 0
    dependency_names = {path.name for path in scan.dependency_files}
    package_init_paths = [
        path
        for path in scan.detected_files
        if path.name == "__init__.py" and "tests" not in path.relative_to(scan.root).parts
    ]
    if {"pyproject.toml", "setup.cfg", "setup.py"} & dependency_names:
        score += 2
    if package_init_paths:
        score += 2
    if any("src" in path.relative_to(scan.root).parts for path in package_init_paths):
        score += 1
    return score


def _score_cli_tool(scan: ProjectScanResult) -> int:
    score = 0
    if "cli.py" in scan.python_entry_candidates:
        score += 3
    if any(name.endswith("__main__.py") for name in scan.python_entry_candidates):
        score += 3
    return score


def _score_data_analysis(scan: ProjectScanResult) -> int:
    score = 0
    if "pandas" in scan.keywords:
        score += 1
    if scan.notebook_paths:
        score += 1
    return score


def _confidence_from_score(score: int) -> float:
    if score >= 5:
        return 0.9
    if score >= 4:
        return 0.8
    if score >= 3:
        return 0.75
    return 0.6


def _recommended_env_manager(project_type: ProjectType) -> str:
    if project_type in {"deep_learning", "notebook", "data_analysis"}:
        return "conda"
    return "venv"


def _editable_install_recommended(
    project_type: ProjectType,
    scan: ProjectScanResult,
) -> bool:
    if project_type != "python_package":
        return False
    dependency_names = {path.name for path in scan.dependency_files}
    return bool({"pyproject.toml", "setup.cfg", "setup.py"} & dependency_names)

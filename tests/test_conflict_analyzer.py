from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quick_env_setup.conflict_analyzer import analyze_install_error
from quick_env_setup.dependency_installer import execute_install_plan
from quick_env_setup.models import (
    DeviceInfo,
    InstallAction,
    InstallPlan,
    MirrorConfig,
    ProjectProfile,
    ProjectScanResult,
    PyTorchStrategy,
    PythonRequirement,
    SourceResolutionResult,
    SourceSpec,
    SystemInfo,
)
from quick_env_setup.validator import validate_environment


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected_category", "expected_evidence"),
    [
        (
            "",
            "ERROR: Cannot install foo==1.0 and foo==2.0 because these package versions have conflicting dependencies.",
            "package_conflict",
            "conflicting dependencies",
        ),
        (
            "",
            "ERROR: Package 'demo' requires a different Python: 3.10.14 not in '>=3.11'",
            "python_version_incompatible",
            "requires a different Python",
        ),
        (
            "",
            "error: Microsoft Visual C++ 14.0 or greater is required. Get it with \"Microsoft C++ Build Tools\"",
            "missing_build_tools",
            "Build Tools",
        ),
        (
            "",
            "ImportError: libGL.so.1: cannot open shared object file: No such file or directory",
            "missing_system_library",
            "libGL.so.1",
        ),
        (
            "",
            "RuntimeError: Detected that PyTorch and torchvision were compiled with different CUDA versions. PyTorch has CUDA Version=12.1 and torchvision has CUDA Version=11.8.",
            "pytorch_cuda_mismatch",
            "different CUDA versions",
        ),
        (
            "Looking in indexes: https://pypi.org/simple",
            "ERROR: Could not fetch URL https://pypi.org/simple/numpy/: There was a problem confirming the ssl certificate: HTTPSConnectionPool(host='pypi.org', port=443): Max retries exceeded",
            "network_failure",
            "Could not fetch URL",
        ),
    ],
)
def test_analyze_install_error_classifies_representative_failures(
    stdout: str,
    stderr: str,
    expected_category: str,
    expected_evidence: str,
) -> None:
    report = analyze_install_error(stdout=stdout, stderr=stderr)

    assert report.category == expected_category
    assert report.summary
    assert report.evidence
    assert expected_evidence in report.evidence[0]
    assert report.recommendations


def test_analyze_install_error_does_not_misclassify_generic_version_conflict_as_python_issue() -> None:
    report = analyze_install_error(
        stderr=(
            "ERROR: Cannot install demo because these package versions have conflicting dependencies.\n"
            "The user requested numpy>=1.26\n"
            "demo-lib 1.0 depends on numpy not in '>=1.26,<2.0'\n"
        )
    )

    assert report.category == "package_conflict"


def test_execute_install_plan_stops_on_first_failure_and_persists_structured_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _make_plan(
        tmp_path,
        actions=[
            InstallAction(
                action_id="step-1",
                kind="check",
                command=["python", "--version"],
                cwd=tmp_path,
                env_overrides={},
                risk_level="low",
                description="first step",
            ),
            InstallAction(
                action_id="step-2",
                kind="install_dependencies",
                command=["python", "-m", "pip", "install", "demo"],
                cwd=tmp_path,
                env_overrides={},
                risk_level="medium",
                description="second step",
            ),
            InstallAction(
                action_id="step-3",
                kind="validate",
                command=["python", "-c", "print('never')"],
                cwd=tmp_path,
                env_overrides={},
                risk_level="low",
                description="third step",
            ),
        ],
    )
    calls: list[list[str]] = []
    kwargs_seen: list[dict[str, object]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        kwargs_seen.append(kwargs)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 0, stdout="Python 3.11.0\n", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="resolver output\n", stderr="install failed\n")

    monkeypatch.setattr("quick_env_setup.dependency_installer.subprocess.run", fake_run)

    result = execute_install_plan(plan)

    assert result.success is False
    assert result.completed_action_ids == ["step-1"]
    assert result.failed_action_id == "step-2"
    assert result.exit_code == 1
    assert calls == [
        ["python", "--version"],
        ["python", "-m", "pip", "install", "demo"],
    ]

    log_text = result.log_path.read_text(encoding="utf-8")
    assert "action_id=step-1" in log_text
    assert "action_id=step-2" in log_text
    assert "action_id=step-3" not in log_text
    assert "cwd=" in log_text
    assert "exit_code=0" in log_text
    assert "exit_code=1" in log_text
    assert "stdout_tail:" in log_text
    assert "stderr_tail:" in log_text
    assert "resolver output" in log_text
    assert "install failed" in log_text
    assert kwargs_seen[0]["shell"] is False
    assert kwargs_seen[0]["capture_output"] is True
    assert kwargs_seen[0]["text"] is True
    assert kwargs_seen[0]["cwd"] == str(tmp_path)
    assert isinstance(kwargs_seen[0]["env"], dict)


def test_execute_install_plan_returns_oserror_failure_and_logs_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _make_plan(
        tmp_path,
        actions=[
            InstallAction(
                action_id="create-environment",
                kind="create_env",
                command=["python", "-m", "venv", ".venv"],
                cwd=tmp_path,
                env_overrides={},
                risk_level="medium",
                description="create env",
            )
        ],
    )

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("permission denied")

    monkeypatch.setattr("quick_env_setup.dependency_installer.subprocess.run", fake_run)

    result = execute_install_plan(plan)

    assert result.success is False
    assert result.failed_action_id == "create-environment"
    assert result.exit_code is None
    assert "permission denied" in result.stderr_tail
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "exit_code=oserror" in log_text
    assert "permission denied" in log_text


def test_execute_install_plan_logs_remote_source_under_existing_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clone_target = tmp_path / "cloned-project"
    plan = _make_plan(
        clone_target,
        source_type="git_url",
        actions=[
            InstallAction(
                action_id="clone-source",
                kind="clone",
                command=["git", "clone", "https://example.com/repo.git", str(clone_target)],
                cwd=tmp_path,
                env_overrides={},
                risk_level="medium",
                description="clone source",
            )
        ],
    )

    def fake_run(
        command: list[str],
        **_: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="cloned\n", stderr="")

    monkeypatch.setattr("quick_env_setup.dependency_installer.subprocess.run", fake_run)

    result = execute_install_plan(plan)

    assert result.success is True
    assert result.log_path == tmp_path / ".env_setup_logs" / "commands.log"
    assert result.log_path.exists()
    assert not clone_target.exists()


def test_validate_environment_keeps_warning_grade_misses_non_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _make_plan(
        tmp_path,
        dependency_packages=["torch", "opencv-python"],
        needs_pytorch=True,
        pytorch_required=True,
        pytorch_variant="cuda",
        accelerator_type="nvidia",
    )
    calls: list[list[str]] = []
    kwargs_seen: list[dict[str, object]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        kwargs_seen.append(kwargs)
        joined = " ".join(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")
        if "importlib.import_module('torch')" in joined:
            return subprocess.CompletedProcess(command, 0, stdout="2.3.0\n", stderr="")
        if "importlib.import_module('cv2')" in joined:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="ModuleNotFoundError: No module named 'cv2'\n")
        if "torch.cuda.is_available()" in joined:
            return subprocess.CompletedProcess(command, 1, stdout="cuda_available=False\n", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("quick_env_setup.validator.subprocess.run", fake_run)

    report = validate_environment(plan)

    assert report.passed is True
    assert report.failures == []
    assert any("import cv2" in warning for warning in report.warnings)
    assert any("torch.cuda.is_available()" in warning for warning in report.warnings)
    assert "import cv2" in report.checks_run
    assert "torch.cuda.is_available()" in report.checks_run
    assert len(calls) == 5
    assert kwargs_seen[0]["shell"] is False
    assert kwargs_seen[0]["capture_output"] is True
    assert kwargs_seen[0]["text"] is True
    assert kwargs_seen[0]["cwd"] == str(tmp_path.resolve())


def test_validate_environment_skips_torch_device_probe_when_torch_import_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _make_plan(
        tmp_path,
        dependency_packages=["torch"],
        needs_pytorch=True,
        pytorch_required=True,
        pytorch_variant="cuda",
        accelerator_type="nvidia",
    )
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **_: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        joined = " ".join(command)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")
        if "importlib.import_module('torch')" in joined:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="ModuleNotFoundError: No module named 'torch'\n")
        if "torch.cuda.is_available()" in joined:
            raise AssertionError("torch device probe should be skipped when torch import fails")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("quick_env_setup.validator.subprocess.run", fake_run)

    report = validate_environment(plan)

    assert report.passed is False
    assert report.failures == ["import torch: ModuleNotFoundError: No module named 'torch'"]
    assert not any("torch.cuda.is_available()" in entry for entry in report.checks_run)
    assert len(calls) == 3


def test_validate_environment_records_warning_oserror_without_failing_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _make_plan(
        tmp_path,
        dependency_packages=["opencv-python"],
    )

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if "importlib.import_module('cv2')" in " ".join(command):
            raise OSError("bad loader")
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr("quick_env_setup.validator.subprocess.run", fake_run)

    report = validate_environment(plan)

    assert report.passed is True
    assert report.failures == []
    assert any("import cv2" in warning and "bad loader" in warning for warning in report.warnings)


def _make_plan(
    project_root: Path,
    *,
    source_type: str = "local_path",
    actions: list[InstallAction] | None = None,
    dependency_packages: list[str] | None = None,
    needs_pytorch: bool = False,
    pytorch_required: bool = False,
    pytorch_variant: str = "none",
    accelerator_type: str = "cpu",
) -> InstallPlan:
    resolved_root = project_root.resolve()
    return InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(project_root),
                source_type=source_type,
                normalized=str(project_root),
            ),
            local_project_path=resolved_root,
            clone_performed=False,
            repo_url="https://example.com/repo.git" if source_type == "git_url" else None,
        ),
        system_info=SystemInfo(
            os_name="linux",
            arch="x86_64",
            is_apple_silicon=False,
            has_conda=True,
            has_git=True,
            python_executables=["python3"],
        ),
        project_scan=ProjectScanResult(
            root=resolved_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(dependency_packages or []),
            parsed_dependency_hints={"packages": dependency_packages or []},
        ),
        project_profile=ProjectProfile(
            project_type="deep_learning" if needs_pytorch else "web",
            confidence=0.8,
            needs_pytorch=needs_pytorch,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.11",
            source="default",
            rationale="test fixture",
        ),
        env_manager="venv",
        env_name="test-env",
        device_info=DeviceInfo(
            accelerator_type=accelerator_type,
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=accelerator_type == "nvidia",
        ),
        pytorch_strategy=PyTorchStrategy(
            required=pytorch_required,
            install_separately=False,
            variant=pytorch_variant,
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="test fixture",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=2,
        actions=actions or [],
        warnings=[],
        assumptions=[],
    )

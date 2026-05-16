from __future__ import annotations

from pathlib import Path

import pytest

from quick_env_setup import cli
from quick_env_setup.models import InstallAction, InstallPlan
from quick_env_setup.utils import InstallWorkflowResult


FIXTURES = Path(__file__).parent / "fixtures"


def test_local_path_produces_install_plan() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(source=str(FIXTURES / "web_project"))

    assert isinstance(plan, InstallPlan)
    assert plan.source_result.local_project_path == (FIXTURES / "web_project").resolve()
    assert plan.actions
    assert all(action.command is not None for action in plan.actions)


def test_dry_run_does_not_execute_actions(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from quick_env_setup.models import MirrorConfig
    from quick_env_setup.models import ProjectProfile, ProjectScanResult, PyTorchStrategy
    from quick_env_setup.models import PythonRequirement, SourceResolutionResult, SourceSpec
    from quick_env_setup.models import SystemInfo, DeviceInfo

    fixture_root = (FIXTURES / "web_project").resolve()

    plan = InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(fixture_root),
                source_type="local_path",
                normalized=str(fixture_root),
            ),
            local_project_path=fixture_root,
            clone_performed=False,
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
            root=fixture_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name="web-project-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=1,
        actions=[
            InstallAction(
                action_id="check-python",
                kind="check",
                command=["python", "--version"],
                cwd=fixture_root,
                env_overrides={},
                risk_level="low",
                description="Check Python availability.",
            )
        ],
        warnings=[],
        assumptions=[],
    )

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("execute_install_plan should not be called during --dry-run")

    monkeypatch.setattr("quick_env_setup.cli.build_install_plan", lambda **_: plan)
    monkeypatch.setattr("quick_env_setup.cli.execute_install_plan", fail_if_called)

    exit_code = cli.main(["--source", str(fixture_root), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Plan summary" in captured.out
    assert "check-python" in captured.out


def test_cli_default_level_is_2_and_dry_run_prints_plan_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_root = (FIXTURES / "web_project").resolve()
    captured_kwargs: dict[str, object] = {}

    def fake_build_install_plan(**kwargs: object) -> InstallPlan:
        captured_kwargs.update(kwargs)
        return _make_cli_plan(fixture_root)

    monkeypatch.setattr("quick_env_setup.cli.build_install_plan", fake_build_install_plan)
    monkeypatch.setattr(
        "quick_env_setup.cli.execute_install_plan",
        lambda plan: (_ for _ in ()).throw(AssertionError("execute_install_plan should not run")),
    )

    exit_code = cli.main(["--source", str(fixture_root), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured_kwargs["safety_level"] == 2
    assert "Plan summary" in captured.out
    assert "safety level: 2" in captured.out


def test_cli_yes_bypasses_low_risk_prompt_and_emits_artifact_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fixture_root = (FIXTURES / "web_project").resolve()
    artifact_dir = tmp_path / ".env_setup_logs"
    prompt_calls: list[bool | None] = []

    def fake_confirm(*, injected_response: bool | None = None) -> bool:
        prompt_calls.append(injected_response)
        return True

    workflow_result = InstallWorkflowResult(
        plan=_make_cli_plan(fixture_root),
        execution_succeeded=True,
        validation_passed=True,
        artifact_dir=artifact_dir,
        artifact_paths={
            "commands.log": artifact_dir / "commands.log",
            "final_report.txt": artifact_dir / "final_report.txt",
        },
        completed_action_ids=["check-python", "create-environment"],
        failed_action_id=None,
        run_candidates=["python app.py"],
        missing_assets=[],
        warnings=[],
    )

    monkeypatch.setattr("quick_env_setup.cli.build_install_plan", lambda **_: _make_cli_plan(fixture_root))
    monkeypatch.setattr("quick_env_setup.cli.confirm_low_risk_execution", fake_confirm)
    monkeypatch.setattr("quick_env_setup.cli.execute_install_plan", lambda plan: workflow_result)

    exit_code = cli.main(["--source", str(fixture_root), "--yes"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert prompt_calls == [True]
    assert "Execution summary" in captured.out
    assert str(artifact_dir / "commands.log") in captured.out
    assert str(artifact_dir / "final_report.txt") in captured.out


def test_cli_returns_nonzero_when_execution_or_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fixture_root = (FIXTURES / "web_project").resolve()
    workflow_result = InstallWorkflowResult(
        plan=_make_cli_plan(fixture_root),
        execution_succeeded=False,
        validation_passed=False,
        artifact_dir=tmp_path / ".env_setup_logs",
        artifact_paths={"error_summary.txt": tmp_path / ".env_setup_logs" / "error_summary.txt"},
        completed_action_ids=["check-python"],
        failed_action_id="install-dependencies",
        run_candidates=[],
        missing_assets=[],
        warnings=["Dependency installation failed."],
    )

    monkeypatch.setattr("quick_env_setup.cli.build_install_plan", lambda **_: _make_cli_plan(fixture_root))
    monkeypatch.setattr("quick_env_setup.cli.confirm_low_risk_execution", lambda **_: True)
    monkeypatch.setattr("quick_env_setup.cli.execute_install_plan", lambda plan: workflow_result)

    exit_code = cli.main(["--source", str(fixture_root), "--yes"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "install-dependencies" in captured.out
    assert "Dependency installation failed." in captured.out


def test_deep_learning_fixture_defaults_to_conda() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(source=str(FIXTURES / "deep_learning_project"))

    assert plan.project_profile.project_type == "deep_learning"
    assert plan.env_manager == "conda"


def test_explicit_env_manager_override_beats_recommendation() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(
        source=str(FIXTURES / "deep_learning_project"),
        env_manager="venv",
    )

    assert plan.project_profile.recommended_env_manager == "conda"
    assert plan.env_manager == "venv"


def test_level_1_plan_excludes_install_execution() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(
        source=str(FIXTURES / "deep_learning_project"),
        safety_level=1,
    )

    risky_kinds = {action.kind for action in plan.actions}
    assert "create_env" not in risky_kinds
    assert "install_pytorch" not in risky_kinds
    assert "install_dependencies" not in risky_kinds
    assert any(action.kind == "check" for action in plan.actions)


def test_high_risk_actions_are_filtered_without_explicit_flag() -> None:
    from quick_env_setup.safety_policy import apply_safety_policy

    allowed_actions, warnings = apply_safety_policy(
        [
            InstallAction(
                action_id="run-demo",
                kind="validate",
                command=["python", "demo.py"],
                cwd=(FIXTURES / "web_project").resolve(),
                env_overrides={},
                risk_level="high",
                description="Run the demo entrypoint.",
            )
        ],
        safety_level=3,
        allow_high_risk=False,
    )

    assert allowed_actions == []
    assert warnings
    assert "high-risk actions require explicit approval flags" in warnings[0]


def test_remote_git_source_plan_includes_git_check_and_clone(tmp_path: Path) -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(
        source="https://github.com/example/project.git",
        clone_dir=str(tmp_path),
    )

    action_ids = [action.action_id for action in plan.actions]
    assert "check-git" in action_ids
    assert "clone-source" in action_ids
    assert plan.source_result.repo_url == "https://github.com/example/project.git"
    assert plan.source_result.local_project_path == tmp_path / "project"


def test_missing_conda_system_adds_prerequisite_check_and_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    from quick_env_setup.models import SystemInfo
    from quick_env_setup.orchestrator import build_install_plan

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.detect_system_info",
        lambda **_: SystemInfo(
            os_name="linux",
            arch="x86_64",
            is_apple_silicon=False,
            has_conda=False,
            has_git=True,
            python_executables=["python3"],
        ),
    )

    plan = build_install_plan(source=str(FIXTURES / "deep_learning_project"))

    conda_check = next(action for action in plan.actions if action.action_id == "check-conda")
    assert conda_check.command == ["conda", "--version"]
    assert any("Conda was not detected" in warning for warning in plan.warnings)


def test_run_demo_is_rejected_even_at_level_3() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    with pytest.raises(NotImplementedError, match="run_demo"):
        build_install_plan(
            source=str(FIXTURES / "web_project"),
            safety_level=3,
            run_demo=True,
        )


def test_environment_yml_project_uses_conda_dependency_flow(tmp_path: Path) -> None:
    from quick_env_setup.orchestrator import build_install_plan

    project_root = tmp_path / "conda-project"
    project_root.mkdir()
    (project_root / "environment.yml").write_text(
        "\n".join(
            [
                "name: conda-project",
                "dependencies:",
                "  - python=3.11",
                "  - numpy",
            ]
        ),
        encoding="utf-8",
    )

    plan = build_install_plan(source=str(project_root), env_manager="conda")

    install_action = next(
        action for action in plan.actions if action.kind == "install_dependencies"
    )
    assert install_action.command == [
        "conda",
        "env",
        "update",
        "-n",
        "conda-project-env",
        "-f",
        str(project_root / "environment.yml"),
    ]


def test_pytorch_install_is_not_split_when_strategy_disables_it(monkeypatch: pytest.MonkeyPatch) -> None:
    from quick_env_setup.models import PyTorchStrategy
    from quick_env_setup.orchestrator import build_install_plan

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.resolve_pytorch_strategy",
        lambda *args, **kwargs: PyTorchStrategy(
            required=True,
            install_separately=False,
            variant="cpu",
            index_url=None,
            packages=["torch"],
            stripped_requirements_path=None,
            rationale="Keep torch in the main dependency install flow.",
        ),
    )

    plan = build_install_plan(source=str(FIXTURES / "deep_learning_project"))

    assert all(action.kind != "install_pytorch" for action in plan.actions)


def test_venv_plan_falls_back_to_detected_python_launcher_when_requested_one_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quick_env_setup.models import SystemInfo
    from quick_env_setup.orchestrator import build_install_plan

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.detect_system_info",
        lambda **_: SystemInfo(
            os_name="linux",
            arch="x86_64",
            is_apple_silicon=False,
            has_conda=True,
            has_git=True,
            python_executables=["python"],
        ),
    )

    plan = build_install_plan(
        source=str(FIXTURES / "package_project"),
        env_manager="venv",
    )

    create_action = next(action for action in plan.actions if action.kind == "create_env")
    assert create_action.command == [
        "python",
        "-m",
        "venv",
        str((FIXTURES / "package_project" / ".venv").resolve()),
    ]


def test_execute_install_plan_uses_consistent_artifact_dir_for_remote_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from quick_env_setup.models import (
        DeviceInfo,
        ExecutionResult,
        MirrorConfig,
        ProjectProfile,
        ProjectScanResult,
        PyTorchStrategy,
        PythonRequirement,
        SourceResolutionResult,
        SourceSpec,
        SystemInfo,
        ValidationReport,
    )
    from quick_env_setup.orchestrator import execute_install_plan

    clone_target = tmp_path / "cloned-project"
    clone_target.mkdir()
    plan = InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw="https://github.com/example/project.git",
                source_type="git_url",
                normalized="https://github.com/example/project.git",
            ),
            local_project_path=clone_target,
            clone_performed=False,
            repo_url="https://github.com/example/project.git",
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
            root=clone_target,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name="cloned-project-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=2,
        actions=[],
        warnings=[],
        assumptions=[],
    )

    artifact_dir = clone_target / ".env_setup_logs"
    commands_log = artifact_dir / "commands.log"
    commands_log.parent.mkdir(parents=True, exist_ok=True)
    commands_log.write_text("command log\n", encoding="utf-8")

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.execute_action_plan",
        lambda plan: ExecutionResult(
            success=True,
            completed_action_ids=[],
            failed_action_id=None,
            exit_code=0,
            log_path=commands_log,
            stdout_tail="",
            stderr_tail="",
        ),
    )
    monkeypatch.setattr(
        "quick_env_setup.orchestrator.validate_environment",
        lambda plan: ValidationReport(passed=True, checks_run=["python --version"], failures=[], warnings=[]),
    )
    monkeypatch.setattr("quick_env_setup.orchestrator.discover_run_candidates", lambda scan: ["python app.py"])
    monkeypatch.setattr("quick_env_setup.orchestrator.detect_missing_assets", lambda scan: [])

    result = execute_install_plan(plan)

    assert result.artifact_dir == artifact_dir
    assert all(path.parent == artifact_dir for path in result.artifact_paths.values())


def test_execute_install_plan_enriches_conflict_report_before_writing_error_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from quick_env_setup.models import (
        DeviceInfo,
        ExecutionResult,
        MirrorConfig,
        ProjectProfile,
        ProjectScanResult,
        PyTorchStrategy,
        PythonRequirement,
        SourceResolutionResult,
        SourceSpec,
        SystemInfo,
    )
    from quick_env_setup.orchestrator import execute_install_plan

    project_root = tmp_path / "broken-project"
    project_root.mkdir()
    plan = InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(project_root),
                source_type="local_path",
                normalized=str(project_root),
            ),
            local_project_path=project_root,
            clone_performed=False,
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
            root=project_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name="broken-project-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=2,
        actions=[],
        warnings=[],
        assumptions=[],
    )

    commands_log = project_root / ".env_setup_logs" / "commands.log"
    commands_log.parent.mkdir(parents=True, exist_ok=True)
    commands_log.write_text("command log\n", encoding="utf-8")

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.execute_action_plan",
        lambda plan: ExecutionResult(
            success=False,
            completed_action_ids=["check-python"],
            failed_action_id="install-dependencies",
            exit_code=1,
            log_path=commands_log,
            stdout_tail="",
            stderr_tail=(
                "ERROR: Could not fetch URL https://pypi.org/simple/numpy/: "
                "There was a problem confirming the ssl certificate\n"
            ),
        ),
    )

    result = execute_install_plan(plan)

    error_summary = result.artifact_paths["error_summary.txt"].read_text(encoding="utf-8")
    assert "Recommended next steps:" in error_summary
    assert "certificate bundle" in error_summary
    final_report = result.artifact_paths["final_report.txt"].read_text(encoding="utf-8")
    assert "Validation: failed" in final_report
    assert "- Diagnose the install failure in error_summary.txt before retrying the setup." in final_report
    assert "- First recovery step: Retry the install after confirming the package index is reachable from this machine." in final_report
    assert "- Detected failure category: network_failure." in final_report
    assert "- Network-related failures often recover after connectivity, mirror, or certificate issues are fixed." in final_report


def test_execute_install_plan_uses_plan_python_version_in_failure_guidance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from quick_env_setup.models import ExecutionResult
    from quick_env_setup.orchestrator import execute_install_plan

    plan = _make_failure_plan(tmp_path / "python-version-project")
    commands_log = plan.source_result.local_project_path / ".env_setup_logs" / "commands.log"
    commands_log.parent.mkdir(parents=True, exist_ok=True)
    commands_log.write_text("command log\n", encoding="utf-8")

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.execute_action_plan",
        lambda plan: ExecutionResult(
            success=False,
            completed_action_ids=["create-environment"],
            failed_action_id="install-dependencies",
            exit_code=1,
            log_path=commands_log,
            stdout_tail="",
            stderr_tail=(
                "ERROR: foo-3.12.0 requires Python >=3.11\n"
                "ERROR: Could not find a version that satisfies the requirement demo-lib\n"
            ),
        ),
    )

    result = execute_install_plan(plan)

    error_summary = result.artifact_paths["error_summary.txt"].read_text(encoding="utf-8")
    assert "current plan targets Python 3.10" in error_summary
    assert "upgrade the environment to python 3.11" in error_summary.lower()
    assert "python 3.12" not in error_summary.lower()


def test_execute_install_plan_prefers_cpu_fallback_for_cpu_pytorch_strategy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from quick_env_setup.models import ExecutionResult, PyTorchStrategy
    from quick_env_setup.orchestrator import execute_install_plan

    plan = _make_failure_plan(
        tmp_path / "cpu-pytorch-project",
        pytorch_strategy=PyTorchStrategy(
            required=True,
            install_separately=True,
            variant="cpu",
            index_url="https://download.pytorch.org/whl/cpu",
            packages=["torch", "torchvision", "torchaudio"],
            stripped_requirements_path=None,
            rationale="cpu requested",
        ),
    )
    commands_log = plan.source_result.local_project_path / ".env_setup_logs" / "commands.log"
    commands_log.parent.mkdir(parents=True, exist_ok=True)
    commands_log.write_text("command log\n", encoding="utf-8")

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.execute_action_plan",
        lambda plan: ExecutionResult(
            success=False,
            completed_action_ids=["create-environment"],
            failed_action_id="install-pytorch",
            exit_code=1,
            log_path=commands_log,
            stdout_tail="",
            stderr_tail="RuntimeError: Torch not compiled with CUDA enabled\n",
        ),
    )

    result = execute_install_plan(plan)

    error_summary_lines = result.artifact_paths["error_summary.txt"].read_text(encoding="utf-8").splitlines()
    recommendations_start = error_summary_lines.index("Recommended next steps:") + 1
    recommendation_lines = [
        line for line in error_summary_lines[recommendations_start:] if line.startswith("- ")
    ]
    assert recommendation_lines
    assert "cpu-only wheels" in recommendation_lines[0].lower()
    assert "plan already targets the cpu variant" in recommendation_lines[0].lower()


def test_execute_install_plan_does_not_suggest_adopting_mirror_when_one_is_already_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from quick_env_setup.models import ExecutionResult, MirrorConfig
    from quick_env_setup.orchestrator import execute_install_plan

    plan = _make_failure_plan(
        tmp_path / "mirror-network-project",
        mirror_config=MirrorConfig(
            enabled=True,
            provider="tuna",
            pip_index_url="https://pypi.tuna.tsinghua.edu.cn/simple",
            conda_channels=["https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"],
        ),
    )
    commands_log = plan.source_result.local_project_path / ".env_setup_logs" / "commands.log"
    commands_log.parent.mkdir(parents=True, exist_ok=True)
    commands_log.write_text("command log\n", encoding="utf-8")

    monkeypatch.setattr(
        "quick_env_setup.orchestrator.execute_action_plan",
        lambda plan: ExecutionResult(
            success=False,
            completed_action_ids=["create-environment"],
            failed_action_id="install-dependencies",
            exit_code=1,
            log_path=commands_log,
            stdout_tail="",
            stderr_tail="ERROR: Could not fetch URL https://pypi.tuna.tsinghua.edu.cn/simple/demo/: Read timed out\n",
        ),
    )

    result = execute_install_plan(plan)

    error_summary = result.artifact_paths["error_summary.txt"].read_text(encoding="utf-8").lower()
    assert "configured tuna mirror" in error_summary
    assert "disable it temporarily to compare against the default index" in error_summary
    assert "trusted package index mirror" not in error_summary


def _make_cli_plan(fixture_root: Path) -> InstallPlan:
    from quick_env_setup.models import MirrorConfig
    from quick_env_setup.models import ProjectProfile, ProjectScanResult, PyTorchStrategy
    from quick_env_setup.models import PythonRequirement, SourceResolutionResult, SourceSpec
    from quick_env_setup.models import SystemInfo, DeviceInfo

    return InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(fixture_root),
                source_type="local_path",
                normalized=str(fixture_root),
            ),
            local_project_path=fixture_root,
            clone_performed=False,
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
            root=fixture_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name="web-project-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=2,
        actions=[
            InstallAction(
                action_id="check-python",
                kind="check",
                command=["python", "--version"],
                cwd=fixture_root,
                env_overrides={},
                risk_level="low",
                description="Check Python availability.",
            )
        ],
        warnings=[],
        assumptions=[],
    )


def test_use_china_mirror_without_provider_uses_conservative_default() -> None:
    from quick_env_setup.orchestrator import build_install_plan

    plan = build_install_plan(
        source=str(FIXTURES / "web_project"),
        use_china_mirror=True,
    )

    assert plan.mirror_config.enabled is True
    assert plan.mirror_config.provider == "tuna"


def test_planner_action_risk_levels_come_from_safety_policy() -> None:
    from quick_env_setup.orchestrator import build_install_plan
    from quick_env_setup.safety_policy import risk_level_for_action_kind

    plan = build_install_plan(source=str(FIXTURES / "deep_learning_project"))

    for action in plan.actions:
        assert action.risk_level == risk_level_for_action_kind(action.kind)


def _make_cli_plan(project_root: Path) -> InstallPlan:
    from quick_env_setup.models import MirrorConfig
    from quick_env_setup.models import ProjectProfile, ProjectScanResult, PyTorchStrategy
    from quick_env_setup.models import PythonRequirement, SourceResolutionResult, SourceSpec
    from quick_env_setup.models import SystemInfo, DeviceInfo

    return InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(project_root),
                source_type="local_path",
                normalized=str(project_root),
            ),
            local_project_path=project_root,
            clone_performed=False,
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
            root=project_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name="web-project-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        ),
        mirror_config=MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        ),
        safety_level=2,
        actions=[
            InstallAction(
                action_id="check-python",
                kind="check",
                command=["python", "--version"],
                cwd=project_root,
                env_overrides={},
                risk_level="low",
                description="Check Python availability.",
            ),
            InstallAction(
                action_id="create-environment",
                kind="create_env",
                command=["python", "-m", "venv", ".venv"],
                cwd=project_root,
                env_overrides={},
                risk_level="medium",
                description="Create the environment.",
            ),
        ],
        warnings=[],
        assumptions=[],
    )


def _make_failure_plan(
    project_root: Path,
    *,
    python_version: str = "3.10",
    pytorch_strategy: object | None = None,
    mirror_config: object | None = None,
) -> InstallPlan:
    from quick_env_setup.models import MirrorConfig
    from quick_env_setup.models import ProjectProfile, ProjectScanResult, PyTorchStrategy
    from quick_env_setup.models import PythonRequirement, SourceResolutionResult, SourceSpec
    from quick_env_setup.models import SystemInfo, DeviceInfo

    project_root.mkdir(parents=True, exist_ok=True)
    resolved_pytorch_strategy = (
        pytorch_strategy
        if isinstance(pytorch_strategy, PyTorchStrategy)
        else PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="not needed",
        )
    )
    resolved_mirror_config = (
        mirror_config
        if isinstance(mirror_config, MirrorConfig)
        else MirrorConfig(
            enabled=False,
            provider="none",
            pip_index_url=None,
            conda_channels=[],
        )
    )

    return InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw=str(project_root),
                source_type="local_path",
                normalized=str(project_root),
            ),
            local_project_path=project_root,
            clone_performed=False,
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
            root=project_root,
            detected_files=[],
            dependency_files=[],
            readme_path=None,
            python_entry_candidates=[],
            notebook_paths=[],
            keywords=set(),
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.8,
            needs_pytorch=resolved_pytorch_strategy.required,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version=python_version,
            source="default",
            rationale="default",
        ),
        env_manager="venv",
        env_name=f"{project_root.name}-env",
        device_info=DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        ),
        pytorch_strategy=resolved_pytorch_strategy,
        mirror_config=resolved_mirror_config,
        safety_level=2,
        actions=[],
        warnings=[],
        assumptions=[],
    )

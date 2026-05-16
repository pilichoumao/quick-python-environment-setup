from __future__ import annotations

import json
from pathlib import Path

from quick_env_setup.models import (
    DeviceInfo,
    FinalReport,
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
    ValidationReport,
)
from quick_env_setup.report_generator import generate_final_report
from quick_env_setup.run_command_discoverer import discover_run_candidates


def test_discover_run_candidates_uses_readme_and_entrypoints(tmp_path: Path) -> None:
    project_root = tmp_path / "demo-project"
    (project_root / "src" / "demo_package").mkdir(parents=True)
    (project_root / "README.md").write_text(
        "\n".join(
            [
                "# Demo",
                "Run the API locally:",
                "```bash",
                "uvicorn app:app --reload",
                "python -m demo_package",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("app = object()\n", encoding="utf-8")
    (project_root / "demo.py").write_text("print('demo')\n", encoding="utf-8")
    (project_root / "inference.py").write_text("print('inference')\n", encoding="utf-8")
    (project_root / "src" / "demo_package" / "__main__.py").write_text(
        "print('package')\n",
        encoding="utf-8",
    )

    scan = ProjectScanResult(
        root=project_root,
        detected_files=[
            project_root / "README.md",
            project_root / "app.py",
            project_root / "demo.py",
            project_root / "inference.py",
            project_root / "src" / "demo_package" / "__main__.py",
        ],
        dependency_files=[],
        readme_path=project_root / "README.md",
        python_entry_candidates=["app.py", "demo.py", "inference.py", "src/demo_package/__main__.py"],
        notebook_paths=[],
        keywords={"fastapi"},
        parsed_dependency_hints={},
    )

    candidates = discover_run_candidates(scan)

    assert candidates == [
        "uvicorn app:app --reload",
        "python -m demo_package",
        "python app.py",
        "python demo.py",
        "python inference.py",
    ]


def test_discover_run_candidates_skips_invalid_module_paths() -> None:
    project_root = Path("/tmp/demo-project")
    scan = ProjectScanResult(
        root=project_root,
        detected_files=[],
        dependency_files=[],
        readme_path=None,
        python_entry_candidates=["src/demo-package/server/__main__.py"],
        notebook_paths=[],
        keywords=set(),
        parsed_dependency_hints={},
    )

    candidates = discover_run_candidates(scan)

    assert candidates == []


def test_generate_final_report_writes_expected_artifacts(tmp_path: Path) -> None:
    project_root = tmp_path / "example-project"
    project_root.mkdir()
    readme_path = project_root / "README.md"
    readme_path.write_text("# Example\n", encoding="utf-8")
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
            detected_files=[readme_path, project_root / "app.py"],
            dependency_files=[],
            readme_path=readme_path,
            python_entry_candidates=["app.py"],
            notebook_paths=[],
            keywords={"fastapi"},
            parsed_dependency_hints={},
        ),
        project_profile=ProjectProfile(
            project_type="web",
            confidence=0.85,
            needs_pytorch=False,
            recommended_env_manager="venv",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.11",
            source="default",
            rationale="Default selection.",
        ),
        env_manager="venv",
        env_name="example-project-env",
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
            rationale="Not required.",
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
                action_id="create-environment",
                kind="create_env",
                command=["python3", "-m", "venv", ".venv"],
                cwd=project_root,
                env_overrides={},
                risk_level="low",
                description="Create the virtual environment.",
            )
        ],
        warnings=["Use a dedicated virtual environment."],
        assumptions=["The project source is already present."],
    )
    validation = ValidationReport(
        passed=False,
        checks_run=["environment-planned", "asset-scan"],
        failures=["Missing weights/model.pt"],
        warnings=["Run candidates are heuristic only."],
    )

    report = generate_final_report(
        base_dir=tmp_path,
        plan=plan,
        validation=validation,
        run_candidates=["python app.py"],
        missing_assets=["weights/model.pt :: Download from project README"],
        error_summary_lines=["Missing weights/model.pt"],
        agent_trace_lines=["scan_project", "discover_run_candidates", "generate_final_report"],
    )

    artifact_dir = tmp_path / ".env_setup_logs"
    expected_files = {
        "detected_config.json",
        "install_plan.json",
        "error_summary.txt",
        "run_candidates.txt",
        "missing_assets.txt",
        "final_report.txt",
        "agent_trace_summary.txt",
    }

    assert isinstance(report, FinalReport)
    assert {path.name for path in artifact_dir.iterdir()} == expected_files
    detected_config = json.loads((artifact_dir / "detected_config.json").read_text(encoding="utf-8"))
    assert detected_config == {
        "source_type": "local_path",
        "source": str(project_root),
        "local_project_path": str(project_root),
        "os": "linux",
        "arch": "x86_64",
        "project_type": "web",
        "env_manager": "venv",
        "env_name": "example-project-env",
        "python_version": "3.11",
        "has_nvidia_gpu": False,
        "device_strategy": "cpu",
        "needs_pytorch": False,
        "pytorch_install_type": "none",
        "use_china_mirror": False,
        "mirror": "none",
        "safety_level": 2,
        "validation_status": "failed",
        "run_candidate_count": 1,
        "run_candidates": ["python app.py"],
        "missing_asset_count": 1,
        "missing_assets": ["weights/model.pt :: Download from project README"],
    }
    assert json.loads((artifact_dir / "install_plan.json").read_text(encoding="utf-8"))["env_name"] == "example-project-env"
    assert (artifact_dir / "error_summary.txt").read_text(encoding="utf-8").splitlines() == [
        "Missing weights/model.pt"
    ]
    assert (artifact_dir / "run_candidates.txt").read_text(encoding="utf-8").splitlines() == [
        "python app.py"
    ]
    assert (artifact_dir / "missing_assets.txt").read_text(encoding="utf-8").splitlines() == [
        "weights/model.pt :: Download from project README"
    ]
    final_report_text = (artifact_dir / "final_report.txt").read_text(encoding="utf-8")
    assert "Status: attention_needed" in final_report_text
    assert f"Source: {project_root}" in final_report_text
    assert f"Local path: {project_root}" in final_report_text
    assert "Environment manager: venv" in final_report_text
    assert "Python version: 3.11" in final_report_text
    assert "Device strategy: cpu" in final_report_text
    assert "PyTorch: none" in final_report_text
    assert "Validation: failed" in final_report_text
    assert "Run candidates:" in final_report_text
    assert "Missing assets:" in final_report_text
    assert "Warnings:" in final_report_text
    assert "Activate and run:" not in final_report_text
    assert "- source .venv/bin/activate" not in final_report_text
    assert "- Use a dedicated virtual environment." in final_report_text
    assert "- Run candidates are heuristic only." in final_report_text
    assert (
        artifact_dir / "agent_trace_summary.txt"
    ).read_text(encoding="utf-8").splitlines() == [
        "scan_project",
        "discover_run_candidates",
        "generate_final_report",
    ]


def test_generate_final_report_includes_conda_activation_and_run_hint(tmp_path: Path) -> None:
    project_root = tmp_path / "example-project"
    project_root.mkdir()
    plan = InstallPlan(
        source_result=SourceResolutionResult(
            source=SourceSpec(
                raw="https://github.com/example/project",
                source_type="git_url",
                normalized="https://github.com/example/project",
            ),
            local_project_path=project_root,
            clone_performed=False,
            repo_url="https://github.com/example/project",
        ),
        system_info=SystemInfo(
            os_name="windows",
            arch="x86_64",
            is_apple_silicon=False,
            has_conda=True,
            has_git=True,
            python_executables=["python"],
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
            recommended_env_manager="conda",
            editable_install_recommended=False,
        ),
        python_requirement=PythonRequirement(
            version="3.10",
            source="default",
            rationale="Default selection.",
        ),
        env_manager="conda",
        env_name="demo-env",
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
            rationale="Not required.",
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
    validation = ValidationReport(
        passed=True,
        checks_run=["python --version"],
        failures=[],
        warnings=[],
    )

    generate_final_report(
        base_dir=tmp_path,
        plan=plan,
        validation=validation,
        run_candidates=["python app.py"],
        missing_assets=[],
    )

    final_report_text = (tmp_path / ".env_setup_logs" / "final_report.txt").read_text(encoding="utf-8")

    assert "Activate and run:" in final_report_text
    assert "- conda activate demo-env" in final_report_text
    assert "- python app.py" in final_report_text


def test_generate_final_report_guides_failed_recovery_with_specific_artifacts(tmp_path: Path) -> None:
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
            rationale="Default selection.",
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
            required=True,
            install_separately=True,
            variant="cuda",
            index_url="https://download.pytorch.org/whl/cu121",
            packages=["torch", "torchvision"],
            stripped_requirements_path=None,
            rationale="GPU requested.",
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
    validation = ValidationReport(
        passed=False,
        checks_run=["install-actions"],
        failures=[
            "Category: pytorch_cuda_mismatch",
            "Summary: Installed PyTorch packages do not match the CUDA runtime.",
            "Why this likely happened: The selected wheels target a different CUDA runtime than this machine or companion packages.",
            "Evidence:",
            "- RuntimeError: Detected that PyTorch and torchvision were compiled with different CUDA versions.",
            "Recommended next steps:",
            "- Install matching torch, torchvision, and torchaudio builds for the same CUDA runtime.",
        ],
        warnings=[],
    )

    generate_final_report(
        base_dir=tmp_path,
        plan=plan,
        validation=validation,
        run_candidates=[],
        missing_assets=[],
        error_summary_lines=validation.failures,
    )

    final_report_text = (tmp_path / ".env_setup_logs" / "final_report.txt").read_text(encoding="utf-8")

    assert "Validation: failed" in final_report_text
    assert "Activate and run:" not in final_report_text
    assert "- Diagnose the install failure in error_summary.txt before retrying the setup." in final_report_text
    assert "- First recovery step: Install matching torch, torchvision, and torchaudio builds for the same CUDA runtime." in final_report_text
    assert "- Detected failure category: pytorch_cuda_mismatch." in final_report_text
    assert "- Verify the selected PyTorch build matches the target CUDA runtime for this machine." in final_report_text

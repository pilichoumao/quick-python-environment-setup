from __future__ import annotations

from pathlib import Path

from quick_env_setup.logger import (
    append_command_log_line,
    artifact_path,
    ensure_log_dir,
)
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
    dataclass_to_dict,
)


def test_runtime_models_serialize_for_reporting(tmp_path: Path) -> None:
    source = SourceSpec(
        raw="./example-project",
        source_type="local_path",
        normalized=str(tmp_path / "example-project"),
    )
    source_result = SourceResolutionResult(
        source=source,
        local_project_path=tmp_path / "example-project",
        clone_performed=False,
    )
    system_info = SystemInfo(
        os_name="linux",
        arch="x86_64",
        is_apple_silicon=False,
        has_conda=True,
        has_git=True,
        python_executables=["python3"],
    )
    project_scan = ProjectScanResult(
        root=tmp_path / "example-project",
        detected_files=[tmp_path / "example-project" / "pyproject.toml"],
        dependency_files=[tmp_path / "example-project" / "requirements.txt"],
        readme_path=tmp_path / "example-project" / "README.md",
        python_entry_candidates=["main.py"],
        notebook_paths=[],
        keywords={"torch", "trainer"},
        parsed_dependency_hints={"requires_python": ">=3.10"},
    )
    profile = ProjectProfile(
        project_type="deep_learning",
        confidence=0.92,
        needs_pytorch=True,
        recommended_env_manager="conda",
        editable_install_recommended=True,
    )
    python_requirement = PythonRequirement(
        version="3.10",
        source="pyproject_toml",
        rationale="Project metadata requires Python 3.10+.",
    )
    device_info = DeviceInfo(
        accelerator_type="nvidia",
        gpu_name="RTX 4090",
        cuda_driver_version="550.54",
        cuda_runtime_version="12.4",
        nvidia_smi_available=True,
    )
    pytorch_strategy = PyTorchStrategy(
        required=True,
        install_separately=True,
        variant="cuda",
        index_url="https://download.pytorch.org/whl/cu124",
        packages=["torch", "torchvision"],
        stripped_requirements_path=tmp_path / "requirements.no_torch.txt",
        rationale="Use CUDA wheels before general dependencies.",
    )
    mirror_config = MirrorConfig(
        enabled=True,
        provider="tuna",
        pip_index_url="https://pypi.tuna.tsinghua.edu.cn/simple",
        conda_channels=["defaults"],
    )
    actions = [
        InstallAction(
            action_id="create-env",
            kind="create_env",
            command=["conda", "create", "-n", "example-env", "python=3.10"],
            cwd=tmp_path,
            env_overrides={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
            risk_level="low",
            description="Create the environment.",
        )
    ]
    plan = InstallPlan(
        source_result=source_result,
        system_info=system_info,
        project_scan=project_scan,
        project_profile=profile,
        python_requirement=python_requirement,
        env_manager="conda",
        env_name="example-env",
        device_info=device_info,
        pytorch_strategy=pytorch_strategy,
        mirror_config=mirror_config,
        safety_level=2,
        actions=actions,
        warnings=["Mirror use is enabled."],
        assumptions=["The repository already exists locally."],
    )

    serialized = dataclass_to_dict(plan)

    assert serialized["source_result"]["source"]["source_type"] == "local_path"
    assert serialized["project_profile"]["project_type"] == "deep_learning"
    assert serialized["pytorch_strategy"]["variant"] == "cuda"
    assert serialized["actions"][0]["command"][0] == "conda"
    assert serialized["project_scan"]["detected_files"] == [
        str(tmp_path / "example-project" / "pyproject.toml")
    ]
    assert sorted(serialized["project_scan"]["keywords"]) == ["torch", "trainer"]


def test_dataclass_to_dict_handles_mixed_set_values_without_sorting() -> None:
    serialized = dataclass_to_dict({"items": {"alpha", 2}})

    assert set(serialized["items"]) == {"alpha", 2}


def test_logger_helpers_create_and_append_artifacts(tmp_path: Path) -> None:
    log_dir = ensure_log_dir(tmp_path)
    command_log = artifact_path(tmp_path, "commands.log")

    append_command_log_line(command_log, "python -m pip install -r requirements.txt")

    assert log_dir == tmp_path / ".env_setup_logs"
    assert command_log == log_dir / "commands.log"
    assert command_log.exists()

    lines = command_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "python -m pip install -r requirements.txt" in lines[0]

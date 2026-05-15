from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal


SourceType = Literal["git_url", "local_path"]
OsName = Literal["windows", "macos", "linux"]
ProjectType = Literal[
    "deep_learning",
    "python_package",
    "web",
    "notebook",
    "cli_tool",
    "data_analysis",
    "uncertain",
]
EnvManager = Literal["conda", "venv"]
PythonRequirementSource = Literal[
    "environment_yml",
    "conda_yml",
    "pyproject_toml",
    "setup_py",
    "setup_cfg",
    "readme",
    "default",
    "user_override",
]
AcceleratorType = Literal["cpu", "nvidia", "apple_mps", "amd_unknown"]
PyTorchVariant = Literal["none", "cpu", "cuda", "mps"]
MirrorProvider = Literal["none", "tuna", "ustc", "aliyun"]
InstallActionKind = Literal[
    "check",
    "clone",
    "create_env",
    "upgrade_packaging_tools",
    "install_pytorch",
    "install_dependencies",
    "editable_install",
    "validate",
    "discover",
    "report",
]
RiskLevel = Literal["low", "medium", "high"]
ConflictCategory = Literal[
    "python_version_incompatible",
    "package_conflict",
    "missing_build_tools",
    "missing_system_library",
    "pytorch_cuda_mismatch",
    "network_failure",
    "missing_assets",
    "project_code_issue",
    "unknown",
]


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: dataclass_to_dict(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): dataclass_to_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, set):
        return [dataclass_to_dict(item) for item in value]
    return value


@dataclass(slots=True)
class SourceSpec:
    raw: str
    source_type: SourceType
    normalized: str


@dataclass(slots=True)
class SourceResolutionResult:
    source: SourceSpec
    local_project_path: Path
    clone_performed: bool
    repo_url: str | None = None


@dataclass(slots=True)
class SystemInfo:
    os_name: OsName
    arch: str
    is_apple_silicon: bool
    has_conda: bool
    has_git: bool
    python_executables: list[str]


@dataclass(slots=True)
class ProjectScanResult:
    root: Path
    detected_files: list[Path]
    dependency_files: list[Path]
    readme_path: Path | None
    python_entry_candidates: list[str]
    notebook_paths: list[Path]
    keywords: set[str]
    parsed_dependency_hints: dict[str, Any]


@dataclass(slots=True)
class ProjectProfile:
    project_type: ProjectType
    confidence: float
    needs_pytorch: bool
    recommended_env_manager: EnvManager
    editable_install_recommended: bool


@dataclass(slots=True)
class PythonRequirement:
    version: str
    source: PythonRequirementSource
    rationale: str


@dataclass(slots=True)
class DeviceInfo:
    accelerator_type: AcceleratorType
    gpu_name: str | None
    cuda_driver_version: str | None
    cuda_runtime_version: str | None
    nvidia_smi_available: bool


@dataclass(slots=True)
class PyTorchStrategy:
    required: bool
    install_separately: bool
    variant: PyTorchVariant
    index_url: str | None
    packages: list[str]
    stripped_requirements_path: Path | None
    rationale: str


@dataclass(slots=True)
class MirrorConfig:
    enabled: bool
    provider: MirrorProvider
    pip_index_url: str | None
    conda_channels: list[str]


@dataclass(slots=True)
class InstallAction:
    action_id: str
    kind: InstallActionKind
    command: list[str] | None
    cwd: Path | None
    env_overrides: dict[str, str]
    risk_level: RiskLevel
    description: str
    skippable: bool = False


@dataclass(slots=True)
class InstallPlan:
    source_result: SourceResolutionResult
    system_info: SystemInfo
    project_scan: ProjectScanResult
    project_profile: ProjectProfile
    python_requirement: PythonRequirement
    env_manager: EnvManager
    env_name: str
    device_info: DeviceInfo
    pytorch_strategy: PyTorchStrategy
    mirror_config: MirrorConfig
    safety_level: int
    actions: list[InstallAction]
    warnings: list[str]
    assumptions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)


@dataclass(slots=True)
class ExecutionResult:
    success: bool
    completed_action_ids: list[str]
    failed_action_id: str | None
    exit_code: int | None
    log_path: Path
    stdout_tail: str
    stderr_tail: str


@dataclass(slots=True)
class ConflictReport:
    category: ConflictCategory
    summary: str
    evidence: list[str]
    recommendations: list[str]


@dataclass(slots=True)
class ValidationReport:
    passed: bool
    checks_run: list[str]
    failures: list[str]


@dataclass(slots=True)
class FinalReport:
    overview: dict[str, Any]
    validation: ValidationReport
    run_candidates: list[str]
    missing_assets: list[str]
    warnings: list[str]
    next_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)

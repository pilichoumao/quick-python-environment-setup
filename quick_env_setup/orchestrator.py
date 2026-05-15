from __future__ import annotations

import sys
from pathlib import Path

from quick_env_setup.env_manager import EnvironmentTarget, get_env_manager
from quick_env_setup.git_handler import build_clone_command, select_clone_target_path
from quick_env_setup.mirror_manager import get_mirror_config
from quick_env_setup.models import (
    EnvManager,
    InstallAction,
    InstallPlan,
    MirrorProvider,
    ProjectScanResult,
    SourceResolutionResult,
)
from quick_env_setup.project_scanner import scan_project
from quick_env_setup.project_type_detector import detect_project_profile
from quick_env_setup.python_version_resolver import resolve_python_requirement
from quick_env_setup.device_detector import resolve_device_info
from quick_env_setup.pytorch_resolver import resolve_pytorch_strategy
from quick_env_setup.safety_policy import (
    apply_safety_policy,
    risk_level_for_action_kind,
    validate_requested_operations,
)
from quick_env_setup.source_resolver import parse_source_spec
from quick_env_setup.system_detector import detect_system_info


def build_install_plan(
    *,
    source: str,
    env_manager: EnvManager | None = None,
    env_name: str | None = None,
    python_version: str | None = None,
    clone_dir: str | None = None,
    cpu_only: bool = False,
    use_china_mirror: bool = False,
    mirror: MirrorProvider | None = None,
    safety_level: int = 2,
    run_demo: bool = False,
) -> InstallPlan:
    validate_requested_operations(safety_level=safety_level, run_demo=run_demo)

    source_result = _resolve_source(source=source, clone_dir=clone_dir)
    system_info = detect_system_info(python_executables=[Path(sys.executable).name])
    project_scan = _scan_or_stub_project(source_result)
    project_profile = detect_project_profile(project_scan)
    python_requirement = resolve_python_requirement(
        project_scan,
        user_override=python_version,
    )
    selected_env_manager = _select_env_manager(
        requested=env_manager,
        recommended=project_profile.recommended_env_manager,
    )
    selected_env_name = env_name or _default_env_name(source_result.local_project_path)
    device_info = resolve_device_info(system_info, cpu_only=cpu_only)
    pytorch_strategy = resolve_pytorch_strategy(
        project_scan,
        device_info,
        cpu_only=cpu_only,
    )
    mirror_provider: MirrorProvider | None = _resolve_mirror_provider(
        use_china_mirror=use_china_mirror,
        mirror=mirror,
    )
    mirror_config = get_mirror_config(mirror_provider)

    warnings = _build_warnings(
        source_result=source_result,
        system_info=system_info,
        env_manager=selected_env_manager,
    )
    assumptions = _build_assumptions(
        source_result=source_result,
        project_scan=project_scan,
    )

    proposed_actions = _build_actions(
        source_result=source_result,
        system_info=system_info,
        project_scan=project_scan,
        project_profile=project_profile,
        python_version=python_requirement.version,
        env_manager_name=selected_env_manager,
        env_name=selected_env_name,
        pytorch_required=pytorch_strategy.required,
        pytorch_install_separately=pytorch_strategy.install_separately,
        pytorch_packages=pytorch_strategy.packages,
        pytorch_index_url=pytorch_strategy.index_url,
        stripped_requirements_path=pytorch_strategy.stripped_requirements_path,
        mirror_config=mirror_config,
    )
    allowed_actions, safety_warnings = apply_safety_policy(
        proposed_actions,
        safety_level=safety_level,
        allow_high_risk=run_demo and safety_level >= 3,
    )
    warnings.extend(safety_warnings)

    return InstallPlan(
        source_result=source_result,
        system_info=system_info,
        project_scan=project_scan,
        project_profile=project_profile,
        python_requirement=python_requirement,
        env_manager=selected_env_manager,
        env_name=selected_env_name,
        device_info=device_info,
        pytorch_strategy=pytorch_strategy,
        mirror_config=mirror_config,
        safety_level=safety_level,
        actions=allowed_actions,
        warnings=warnings,
        assumptions=assumptions,
    )


def execute_install_plan(plan: InstallPlan) -> None:
    raise NotImplementedError(
        "Install execution is not implemented yet; use --dry-run to inspect the plan."
    )


def _resolve_source(*, source: str, clone_dir: str | None) -> SourceResolutionResult:
    source_spec = parse_source_spec(source)
    if source_spec.source_type == "local_path":
        local_project_path = Path(source_spec.normalized)
        if not local_project_path.exists():
            raise ValueError(f"Local project path does not exist: {local_project_path}")
        return SourceResolutionResult(
            source=source_spec,
            local_project_path=local_project_path,
            clone_performed=False,
        )

    parent_directory = Path(clone_dir).expanduser().resolve() if clone_dir else Path.cwd()
    return SourceResolutionResult(
        source=source_spec,
        local_project_path=select_clone_target_path(source_spec, parent_directory),
        clone_performed=False,
        repo_url=source_spec.normalized,
    )


def _scan_or_stub_project(source_result: SourceResolutionResult) -> ProjectScanResult:
    project_root = source_result.local_project_path
    if project_root.exists():
        return scan_project(project_root)

    return ProjectScanResult(
        root=project_root,
        detected_files=[],
        dependency_files=[],
        readme_path=None,
        python_entry_candidates=[],
        notebook_paths=[],
        keywords=set(),
        parsed_dependency_hints={},
    )


def _select_env_manager(
    *,
    requested: EnvManager | None,
    recommended: EnvManager,
) -> EnvManager:
    return requested or recommended


def _default_env_name(project_root: Path) -> str:
    base = project_root.name.strip().lower() or "project"
    slug = "".join(character if character.isalnum() else "-" for character in base)
    collapsed = "-".join(part for part in slug.split("-") if part)
    return f"{collapsed or 'project'}-env"


def _build_warnings(
    *,
    source_result: SourceResolutionResult,
    system_info: object,
    env_manager: EnvManager,
) -> list[str]:
    from quick_env_setup.models import SystemInfo

    warnings: list[str] = []
    if source_result.source.source_type == "git_url":
        warnings.append(
            "Remote repositories are only planned in this task; cloning is deferred to execution."
        )
        if isinstance(system_info, SystemInfo) and not system_info.has_git:
            warnings.append("Git was not detected on this system; cloning will fail until it is installed.")

    if isinstance(system_info, SystemInfo) and env_manager == "conda" and not system_info.has_conda:
        warnings.append("Conda was not detected on this system; the plan still recommends it.")

    return warnings


def _build_assumptions(
    *,
    source_result: SourceResolutionResult,
    project_scan: ProjectScanResult,
) -> list[str]:
    assumptions: list[str] = []
    if not project_scan.detected_files:
        assumptions.append(
            f"No project files were scanned at {source_result.local_project_path}; planning used conservative defaults."
        )
    return assumptions


def _build_actions(
    *,
    source_result: SourceResolutionResult,
    system_info: object,
    project_scan: ProjectScanResult,
    project_profile: object,
    python_version: str,
    env_manager_name: EnvManager,
    env_name: str,
    pytorch_required: bool,
    pytorch_install_separately: bool,
    pytorch_packages: list[str],
    pytorch_index_url: str | None,
    stripped_requirements_path: Path | None,
    mirror_config: object,
) -> list[InstallAction]:
    from quick_env_setup.models import MirrorConfig, ProjectProfile, SystemInfo

    if not isinstance(system_info, SystemInfo):
        raise TypeError("system_info must be a SystemInfo instance")
    if not isinstance(project_profile, ProjectProfile):
        raise TypeError("project_profile must be a ProjectProfile instance")
    if not isinstance(mirror_config, MirrorConfig):
        raise TypeError("mirror_config must be a MirrorConfig instance")

    actions: list[InstallAction] = []

    if source_result.source.source_type == "git_url" and source_result.repo_url is not None:
        actions.append(
            InstallAction(
                action_id="check-git",
                kind="check",
                command=["git", "--version"],
                cwd=source_result.local_project_path.parent,
                env_overrides={},
                risk_level=risk_level_for_action_kind("check"),
                description="Check that git is available before cloning a remote source.",
            )
        )
        actions.append(
            InstallAction(
                action_id="clone-source",
                kind="clone",
                command=build_clone_command(
                    source_result.repo_url,
                    source_result.local_project_path,
                ),
                cwd=source_result.local_project_path.parent,
                env_overrides={},
                risk_level=risk_level_for_action_kind("clone"),
                description="Clone the requested repository into an isolated working directory.",
            )
        )

    manager = get_env_manager(env_manager_name)
    target = _environment_target(
        manager_name=env_manager_name,
        env_name=env_name,
        project_root=source_result.local_project_path,
    )

    if env_manager_name == "conda":
        actions.append(
            InstallAction(
                action_id="check-conda",
                kind="check",
                command=["conda", "--version"],
                cwd=source_result.local_project_path,
                env_overrides={},
                risk_level=risk_level_for_action_kind("check"),
                description="Check that conda is available before creating the planned environment.",
            )
        )

    actions.append(
        InstallAction(
            action_id="create-environment",
            kind="create_env",
            command=manager.build_create_command(target, python_version),
            cwd=source_result.local_project_path,
            env_overrides={},
            risk_level=risk_level_for_action_kind("create_env"),
            description="Create an isolated Python environment for the project.",
        )
    )

    actions.append(
        InstallAction(
            action_id="upgrade-packaging-tools",
            kind="upgrade_packaging_tools",
            command=_build_packaging_upgrade_command(
                manager_name=env_manager_name,
                target=target,
                os_name=system_info.os_name,
            ),
            cwd=source_result.local_project_path,
            env_overrides={},
            risk_level=risk_level_for_action_kind("upgrade_packaging_tools"),
            description="Upgrade pip, setuptools, and wheel inside the planned environment.",
        )
    )

    dependency_command = _build_dependency_install_command(
        manager=manager,
        target=target,
        project_scan=project_scan,
        env_manager_name=env_manager_name,
        env_name=env_name,
        os_name=system_info.os_name,
        mirror_config=mirror_config,
        pytorch_install_separately=pytorch_install_separately,
        stripped_requirements_path=stripped_requirements_path,
    )

    if pytorch_required and pytorch_install_separately and pytorch_packages:
        actions.append(
            InstallAction(
                action_id="install-pytorch",
                kind="install_pytorch",
                command=_build_pytorch_install_command(
                    manager_name=env_manager_name,
                    target=target,
                    os_name=system_info.os_name,
                    packages=pytorch_packages,
                    index_url=pytorch_index_url,
                ),
                cwd=source_result.local_project_path,
                env_overrides={},
                risk_level=risk_level_for_action_kind("install_pytorch"),
                description="Install the planned PyTorch distribution before generic dependencies.",
            )
        )

    if dependency_command is not None:
        actions.append(
            InstallAction(
                action_id="install-dependencies",
                kind="install_dependencies",
                command=dependency_command,
                cwd=source_result.local_project_path,
                env_overrides={},
                risk_level=risk_level_for_action_kind("install_dependencies"),
                description="Install project dependencies using the selected dependency source.",
            )
        )

    if project_profile.editable_install_recommended:
        actions.append(
            InstallAction(
                action_id="editable-install",
                kind="editable_install",
                command=_build_editable_install_command(
                    manager_name=env_manager_name,
                    target=target,
                    os_name=system_info.os_name,
                    project_root=source_result.local_project_path,
                    mirror_config=mirror_config,
                ),
                cwd=source_result.local_project_path,
                env_overrides={},
                risk_level=risk_level_for_action_kind("editable_install"),
                description="Install the local package in editable mode.",
            )
        )

    return actions


def _resolve_mirror_provider(
    *,
    use_china_mirror: bool,
    mirror: MirrorProvider | None,
) -> MirrorProvider:
    if not use_china_mirror:
        return "none"
    if mirror is not None:
        return mirror
    return "tuna"


def _environment_target(
    *,
    manager_name: EnvManager,
    env_name: str,
    project_root: Path,
) -> EnvironmentTarget:
    if manager_name == "conda":
        return EnvironmentTarget.for_conda(env_name)
    return EnvironmentTarget.for_venv(project_root / ".venv")


def _build_packaging_upgrade_command(
    *,
    manager_name: EnvManager,
    target: EnvironmentTarget,
    os_name: str,
) -> list[str]:
    base = _environment_python_command(
        manager_name=manager_name,
        target=target,
        os_name=os_name,
    )
    return [*base, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]


def _build_pytorch_install_command(
    *,
    manager_name: EnvManager,
    target: EnvironmentTarget,
    os_name: str,
    packages: list[str],
    index_url: str | None,
) -> list[str]:
    command = [
        *_environment_python_command(
            manager_name=manager_name,
            target=target,
            os_name=os_name,
        ),
        "-m",
        "pip",
        "install",
        *packages,
    ]
    if index_url:
        command.extend(["--index-url", index_url])
    return command


def _build_editable_install_command(
    *,
    manager_name: EnvManager,
    target: EnvironmentTarget,
    os_name: str,
    project_root: Path,
    mirror_config: object,
) -> list[str]:
    from quick_env_setup.mirror_manager import pip_args_for_mirror
    from quick_env_setup.models import MirrorConfig

    if not isinstance(mirror_config, MirrorConfig):
        raise TypeError("mirror_config must be a MirrorConfig instance")

    return [
        *_environment_python_command(
            manager_name=manager_name,
            target=target,
            os_name=os_name,
        ),
        "-m",
        "pip",
        "install",
        *pip_args_for_mirror(mirror_config),
        "-e",
        str(project_root),
    ]


def _environment_python_command(
    *,
    manager_name: EnvManager,
    target: EnvironmentTarget,
    os_name: str,
) -> list[str]:
    if manager_name == "conda":
        return ["conda", "run", "-n", target.require_env_name(), "python"]
    if os_name == "windows":
        return [str(target.require_env_path() / "Scripts" / "python.exe")]
    return [str(target.require_env_path() / "bin" / "python")]


def _select_dependency_install_file(
    *,
    project_scan: ProjectScanResult,
    pytorch_install_separately: bool,
    stripped_requirements_path: Path | None,
) -> Path | None:
    preferred_names = ("requirements.txt", "requirements-dev.txt", "requirements.in")
    dependency_by_name = {path.name: path for path in project_scan.dependency_files}
    for name in preferred_names:
        if name in dependency_by_name:
            if (
                pytorch_install_separately
                and stripped_requirements_path is not None
                and name == "requirements.txt"
            ):
                return stripped_requirements_path
            return dependency_by_name[name]
    return None


def _build_dependency_install_command(
    *,
    manager: object,
    target: EnvironmentTarget,
    project_scan: ProjectScanResult,
    env_manager_name: EnvManager,
    env_name: str,
    os_name: str,
    mirror_config: object,
    pytorch_install_separately: bool,
    stripped_requirements_path: Path | None,
) -> list[str] | None:
    from quick_env_setup.models import MirrorConfig

    if not isinstance(mirror_config, MirrorConfig):
        raise TypeError("mirror_config must be a MirrorConfig instance")

    requirements_file = _select_dependency_install_file(
        project_scan=project_scan,
        pytorch_install_separately=pytorch_install_separately,
        stripped_requirements_path=stripped_requirements_path,
    )
    if requirements_file is not None:
        return manager.build_pip_install_command(
            target,
            requirements_file,
            mirror_config=mirror_config,
            os_name=os_name,
        )

    conda_environment_file = _select_conda_environment_file(project_scan)
    if conda_environment_file is None or env_manager_name != "conda":
        return None

    return [
        "conda",
        "env",
        "update",
        "-n",
        env_name,
        "-f",
        str(conda_environment_file),
    ]


def _select_conda_environment_file(project_scan: ProjectScanResult) -> Path | None:
    preferred_names = ("environment.yml", "environment.yaml", "conda.yml", "conda.yaml")
    dependency_by_name = {path.name: path for path in project_scan.dependency_files}
    for name in preferred_names:
        if name in dependency_by_name:
            return dependency_by_name[name]
    return None

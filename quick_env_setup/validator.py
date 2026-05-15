from __future__ import annotations

import subprocess
from dataclasses import dataclass

from quick_env_setup.models import InstallPlan, ValidationReport


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    name: str
    command: list[str]
    requires_torch: bool = False
    severity: str = "error"


def build_validation_checks(plan: InstallPlan) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = [
        ValidationCheck("python --version", build_python_version_check_command(plan)),
        ValidationCheck("pip --version", build_pip_version_check_command(plan)),
    ]

    include_torch = _should_probe_torch(plan)
    if include_torch:
        checks.append(
            ValidationCheck(
                "import torch",
                build_import_probe_command(plan, "torch"),
            )
        )

    if _should_probe_numpy(plan):
        checks.append(
            ValidationCheck(
                "import numpy",
                build_import_probe_command(plan, "numpy"),
            )
        )

    if _should_probe_cv2(plan):
        checks.append(
            ValidationCheck(
                "import cv2",
                build_import_probe_command(plan, "cv2"),
                severity="warning",
            )
        )

    device_check = build_torch_device_probe_check(plan)
    if device_check is not None:
        checks.append(device_check)

    return checks


def build_import_probe_command(plan: InstallPlan, module_name: str) -> list[str]:
    probe = (
        "import importlib;"
        f"module = importlib.import_module({module_name!r});"
        "print(getattr(module, '__version__', 'ok'))"
    )
    return [*_python_command(plan), "-c", probe]


def build_python_version_check_command(plan: InstallPlan) -> list[str]:
    return [*_python_command(plan), "--version"]


def build_pip_version_check_command(plan: InstallPlan) -> list[str]:
    return [*_pip_command(plan), "--version"]


def build_torch_device_probe_check(plan: InstallPlan) -> ValidationCheck | None:
    if not _should_probe_torch(plan):
        return None

    if plan.pytorch_strategy.variant == "cuda" or plan.device_info.accelerator_type == "nvidia":
        probe = (
            "import torch, sys;"
            "available = torch.cuda.is_available();"
            "print(f'cuda_available={available}');"
            "raise SystemExit(0 if available else 1)"
        )
        return ValidationCheck(
            "torch.cuda.is_available()",
            [*_python_command(plan), "-c", probe],
            requires_torch=True,
            severity="warning",
        )

    if plan.pytorch_strategy.variant == "mps" or plan.device_info.accelerator_type == "apple_mps":
        probe = (
            "import torch, sys;"
            "backend = getattr(torch.backends, 'mps', None);"
            "available = bool(backend and backend.is_available());"
            "print(f'mps_available={available}');"
            "raise SystemExit(0 if available else 1)"
        )
        return ValidationCheck(
            "torch.backends.mps.is_available()",
            [*_python_command(plan), "-c", probe],
            requires_torch=True,
            severity="warning",
        )

    return None


def build_torch_device_probe_command(plan: InstallPlan) -> list[str] | None:
    check = build_torch_device_probe_check(plan)
    if check is None:
        return None
    return check.command


def validate_environment(plan: InstallPlan) -> ValidationReport:
    checks_run: list[str] = []
    failures: list[str] = []
    warnings: list[str] = []
    torch_import_succeeded = True

    for check in build_validation_checks(plan):
        if check.requires_torch and not torch_import_succeeded:
            continue

        try:
            completed = subprocess.run(
                check.command,
                cwd=str(plan.source_result.local_project_path),
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as exc:
            if check.severity == "warning":
                checks_run.append(check.name)
                warnings.append(f"{check.name}: {exc}")
            else:
                checks_run.append(check.name)
                failures.append(f"{check.name}: {exc}")
            if check.name == "import torch":
                torch_import_succeeded = False
            continue

        if completed.returncode != 0:
            if check.severity == "warning":
                checks_run.append(check.name)
                warnings.append(f"{check.name}: {_format_detail(completed.stderr, completed.stdout)}")
            else:
                checks_run.append(check.name)
                failures.append(_format_failure(check.name, completed.stderr, completed.stdout))
            if check.name == "import torch":
                torch_import_succeeded = False
        else:
            checks_run.append(check.name)
            if check.name == "import torch":
                torch_import_succeeded = True

    return ValidationReport(
        passed=not failures,
        checks_run=checks_run,
        failures=failures,
        warnings=warnings,
    )


def _python_command(plan: InstallPlan) -> list[str]:
    if plan.env_manager == "conda":
        return ["conda", "run", "-n", plan.env_name, "python"]
    if plan.system_info.os_name == "windows":
        return [str(plan.source_result.local_project_path / ".venv" / "Scripts" / "python.exe")]
    return [str(plan.source_result.local_project_path / ".venv" / "bin" / "python")]


def _pip_command(plan: InstallPlan) -> list[str]:
    if plan.env_manager == "conda":
        return ["conda", "run", "-n", plan.env_name, "pip"]
    if plan.system_info.os_name == "windows":
        return [str(plan.source_result.local_project_path / ".venv" / "Scripts" / "pip.exe")]
    return [str(plan.source_result.local_project_path / ".venv" / "bin" / "pip")]


def _dependency_packages(plan: InstallPlan) -> set[str]:
    packages = plan.project_scan.parsed_dependency_hints.get("packages", [])
    normalized = {
        str(package).lower()
        for package in packages
        if isinstance(package, str) and package
    }
    normalized.update(keyword.lower() for keyword in plan.project_scan.keywords)
    return normalized


def _should_probe_torch(plan: InstallPlan) -> bool:
    packages = _dependency_packages(plan)
    return (
        plan.project_profile.needs_pytorch
        or plan.pytorch_strategy.required
        or "torch" in packages
        or "pytorch" in packages
    )


def _should_probe_numpy(plan: InstallPlan) -> bool:
    packages = _dependency_packages(plan)
    return "numpy" in packages


def _should_probe_cv2(plan: InstallPlan) -> bool:
    packages = _dependency_packages(plan)
    return any(
        package in packages
        for package in ("opencv-python", "opencv-contrib-python", "opencv-python-headless", "cv2")
    )


def _format_failure(name: str, stderr: str, stdout: str) -> str:
    details = _format_detail(stderr, stdout)
    return f"{name}: {details}"


def _format_detail(stderr: str, stdout: str) -> str:
    return stderr.strip() or stdout.strip() or "validation command failed"

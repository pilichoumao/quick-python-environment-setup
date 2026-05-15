from __future__ import annotations

import shutil
import subprocess
from typing import Callable

from quick_env_setup.models import DeviceInfo, SystemInfo


WhichFunction = Callable[[str], str | None]
RunCommand = Callable[[list[str]], str]


def parse_nvidia_smi_query_output(output: str) -> dict[str, str | None] | None:
    first_line = next(
        (line.strip() for line in output.splitlines() if line.strip()),
        "",
    )
    if not first_line:
        return None

    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 3 or not parts[0]:
        return None

    return {
        "gpu_name": parts[0],
        "cuda_driver_version": _normalize_nvidia_smi_value(parts[1]),
        "cuda_runtime_version": _normalize_nvidia_smi_value(parts[2]),
    }


def detect_nvidia_smi(
    *,
    which: WhichFunction = shutil.which,
    run_command: RunCommand | None = None,
) -> DeviceInfo | None:
    if which("nvidia-smi") is None:
        return None

    output = ""
    if run_command is None:
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,cuda_version",
                    "--format=csv,noheader",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return DeviceInfo(
                accelerator_type="cpu",
                gpu_name=None,
                cuda_driver_version=None,
                cuda_runtime_version=None,
                nvidia_smi_available=True,
            )
        output = completed.stdout
    else:
        output = run_command(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,cuda_version",
                "--format=csv,noheader",
            ]
        )

    parsed = parse_nvidia_smi_query_output(output)
    if parsed is None:
        return DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=True,
        )

    return DeviceInfo(
        accelerator_type="nvidia",
        gpu_name=parsed["gpu_name"] or None,
        cuda_driver_version=parsed["cuda_driver_version"] or None,
        cuda_runtime_version=parsed["cuda_runtime_version"] or None,
        nvidia_smi_available=True,
    )


def _normalize_nvidia_smi_value(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.lower() in {"n/a", "na", "none", "unknown"}:
        return None
    return normalized


def bridge_apple_silicon_device(system_info: SystemInfo) -> DeviceInfo | None:
    if not system_info.is_apple_silicon:
        return None
    return DeviceInfo(
        accelerator_type="apple_mps",
        gpu_name="Apple Silicon",
        cuda_driver_version=None,
        cuda_runtime_version=None,
        nvidia_smi_available=False,
    )


def resolve_device_info(
    system_info: SystemInfo,
    *,
    cpu_only: bool = False,
    which: WhichFunction = shutil.which,
    run_command: RunCommand | None = None,
) -> DeviceInfo:
    if cpu_only:
        return DeviceInfo(
            accelerator_type="cpu",
            gpu_name=None,
            cuda_driver_version=None,
            cuda_runtime_version=None,
            nvidia_smi_available=False,
        )

    if nvidia_device := detect_nvidia_smi(which=which, run_command=run_command):
        if nvidia_device.accelerator_type == "nvidia":
            return nvidia_device

    if apple_device := bridge_apple_silicon_device(system_info):
        return apple_device

    return DeviceInfo(
        accelerator_type="cpu",
        gpu_name=None,
        cuda_driver_version=None,
        cuda_runtime_version=None,
        nvidia_smi_available=False,
    )

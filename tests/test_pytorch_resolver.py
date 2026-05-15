from __future__ import annotations

from pathlib import Path

from quick_env_setup.device_detector import (
    parse_nvidia_smi_query_output,
    resolve_device_info,
)
from quick_env_setup.models import DeviceInfo, ProjectScanResult, SystemInfo
from quick_env_setup.pytorch_resolver import resolve_pytorch_strategy


def _make_project_scan(
    root: Path,
    *,
    packages: list[str] | None = None,
    keywords: set[str] | None = None,
) -> ProjectScanResult:
    return ProjectScanResult(
        root=root,
        detected_files=[],
        dependency_files=[],
        readme_path=None,
        python_entry_candidates=[],
        notebook_paths=[],
        keywords=keywords or set(),
        parsed_dependency_hints={
            "packages": list(packages or []),
            "has_pyproject": False,
            "has_requirements_txt": bool(packages),
        },
    )


def _make_system_info(*, apple_silicon: bool = False) -> SystemInfo:
    return SystemInfo(
        os_name="macos" if apple_silicon else "linux",
        arch="arm64" if apple_silicon else "x86_64",
        is_apple_silicon=apple_silicon,
        has_conda=True,
        has_git=True,
        python_executables=["python3"],
    )


def _make_device_info(
    accelerator_type: str,
    *,
    gpu_name: str | None = None,
    cuda_version: str | None = None,
) -> DeviceInfo:
    return DeviceInfo(
        accelerator_type=accelerator_type,
        gpu_name=gpu_name,
        cuda_driver_version="550.54.14" if cuda_version else None,
        cuda_runtime_version=cuda_version,
        nvidia_smi_available=accelerator_type == "nvidia",
    )


def test_parse_nvidia_smi_query_output_extracts_gpu_metadata() -> None:
    parsed = parse_nvidia_smi_query_output(
        "NVIDIA GeForce RTX 4090, 550.54.14, 12.4\n"
    )

    assert parsed == {
        "gpu_name": "NVIDIA GeForce RTX 4090",
        "cuda_driver_version": "550.54.14",
        "cuda_runtime_version": "12.4",
    }


def test_parse_nvidia_smi_query_output_treats_na_cuda_as_missing() -> None:
    parsed = parse_nvidia_smi_query_output(
        "NVIDIA GeForce RTX 4090, 550.54.14, N/A\n"
    )

    assert parsed == {
        "gpu_name": "NVIDIA GeForce RTX 4090",
        "cuda_driver_version": "550.54.14",
        "cuda_runtime_version": None,
    }


def test_resolve_device_info_detects_nvidia_gpu() -> None:
    device = resolve_device_info(
        _make_system_info(),
        which=lambda command: "/usr/bin/nvidia-smi"
        if command == "nvidia-smi"
        else None,
        run_command=lambda command: "NVIDIA GeForce RTX 4090, 550.54.14, 12.4\n",
    )

    assert device.accelerator_type == "nvidia"
    assert device.gpu_name == "NVIDIA GeForce RTX 4090"
    assert device.cuda_driver_version == "550.54.14"
    assert device.cuda_runtime_version == "12.4"
    assert device.nvidia_smi_available is True


def test_resolve_device_info_bridges_apple_silicon_to_mps() -> None:
    device = resolve_device_info(_make_system_info(apple_silicon=True))

    assert device.accelerator_type == "apple_mps"
    assert device.gpu_name == "Apple Silicon"
    assert device.cuda_driver_version is None
    assert device.cuda_runtime_version is None
    assert device.nvidia_smi_available is False


def test_resolve_pytorch_strategy_cpu_only_flag_forces_cpu(tmp_path: Path) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch", "torchvision", "numpy"],
        keywords={"torch"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 4090", cuda_version="12.4"),
        cpu_only=True,
    )

    assert strategy.required is True
    assert strategy.variant == "cpu"
    assert strategy.index_url == "https://download.pytorch.org/whl/cpu"


def test_resolve_pytorch_strategy_chooses_cuda_for_nvidia_hosts(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch", "torchvision", "torchaudio", "numpy"],
        keywords={"torch", "training"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 4090", cuda_version="12.4"),
    )

    assert strategy.required is True
    assert strategy.install_separately is True
    assert strategy.variant == "cuda"
    assert strategy.index_url == "https://download.pytorch.org/whl/cu124"
    assert strategy.packages == ["torch", "torchvision", "torchaudio"]
    assert strategy.stripped_requirements_path == (
        tmp_path / ".env_setup_logs" / "requirements.no_torch.txt"
    )


def test_resolve_pytorch_strategy_only_plans_detected_torch_packages(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch", "numpy"],
        keywords={"torch", "training"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 4090", cuda_version="12.1"),
    )

    assert strategy.required is True
    assert strategy.packages == ["torch"]
    assert strategy.stripped_requirements_path == (
        tmp_path / ".env_setup_logs" / "requirements.no_torch.txt"
    )
    assert strategy.index_url == "https://download.pytorch.org/whl/cu121"


def test_resolve_pytorch_strategy_uses_cu118_for_cuda_11_8(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch"],
        keywords={"torch", "training"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 3080", cuda_version="11.8"),
    )

    assert strategy.required is True
    assert strategy.variant == "cuda"
    assert strategy.index_url == "https://download.pytorch.org/whl/cu118"


def test_resolve_pytorch_strategy_falls_back_to_oldest_supported_cuda_index(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch"],
        keywords={"torch", "training"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 2080", cuda_version="11.7"),
    )

    assert strategy.required is True
    assert strategy.variant == "cuda"
    assert strategy.index_url == "https://download.pytorch.org/whl/cu118"


def test_resolve_pytorch_strategy_chooses_mps_for_apple_silicon(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch", "numpy"],
        keywords={"pytorch"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("apple_mps", gpu_name="Apple Silicon"),
    )

    assert strategy.required is True
    assert strategy.variant == "mps"
    assert strategy.index_url is None


def test_resolve_pytorch_strategy_defaults_to_cpu_without_accelerator(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch"],
        keywords={"torch"},
    )

    strategy = resolve_pytorch_strategy(project_scan, _make_device_info("cpu"))

    assert strategy.required is True
    assert strategy.variant == "cpu"
    assert strategy.index_url == "https://download.pytorch.org/whl/cpu"


def test_resolve_pytorch_strategy_leaves_cuda_index_unset_for_malformed_runtime(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["torch"],
        keywords={"torch", "training"},
    )

    strategy = resolve_pytorch_strategy(
        project_scan,
        _make_device_info("nvidia", gpu_name="RTX 4090", cuda_version="N/A"),
    )

    assert strategy.required is True
    assert strategy.variant == "cuda"
    assert strategy.index_url is None


def test_resolve_pytorch_strategy_skips_projects_without_torch_hints(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["requests", "fastapi"],
        keywords={"web"},
    )

    strategy = resolve_pytorch_strategy(project_scan, _make_device_info("cpu"))

    assert strategy.required is False
    assert strategy.install_separately is False
    assert strategy.variant == "none"
    assert strategy.index_url is None
    assert strategy.packages == []
    assert strategy.stripped_requirements_path is None


def test_resolve_pytorch_strategy_does_not_plan_from_keyword_only_false_positive(
    tmp_path: Path,
) -> None:
    project_scan = _make_project_scan(
        tmp_path,
        packages=["numpy", "pandas"],
        keywords={"torch"},
    )

    strategy = resolve_pytorch_strategy(project_scan, _make_device_info("cpu"))

    assert strategy.required is False
    assert strategy.install_separately is False
    assert strategy.variant == "none"

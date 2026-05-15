from __future__ import annotations

from quick_env_setup.logger import artifact_path
from quick_env_setup.models import DeviceInfo, ProjectScanResult, PyTorchStrategy


TORCH_PACKAGES = ("torch", "torchvision", "torchaudio")
CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"
CUDA_INDEX_BY_RUNTIME = (
    ((12, 4), "https://download.pytorch.org/whl/cu124"),
    ((12, 1), "https://download.pytorch.org/whl/cu121"),
    ((11, 8), "https://download.pytorch.org/whl/cu118"),
)


def resolve_pytorch_strategy(
    project_scan: ProjectScanResult,
    device_info: DeviceInfo,
    *,
    cpu_only: bool = False,
) -> PyTorchStrategy:
    packages = _normalized_packages(project_scan)
    detected_torch_packages = [name for name in TORCH_PACKAGES if name in packages]
    required = _project_requires_pytorch(project_scan, packages)

    if not required:
        return PyTorchStrategy(
            required=False,
            install_separately=False,
            variant="none",
            index_url=None,
            packages=[],
            stripped_requirements_path=None,
            rationale="No explicit PyTorch package or keyword hints were detected.",
        )

    variant = _resolve_variant(device_info, cpu_only=cpu_only)
    index_url = _index_url_for_variant(variant, device_info)
    planned_packages = _planned_torch_packages(detected_torch_packages)
    stripped_requirements_path = None
    if detected_torch_packages:
        stripped_requirements_path = artifact_path(
            project_scan.root,
            "requirements.no_torch.txt",
        )

    return PyTorchStrategy(
        required=True,
        install_separately=True,
        variant=variant,
        index_url=index_url,
        packages=planned_packages,
        stripped_requirements_path=stripped_requirements_path,
        rationale=_build_rationale(
            variant,
            device_info=device_info,
            cpu_only=cpu_only,
            detected_torch_packages=detected_torch_packages,
            stripped_requirements_path=stripped_requirements_path,
        ),
    )


def _normalized_packages(project_scan: ProjectScanResult) -> set[str]:
    raw_packages = project_scan.parsed_dependency_hints.get("packages", [])
    if not isinstance(raw_packages, list):
        return set()
    return {str(package).strip().lower() for package in raw_packages if str(package).strip()}


def _project_requires_pytorch(
    project_scan: ProjectScanResult,
    packages: set[str],
) -> bool:
    if set(TORCH_PACKAGES) & packages:
        return True
    keywords = {keyword.strip().lower() for keyword in project_scan.keywords}
    has_torch_keyword = bool({"torch", "pytorch"} & keywords)
    has_supporting_keyword = bool({"training", "trainer"} & keywords)
    return has_torch_keyword and has_supporting_keyword


def _planned_torch_packages(detected_torch_packages: list[str]) -> list[str]:
    if detected_torch_packages:
        return detected_torch_packages
    return ["torch"]


def _resolve_variant(device_info: DeviceInfo, *, cpu_only: bool) -> str:
    if cpu_only:
        return "cpu"
    if device_info.accelerator_type == "nvidia":
        return "cuda"
    if device_info.accelerator_type == "apple_mps":
        return "mps"
    return "cpu"


def _index_url_for_variant(variant: str, device_info: DeviceInfo) -> str | None:
    if variant == "cpu":
        return CPU_INDEX_URL
    if variant == "mps":
        return None
    if variant != "cuda":
        return None
    return _resolve_cuda_index_url(device_info.cuda_runtime_version)


def _resolve_cuda_index_url(cuda_runtime_version: str | None) -> str | None:
    parsed_version = _parse_cuda_version(cuda_runtime_version)
    if parsed_version is None:
        return None

    for supported_version, index_url in CUDA_INDEX_BY_RUNTIME:
        if parsed_version >= supported_version:
            return index_url
    return CUDA_INDEX_BY_RUNTIME[-1][1]


def _parse_cuda_version(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.strip().split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _build_rationale(
    variant: str,
    *,
    device_info: DeviceInfo,
    cpu_only: bool,
    detected_torch_packages: list[str],
    stripped_requirements_path: object,
) -> str:
    if cpu_only:
        return "CPU-only mode was requested, so PyTorch will use the official CPU wheels."
    if variant == "cuda":
        details = device_info.gpu_name or "an NVIDIA GPU"
        if device_info.cuda_runtime_version is None:
            base = (
                f"Detected {details}, but the CUDA runtime version was unavailable; "
                "leave the official CUDA wheel index unresolved for a later check."
            )
        else:
            base = f"Detected {details}; selecting the official CUDA wheel index."
    elif variant == "mps":
        base = "Detected Apple Silicon; using the default PyTorch build and planning for MPS validation."
    else:
        base = "No supported accelerator was detected; defaulting conservatively to CPU PyTorch wheels."

    if stripped_requirements_path is None:
        if not detected_torch_packages:
            return f"{base} No explicit torch extras were detected, so only core torch is planned."
        return base
    return f"{base} Torch packages should be removed from the generic requirements install path."

from __future__ import annotations

import re

from quick_env_setup.models import ConflictCategory, ConflictReport


_PATTERNS: tuple[tuple[ConflictCategory, tuple[re.Pattern[str], ...], str, list[str]], ...] = (
    (
        "package_conflict",
        (
            re.compile(r"conflicting dependencies", re.IGNORECASE),
            re.compile(r"resolutionimpossible", re.IGNORECASE),
            re.compile(r"cannot install .* because these package versions have conflicting dependencies", re.IGNORECASE),
        ),
        "Dependency versions in the requested install set are incompatible.",
        [
            "Relax pinned package versions and retry the install.",
            "Install the conflicting packages separately to inspect resolver output.",
        ],
    ),
    (
        "python_version_incompatible",
        (
            re.compile(r"requires a different python", re.IGNORECASE),
            re.compile(r"requires-python", re.IGNORECASE),
            re.compile(r"python .* not in ['\"]?[<>=!,.\d\s]+['\"]?", re.IGNORECASE),
        ),
        "The selected Python interpreter does not satisfy the project or package requirement.",
        [
            "Create the environment with a compatible Python version.",
            "Check pyproject.toml, setup.cfg, setup.py, or README for the required version.",
        ],
    ),
    (
        "missing_build_tools",
        (
            re.compile(r"microsoft visual c\+\+", re.IGNORECASE),
            re.compile(r"gcc.*failed", re.IGNORECASE),
            re.compile(r"python\.h: no such file or directory", re.IGNORECASE),
            re.compile(r"rust compiler", re.IGNORECASE),
        ),
        "A required compiler or native build tool is missing.",
        [
            "Install the missing compiler toolchain for this platform.",
            "Prefer prebuilt wheels when they are available for the current Python version.",
        ],
    ),
    (
        "missing_system_library",
        (
            re.compile(r"cannot open shared object file", re.IGNORECASE),
            re.compile(r"image not found", re.IGNORECASE),
            re.compile(r"dll load failed", re.IGNORECASE),
            re.compile(r"library not loaded", re.IGNORECASE),
        ),
        "A required system library is missing from the host machine.",
        [
            "Install the missing operating-system package that provides the library.",
            "Retry with a wheel built for this platform if one exists.",
        ],
    ),
    (
        "pytorch_cuda_mismatch",
        (
            re.compile(r"different cuda versions", re.IGNORECASE),
            re.compile(r"torch not compiled with cuda enabled", re.IGNORECASE),
            re.compile(r"cuda driver version is insufficient", re.IGNORECASE),
            re.compile(r"pytorch.*cuda version", re.IGNORECASE),
        ),
        "The installed PyTorch stack does not match the available CUDA runtime or companion packages.",
        [
            "Install matching torch, torchvision, and torchaudio builds for the target CUDA runtime.",
            "Use the CPU build when GPU acceleration is not required or the driver is unavailable.",
        ],
    ),
    (
        "network_failure",
        (
            re.compile(r"could not fetch url", re.IGNORECASE),
            re.compile(r"temporary failure in name resolution", re.IGNORECASE),
            re.compile(r"max retries exceeded", re.IGNORECASE),
            re.compile(r"ssl certificate", re.IGNORECASE),
            re.compile(r"read timed out", re.IGNORECASE),
            re.compile(r"connection timed out", re.IGNORECASE),
        ),
        "Dependency download failed because the package index or network path was unavailable.",
        [
            "Retry after confirming network connectivity and index availability.",
            "Configure a trusted mirror when the default package index is slow or blocked.",
        ],
    ),
)


def analyze_install_error(
    output: str | None = None,
    *,
    stdout: str = "",
    stderr: str = "",
) -> ConflictReport:
    combined = _combine_output(output=output, stdout=stdout, stderr=stderr)
    for category, patterns, summary, recommendations in _PATTERNS:
        evidence = _match_evidence(combined, patterns)
        if evidence:
            return ConflictReport(
                category=category,
                summary=summary,
                evidence=evidence,
                recommendations=recommendations,
            )

    fallback_evidence = _fallback_evidence(combined)
    return ConflictReport(
        category="unknown",
        summary="The failure output did not match a known installation conflict pattern.",
        evidence=fallback_evidence,
        recommendations=[
            "Review the captured stdout and stderr for the failing action.",
            "Retry with a narrower install step to isolate the failing dependency or command.",
        ],
    )


def analyze_conflict(
    output: str | None = None,
    *,
    stdout: str = "",
    stderr: str = "",
) -> ConflictReport:
    return analyze_install_error(output, stdout=stdout, stderr=stderr)


def _match_evidence(text: str, patterns: tuple[re.Pattern[str], ...]) -> list[str]:
    evidence: list[str] = []
    for line in _non_empty_lines(text):
        if any(pattern.search(line) for pattern in patterns):
            evidence.append(line.strip())
    return evidence[:3]


def _fallback_evidence(text: str) -> list[str]:
    lines = _non_empty_lines(text)
    if not lines:
        return ["No stdout or stderr was captured."]
    return [line.strip() for line in lines[:3]]


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _combine_output(*, output: str | None, stdout: str, stderr: str) -> str:
    if output is not None and not stdout and not stderr:
        return output
    return "\n".join(part for part in (stderr, stdout, output or "") if part)

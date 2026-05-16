from __future__ import annotations

import re

from quick_env_setup.models import ConflictCategory, ConflictReport


_CATEGORY_SPECS: tuple[dict[str, object], ...] = (
    {
        "category": "python_version_incompatible",
        "patterns": (
            re.compile(r"requires a different python", re.IGNORECASE),
            re.compile(r"requires-python", re.IGNORECASE),
            re.compile(r"requires python", re.IGNORECASE),
            re.compile(r"python .* not in ['\"]?[<>=!,.\d\s]+['\"]?", re.IGNORECASE),
        ),
        "summary": "The selected Python interpreter does not satisfy the project or package requirement.",
        "confidence": 0.95,
        "base_tags": ("python", "requires_python"),
    },
    {
        "category": "pytorch_cuda_mismatch",
        "patterns": (
            re.compile(r"different cuda versions", re.IGNORECASE),
            re.compile(r"torch not compiled with cuda enabled", re.IGNORECASE),
            re.compile(r"cuda driver version is insufficient", re.IGNORECASE),
            re.compile(r"pytorch.*cuda version", re.IGNORECASE),
        ),
        "summary": "The installed PyTorch stack does not match the available CUDA runtime or companion packages.",
        "confidence": 0.95,
        "base_tags": ("pytorch", "cuda"),
    },
    {
        "category": "missing_build_tools",
        "patterns": (
            re.compile(r"microsoft visual c\+\+", re.IGNORECASE),
            re.compile(r"gcc.*failed", re.IGNORECASE),
            re.compile(r"python\.h: no such file or directory", re.IGNORECASE),
            re.compile(r"rust compiler", re.IGNORECASE),
        ),
        "summary": "A required compiler or native build tool is missing.",
        "confidence": 0.9,
        "base_tags": ("native_build",),
    },
    {
        "category": "missing_system_library",
        "patterns": (
            re.compile(r"cannot open shared object file", re.IGNORECASE),
            re.compile(r"image not found", re.IGNORECASE),
            re.compile(r"dll load failed", re.IGNORECASE),
            re.compile(r"library not loaded", re.IGNORECASE),
        ),
        "summary": "A required system library is missing from the host machine.",
        "confidence": 0.9,
        "base_tags": ("system_library",),
    },
    {
        "category": "network_failure",
        "patterns": (
            re.compile(r"could not fetch url", re.IGNORECASE),
            re.compile(r"temporary failure in name resolution", re.IGNORECASE),
            re.compile(r"max retries exceeded", re.IGNORECASE),
            re.compile(r"ssl certificate", re.IGNORECASE),
            re.compile(r"read timed out", re.IGNORECASE),
            re.compile(r"connection timed out", re.IGNORECASE),
            re.compile(r"failed to establish a new connection", re.IGNORECASE),
            re.compile(r"nodename nor servname provided", re.IGNORECASE),
            re.compile(r"name or service not known", re.IGNORECASE),
        ),
        "summary": "Dependency download failed because the package index or network path was unavailable.",
        "confidence": 0.85,
        "base_tags": ("network",),
    },
    {
        "category": "package_conflict",
        "patterns": (
            re.compile(r"conflicting dependencies", re.IGNORECASE),
            re.compile(r"resolutionimpossible", re.IGNORECASE),
            re.compile(r"cannot install .* because these package versions have conflicting dependencies", re.IGNORECASE),
            re.compile(r"could not find a version that satisfies the requirement", re.IGNORECASE),
            re.compile(r"no matching distribution found", re.IGNORECASE),
            re.compile(r"protobuf version conflict", re.IGNORECASE),
            re.compile(r"numpy version conflict", re.IGNORECASE),
            re.compile(r"pydantic v1/v2 conflict", re.IGNORECASE),
        ),
        "summary": "Dependency versions in the requested install set are incompatible.",
        "confidence": 0.8,
        "base_tags": ("resolver",),
    },
)

_PACKAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"requirement ([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"Collecting ([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"Building wheel for ([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"requested ([A-Za-z0-9_.-]+)(?=[<>=!~])", re.IGNORECASE),
    re.compile(r"for ([A-Za-z0-9_.-]+) \(", re.IGNORECASE),
    re.compile(r"([A-Za-z0-9_.-]+)\s+\S+\s+depends on", re.IGNORECASE),
)

_PYTHON_CANDIDATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Python (\d+\.\d+)", re.IGNORECASE),
    re.compile(r"cp(\d)(\d{1,2})\b", re.IGNORECASE),
)


def analyze_install_error(
    output: str | None = None,
    *,
    stdout: str = "",
    stderr: str = "",
) -> ConflictReport:
    combined = _combine_output(output=output, stdout=stdout, stderr=stderr)
    category_spec = _detect_category(combined)
    evidence = _collect_evidence(combined, category_spec)
    report = ConflictReport(
        category=category_spec["category"],
        summary=category_spec["summary"],
        evidence=evidence,
        recommendations=[],
        confidence=category_spec["confidence"],
        recovery_tags=_build_recovery_tags(combined, category_spec),
        related_packages=_extract_related_packages(combined),
        suggested_python_versions=_extract_python_version_hints(combined),
    )
    return report


def analyze_conflict(
    output: str | None = None,
    *,
    stdout: str = "",
    stderr: str = "",
) -> ConflictReport:
    return analyze_install_error(output, stdout=stdout, stderr=stderr)


def render_conflict_report(report: ConflictReport) -> list[str]:
    lines = [
        f"Category: {report.category}",
        f"Summary: {report.summary}",
    ]
    if report.evidence:
        lines.append("Evidence:")
        lines.extend(f"- {line}" for line in report.evidence)
    if report.recommendations:
        lines.append("Recommended next steps:")
        lines.extend(f"- {line}" for line in report.recommendations)
    return lines


def _detect_category(text: str) -> dict[str, object]:
    for spec in _CATEGORY_SPECS:
        patterns = spec["patterns"]
        if _match_evidence(text, patterns):
            return spec
    return {
        "category": "unknown",
        "patterns": (),
        "summary": "The failure output did not match a known installation conflict pattern.",
        "confidence": 0.2,
        "base_tags": ("unknown",),
    }


def _collect_evidence(text: str, category_spec: dict[str, object]) -> list[str]:
    patterns = category_spec["patterns"]
    if patterns:
        evidence = _match_evidence(text, patterns)
        if evidence:
            return evidence
    return _fallback_evidence(text)


def _extract_related_packages(text: str) -> list[str]:
    packages: list[str] = []
    for line in _non_empty_lines(text):
        for pattern in _PACKAGE_PATTERNS:
            match = pattern.search(line)
            if match:
                packages.append(match.group(1))
    return _unique_preserving_order(packages)


def _extract_python_version_hints(text: str) -> list[str]:
    versions: list[str] = []
    lines = _non_empty_lines(text)
    preferred_lines = [
        line
        for line in lines
        if "consider python" in line.lower() or "try python" in line.lower()
    ]
    fallback_lines = [line for line in lines if line not in preferred_lines]

    for line in [*preferred_lines, *fallback_lines]:
        for pattern in _PYTHON_CANDIDATE_PATTERNS:
            for match in pattern.finditer(line):
                version = _normalize_python_version_match(match)
                if version is not None:
                    versions.append(version)
    return _unique_preserving_order(versions)


def _build_recovery_tags(text: str, category_spec: dict[str, object]) -> list[str]:
    tags = list(category_spec["base_tags"])
    lower_text = text.lower()
    category = category_spec["category"]

    if category == "package_conflict":
        if "no matching distribution found" in lower_text:
            tags.append("no_matching_distribution")
        if "supported tags" in lower_text or "platform tags" in lower_text:
            tags.append("platform_mismatch")
        if "conflicting dependencies" in lower_text or "resolutionimpossible" in lower_text:
            tags.append("pinned_versions")
    elif category == "network_failure":
        if (
            "temporary failure in name resolution" in lower_text
            or "failed to establish a new connection" in lower_text
            or "name or service not known" in lower_text
            or "nodename nor servname provided" in lower_text
        ):
            tags.append("dns")
        if "ssl certificate" in lower_text or "certificate_verify_failed" in lower_text:
            tags.append("ssl")
    elif category == "missing_build_tools":
        if "microsoft visual c++" in lower_text:
            tags.append("windows_msvc")
    elif category == "pytorch_cuda_mismatch":
        tags.append("binary_compatibility")

    return _unique_preserving_order(tags)


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


def _normalize_python_version_match(match: re.Match[str]) -> str | None:
    if len(match.groups()) == 1:
        return match.group(1)
    if len(match.groups()) == 2:
        return f"{match.group(1)}.{match.group(2)}"
    return None


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _combine_output(*, output: str | None, stdout: str, stderr: str) -> str:
    if output is not None and not stdout and not stderr:
        return output
    return "\n".join(part for part in (stderr, stdout, output or "") if part)


def _unique_preserving_order(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values

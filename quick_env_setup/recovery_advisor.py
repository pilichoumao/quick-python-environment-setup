from __future__ import annotations

from dataclasses import replace

from quick_env_setup.models import ConflictReport


def build_recovery_guidance(report: ConflictReport) -> ConflictReport:
    recommendations = _recommendations_for_report(report)
    return replace(report, recommendations=recommendations)


def _recommendations_for_report(report: ConflictReport) -> list[str]:
    if report.category == "python_version_incompatible":
        return _python_version_recommendations(report)
    if report.category == "package_conflict":
        return _package_conflict_recommendations(report)
    if report.category == "network_failure":
        return _network_failure_recommendations(report)
    if report.category == "pytorch_cuda_mismatch":
        return _pytorch_cuda_recommendations(report)
    if report.category == "missing_build_tools":
        return _missing_build_tools_recommendations(report)
    if report.category == "missing_system_library":
        return [
            "Install the missing operating-system package that provides the shared library named in the error.",
            "Retry with a prebuilt wheel for the current platform if one is available.",
        ]
    return [
        "Review the captured stdout and stderr for the failing action.",
        "Retry with a narrower install step to isolate the failing dependency or command.",
    ]


def _python_version_recommendations(report: ConflictReport) -> list[str]:
    recommendations = [
        "Create the environment with a Python interpreter that satisfies the package metadata.",
    ]
    if report.suggested_python_versions:
        versions = ", ".join(f"Python {version}" for version in report.suggested_python_versions)
        recommendations.append(f"Retry with one of the compatible candidates seen in the log: {versions}.")
    recommendations.append(
        "Check pyproject.toml, setup.cfg, setup.py, or the package release notes for the exact Requires-Python range."
    )
    return recommendations


def _package_conflict_recommendations(report: ConflictReport) -> list[str]:
    recommendations = [
        "Relax pinned package versions or reduce the install set so pip can resolve a compatible combination.",
    ]
    if "no_matching_distribution" in report.recovery_tags:
        recommendations.append(
            "Confirm that the requested wheel exists for the current interpreter and platform tags before retrying."
        )
    if "platform_mismatch" in report.recovery_tags:
        recommendations.append(
            "Compare the current platform tags against the published wheels and switch to a compatible build if needed."
        )
    if report.suggested_python_versions:
        versions = ", ".join(f"Python {version}" for version in report.suggested_python_versions)
        recommendations.append(f"Retry with a compatible interpreter candidate such as {versions}.")
    if report.related_packages:
        package_list = ", ".join(report.related_packages)
        recommendations.append(f"Inspect the published versions for {package_list} and choose a mutually compatible set.")
    return recommendations


def _network_failure_recommendations(report: ConflictReport) -> list[str]:
    recommendations = ["Retry the install after confirming the package index is reachable from this machine."]
    if "dns" in report.recovery_tags:
        recommendations.append("If DNS lookups are flaky, retry later or configure a package index mirror closer to the host.")
    if "ssl" in report.recovery_tags:
        recommendations.append(
            "Refresh the certificate bundle or trust store, and check whether a proxy or TLS inspection is rewriting certificates."
        )
    if "ssl" not in report.recovery_tags and "dns" not in report.recovery_tags:
        recommendations.append("Configure a trusted package index mirror if the default index is slow or intermittently blocked.")
    return recommendations


def _pytorch_cuda_recommendations(report: ConflictReport) -> list[str]:
    recommendations = [
        "Install matching torch, torchvision, and torchaudio builds for the same CUDA runtime.",
        "If GPU acceleration is not required on this machine, retry with CPU-only wheels.",
    ]
    if report.related_packages:
        package_list = ", ".join(report.related_packages)
        recommendations.append(f"Pin the entire PyTorch stack together instead of mixing binary variants across {package_list}.")
    return recommendations


def _missing_build_tools_recommendations(report: ConflictReport) -> list[str]:
    recommendations: list[str] = []
    if "windows_msvc" in report.recovery_tags:
        recommendations.append("Install Microsoft C++ Build Tools 14.0 or newer, then retry building the wheel.")
    else:
        recommendations.append("Install the missing compiler toolchain for this platform, then retry the build.")
    recommendations.append("Prefer a prebuilt wheel for the current Python version and platform when one is available.")
    if report.related_packages:
        recommendations.append(f"Check whether {report.related_packages[0]} publishes wheels for this interpreter before building from source.")
    return recommendations

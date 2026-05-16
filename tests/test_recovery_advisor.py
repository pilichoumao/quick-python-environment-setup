from __future__ import annotations

from pathlib import Path

import pytest

from quick_env_setup.conflict_analyzer import analyze_install_error
from quick_env_setup.recovery_advisor import build_recovery_guidance


ERROR_LOG_FIXTURES = Path(__file__).parent / "fixtures" / "error_logs"


def _read_error_log(name: str) -> str:
    return (ERROR_LOG_FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("fixture_name", "expected_category", "required_hints", "forbidden_hint"),
    [
        (
            "pinned_resolver_conflict.txt",
            "package_conflict",
            ["Relax pinned package versions", "Inspect the published versions for numpy, demo-lib"],
            "certificate bundle",
        ),
        (
            "python_requires.txt",
            "python_version_incompatible",
            ["Python 3.8", "Python 3.10"],
            "trusted mirror",
        ),
        (
            "no_matching_distribution.txt",
            "package_conflict",
            ["platform tags", "Python 3.10"],
            "DNS",
        ),
        (
            "network_dns_failure.txt",
            "network_failure",
            ["Retry the install", "package index mirror"],
            "Python 3.10",
        ),
        (
            "network_ssl_failure.txt",
            "network_failure",
            ["certificate bundle", "proxy or TLS inspection"],
            "downgrade Python",
        ),
        (
            "pytorch_cuda_mismatch.txt",
            "pytorch_cuda_mismatch",
            ["matching torch, torchvision, and torchaudio", "CPU-only wheels"],
            "trusted mirror",
        ),
        (
            "missing_build_tools_windows.txt",
            "missing_build_tools",
            ["Microsoft C++ Build Tools", "prebuilt wheel"],
            "downgrade Python",
        ),
    ],
)
def test_build_recovery_guidance_adds_scenario_specific_recommendations(
    fixture_name: str,
    expected_category: str,
    required_hints: list[str],
    forbidden_hint: str,
) -> None:
    report = analyze_install_error(stderr=_read_error_log(fixture_name))

    enriched = build_recovery_guidance(report)

    assert enriched.category == expected_category
    joined_recommendations = "\n".join(enriched.recommendations)
    for hint in required_hints:
        assert hint in joined_recommendations
    assert forbidden_hint not in joined_recommendations

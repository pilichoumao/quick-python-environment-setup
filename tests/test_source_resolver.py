from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from quick_env_setup.models import SourceSpec
from quick_env_setup.git_handler import (
    detect_clone_conflict,
    select_clone_target_path,
)
from quick_env_setup.source_resolver import parse_source_spec
from quick_env_setup.system_detector import (
    detect_architecture,
    detect_apple_silicon,
    detect_conda_presence,
    detect_git_presence,
    map_os_name,
)


def test_parse_source_spec_accepts_github_https_url() -> None:
    spec = parse_source_spec("https://github.com/example/project.git")

    assert spec == SourceSpec(
        raw="https://github.com/example/project.git",
        source_type="git_url",
        normalized="https://github.com/example/project.git",
    )


def test_parse_source_spec_accepts_gitlab_ssh_url() -> None:
    spec = parse_source_spec("git@gitlab.com:team/project.git")

    assert spec.source_type == "git_url"
    assert spec.normalized == "git@gitlab.com:team/project.git"


def test_parse_source_spec_normalizes_local_posix_path() -> None:
    spec = parse_source_spec("./example-project")

    assert spec.source_type == "local_path"
    assert spec.normalized == str(Path("./example-project").expanduser().resolve())


def test_parse_source_spec_preserves_windows_like_path_string() -> None:
    raw = r"C:\Users\dev\project"

    spec = parse_source_spec(raw)

    assert spec.source_type == "local_path"
    assert spec.normalized == str(PureWindowsPath(raw))


def test_parse_source_spec_rejects_unsupported_source() -> None:
    with pytest.raises(ValueError, match="Unsupported source"):
        parse_source_spec("ftp://example.com/project.tar.gz")


@pytest.mark.parametrize(
    "raw",
    [
        "git@bitbucket.org:org/repo.git",
        "ssh://git@example.com/org/repo.git",
        "github.com/org/repo",
    ],
)
def test_parse_source_spec_rejects_unsupported_remote_like_inputs(raw: str) -> None:
    with pytest.raises(ValueError, match="Unsupported source"):
        parse_source_spec(raw)


@pytest.mark.parametrize(
    ("raw_system", "expected"),
    [
        ("Darwin", "macos"),
        ("Linux", "linux"),
        ("Windows", "windows"),
    ],
)
def test_map_os_name_supports_expected_platform_names(
    raw_system: str,
    expected: str,
) -> None:
    assert map_os_name(raw_system) == expected


@pytest.mark.parametrize(
    ("raw_arch", "expected"),
    [
        ("AMD64", "x86_64"),
        ("x86_64", "x86_64"),
        ("arm64", "arm64"),
        ("aarch64", "arm64"),
    ],
)
def test_detect_architecture_normalizes_common_aliases(
    raw_arch: str,
    expected: str,
) -> None:
    assert detect_architecture(raw_arch) == expected


@pytest.mark.parametrize(
    ("os_name", "arch", "expected"),
    [
        ("macos", "arm64", True),
        ("macos", "x86_64", False),
        ("linux", "arm64", False),
    ],
)
def test_detect_apple_silicon_requires_macos_arm64(
    os_name: str,
    arch: str,
    expected: bool,
) -> None:
    assert detect_apple_silicon(os_name, arch) is expected


def test_detect_git_presence_uses_which_style_probe() -> None:
    assert detect_git_presence(which=lambda name: f"/usr/bin/{name}") is True
    assert detect_git_presence(which=lambda name: None) is False


def test_detect_conda_presence_uses_which_style_probe() -> None:
    assert detect_conda_presence(which=lambda name: f"/opt/bin/{name}") is True
    assert detect_conda_presence(which=lambda name: None) is False


def test_select_clone_target_path_uses_repo_name_without_git_suffix() -> None:
    source = SourceSpec(
        raw="https://github.com/example/project.git",
        source_type="git_url",
        normalized="https://github.com/example/project.git",
    )

    target = select_clone_target_path(source, Path("/tmp/workspace"))

    assert target == Path("/tmp/workspace/project")


def test_detect_clone_conflict_is_none_for_missing_target(tmp_path: Path) -> None:
    assert detect_clone_conflict(tmp_path / "project") is None


def test_detect_clone_conflict_flags_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "project"
    target.mkdir()

    assert detect_clone_conflict(target) == str(target)

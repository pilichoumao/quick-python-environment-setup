from __future__ import annotations

from pathlib import Path

import pytest

from quick_env_setup.conda_manager import (
    build_conda_create_command,
    build_conda_pip_install_command,
)
from quick_env_setup.env_manager import EnvironmentTarget, get_env_manager
from quick_env_setup.mirror_manager import (
    conda_channels_for_mirror,
    get_mirror_config,
    pip_args_for_mirror,
)
from quick_env_setup.venv_manager import (
    build_venv_create_command,
    compose_venv_python_path,
)


def test_get_env_manager_returns_conda_builder() -> None:
    manager = get_env_manager("conda")

    assert manager.manager_name == "conda"
    assert manager.build_create_command(
        EnvironmentTarget.for_conda("demo-env"),
        "3.10",
    ) == [
        "conda",
        "create",
        "-n",
        "demo-env",
        "python=3.10",
        "-y",
    ]


def test_get_env_manager_returns_venv_builder() -> None:
    manager = get_env_manager("venv")

    assert manager.manager_name == "venv"
    assert manager.build_create_command(
        EnvironmentTarget.for_venv(Path(".venv")),
        "3.11",
    ) == ["python3.11", "-m", "venv", ".venv"]


def test_environment_target_requires_exactly_one_locator() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        EnvironmentTarget()


def test_environment_target_rejects_both_env_name_and_env_path() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        EnvironmentTarget(env_name="demo-env", env_path=Path(".venv"))


def test_build_conda_pip_install_command_uses_conda_run_and_requirements_file() -> None:
    command = build_conda_pip_install_command(
        env_name="demo-env",
        requirements_file=Path("requirements.txt"),
    )

    assert command == [
        "conda",
        "run",
        "-n",
        "demo-env",
        "python",
        "-m",
        "pip",
        "install",
        "-r",
        "requirements.txt",
    ]


def test_build_venv_create_command_uses_requested_python_launcher() -> None:
    command = build_venv_create_command(
        env_path=Path(".venv"),
        python_executable="python3.11",
    )

    assert command == ["python3.11", "-m", "venv", ".venv"]


def test_compose_venv_python_path_supports_posix_and_windows() -> None:
    assert compose_venv_python_path(Path(".venv"), os_name="linux") == Path(
        ".venv/bin/python"
    )
    assert compose_venv_python_path(Path(".venv"), os_name="windows") == Path(
        ".venv/Scripts/python.exe"
    )


def test_venv_manager_builds_windows_local_pip_install_command() -> None:
    manager = get_env_manager("venv")

    command = manager.build_pip_install_command(
        EnvironmentTarget.for_venv(Path(".venv")),
        requirements_file=Path("requirements.txt"),
        os_name="windows",
    )

    assert command == [
        ".venv/Scripts/python.exe",
        "-m",
        "pip",
        "install",
        "-r",
        "requirements.txt",
    ]


def test_command_scoped_pip_mirror_configuration_uses_provider_specific_index_url() -> None:
    mirror_config = get_mirror_config("tuna")

    assert mirror_config.pip_index_url == (
        "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    )
    assert conda_channels_for_mirror(mirror_config) == [
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main",
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free",
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    ]
    assert pip_args_for_mirror(mirror_config) == [
        "-i",
        "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
    ]


def test_aliyun_mirror_supports_pip_but_not_conda_channels() -> None:
    mirror_config = get_mirror_config("aliyun")

    assert mirror_config.enabled is True
    assert pip_args_for_mirror(mirror_config) == [
        "-i",
        "https://mirrors.aliyun.com/pypi/simple/",
    ]
    assert conda_channels_for_mirror(mirror_config) == []

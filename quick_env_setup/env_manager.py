from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from quick_env_setup.conda_manager import (
    build_conda_create_command,
    build_conda_pip_install_command,
)
from quick_env_setup.models import EnvManager as EnvManagerName, MirrorConfig, OsName
from quick_env_setup.venv_manager import (
    build_venv_create_command,
    build_venv_pip_install_command,
)


@dataclass(frozen=True, slots=True)
class EnvironmentTarget:
    env_name: str | None = None
    env_path: Path | None = None

    def __post_init__(self) -> None:
        has_env_name = self.env_name is not None
        has_env_path = self.env_path is not None
        if has_env_name == has_env_path:
            raise ValueError(
                "Environment target must define exactly one of env_name or env_path"
            )

    @classmethod
    def for_conda(cls, env_name: str) -> EnvironmentTarget:
        return cls(env_name=env_name)

    @classmethod
    def for_venv(cls, env_path: Path) -> EnvironmentTarget:
        return cls(env_path=env_path)

    def require_env_name(self) -> str:
        if self.env_name is None:
            raise ValueError("Environment target requires a conda environment name")
        return self.env_name

    def require_env_path(self) -> Path:
        if self.env_path is None:
            raise ValueError("Environment target requires a venv filesystem path")
        return self.env_path


class EnvironmentManager(Protocol):
    manager_name: EnvManagerName

    def build_create_command(
        self,
        target: EnvironmentTarget,
        python_version: str,
    ) -> list[str]:
        ...

    def build_pip_install_command(
        self,
        target: EnvironmentTarget,
        requirements_file: Path,
        mirror_config: MirrorConfig | None = None,
        os_name: OsName = "linux",
    ) -> list[str]:
        ...


class CondaEnvironmentManager:
    manager_name: EnvManagerName = "conda"

    def build_create_command(
        self,
        target: EnvironmentTarget,
        python_version: str,
    ) -> list[str]:
        return build_conda_create_command(
            env_name=target.require_env_name(),
            python_version=python_version,
        )

    def build_pip_install_command(
        self,
        target: EnvironmentTarget,
        requirements_file: Path,
        mirror_config: MirrorConfig | None = None,
        os_name: OsName = "linux",
    ) -> list[str]:
        del os_name
        return build_conda_pip_install_command(
            env_name=target.require_env_name(),
            requirements_file=requirements_file,
            mirror_config=mirror_config,
        )


class VenvEnvironmentManager:
    manager_name: EnvManagerName = "venv"

    def build_create_command(
        self,
        target: EnvironmentTarget,
        python_version: str,
    ) -> list[str]:
        return build_venv_create_command(
            env_path=target.require_env_path(),
            python_executable=f"python{python_version}",
        )

    def build_pip_install_command(
        self,
        target: EnvironmentTarget,
        requirements_file: Path,
        mirror_config: MirrorConfig | None = None,
        os_name: OsName = "linux",
    ) -> list[str]:
        return build_venv_pip_install_command(
            env_path=target.require_env_path(),
            requirements_file=requirements_file,
            os_name=os_name,
            mirror_config=mirror_config,
        )


_ENV_MANAGERS: dict[EnvManagerName, EnvironmentManager] = {
    "conda": CondaEnvironmentManager(),
    "venv": VenvEnvironmentManager(),
}


def get_env_manager(manager_name: EnvManagerName) -> EnvironmentManager:
    try:
        return _ENV_MANAGERS[manager_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported environment manager: {manager_name}") from exc

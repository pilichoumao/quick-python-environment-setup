from __future__ import annotations

from quick_env_setup.models import MirrorConfig, MirrorProvider


_MIRROR_CONFIG_BY_PROVIDER: dict[MirrorProvider, MirrorConfig] = {
    "none": MirrorConfig(
        enabled=False,
        provider="none",
        pip_index_url=None,
        conda_channels=[],
    ),
    "tuna": MirrorConfig(
        enabled=True,
        provider="tuna",
        pip_index_url="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
        conda_channels=[
            "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main",
            "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free",
            "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
        ],
    ),
    "ustc": MirrorConfig(
        enabled=True,
        provider="ustc",
        pip_index_url="https://mirrors.ustc.edu.cn/pypi/simple",
        conda_channels=[
            "https://mirrors.ustc.edu.cn/anaconda/pkgs/main",
            "https://mirrors.ustc.edu.cn/anaconda/pkgs/free",
            "https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge",
        ],
    ),
    "aliyun": MirrorConfig(
        enabled=True,
        provider="aliyun",
        pip_index_url="https://mirrors.aliyun.com/pypi/simple/",
        conda_channels=[],
    ),
}


def get_mirror_config(provider: MirrorProvider | None) -> MirrorConfig:
    normalized_provider: MirrorProvider = provider or "none"
    try:
        base_config = _MIRROR_CONFIG_BY_PROVIDER[normalized_provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported mirror provider: {provider}") from exc
    return MirrorConfig(
        enabled=base_config.enabled,
        provider=base_config.provider,
        pip_index_url=base_config.pip_index_url,
        conda_channels=list(base_config.conda_channels),
    )


def pip_args_for_mirror(mirror_config: MirrorConfig | None) -> list[str]:
    if mirror_config is None or not mirror_config.enabled:
        return []
    if not mirror_config.pip_index_url:
        return []
    return ["-i", mirror_config.pip_index_url]


def conda_channels_for_mirror(mirror_config: MirrorConfig | None) -> list[str]:
    if mirror_config is None:
        return []
    return list(mirror_config.conda_channels)

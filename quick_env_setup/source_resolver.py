from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

from quick_env_setup.models import SourceSpec


_HTTPS_GIT_HOST_PATTERN = re.compile(
    r"^https://(?:github\.com|gitlab\.com)/[^/\s]+/[^/\s]+(?:\.git)?/?$",
    re.IGNORECASE,
)
_SSH_GIT_HOST_PATTERN = re.compile(
    r"^(?:git@)(?:github\.com|gitlab\.com):[^/\s]+/[^/\s]+(?:\.git)?$",
    re.IGNORECASE,
)
_SCPLIKE_REMOTE_PATTERN = re.compile(r"^[^/\s@]+@[^:\s]+:[^/\s]+/[^/\s]+(?:\.git)?$")
_WINDOWS_PATH_PATTERN = re.compile(
    r"^(?:[a-zA-Z]:[\\/]|\\\\[^\\\/]+[\\\/][^\\\/]+)"
)
_URL_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_REMOTE_HOST_SHORTHAND_PATTERN = re.compile(
    r"^(?:github|gitlab|bitbucket)\.com/[^/\s]+/[^/\s]+(?:\.git)?/?$",
    re.IGNORECASE,
)


def is_supported_git_url(value: str) -> bool:
    return bool(
        _HTTPS_GIT_HOST_PATTERN.match(value) or _SSH_GIT_HOST_PATTERN.match(value)
    )


def is_windows_like_path(value: str) -> bool:
    return bool(_WINDOWS_PATH_PATTERN.match(value))


def looks_like_unsupported_remote(value: str) -> bool:
    if _URL_SCHEME_PATTERN.match(value):
        return not is_supported_git_url(value)
    return bool(
        _SCPLIKE_REMOTE_PATTERN.match(value)
        or _REMOTE_HOST_SHORTHAND_PATTERN.match(value)
    )


def normalize_local_path(value: str) -> str:
    if is_windows_like_path(value):
        return str(PureWindowsPath(value))
    return str(Path(value).expanduser().resolve())


def parse_source_spec(raw: str) -> SourceSpec:
    candidate = raw.strip()
    if not candidate:
        raise ValueError("Unsupported source: empty input")

    if is_supported_git_url(candidate):
        return SourceSpec(raw=raw, source_type="git_url", normalized=candidate)

    if looks_like_unsupported_remote(candidate):
        raise ValueError(f"Unsupported source: {raw}")

    return SourceSpec(
        raw=raw,
        source_type="local_path",
        normalized=normalize_local_path(candidate),
    )

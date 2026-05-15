from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from quick_env_setup.models import ProjectScanResult


@dataclass(slots=True)
class MissingAsset:
    category: str
    asset_path: str
    evidence: list[str]
    download_hints: list[str]


ASSET_PATTERNS: tuple[tuple[str, str], ...] = (
    ("weights", r"(?<![\w:\\-])(?P<path>[\w./-]+\.(?:pt|pth|ckpt|bin|safetensors|onnx))"),
    ("config", r"(?<![\w:\\-])(?P<path>[\w./-]+\.(?:ya?ml|json|ini|toml))"),
    ("data", r"(?<![\w:\\-])(?P<path>[\w./-]+\.(?:csv|tsv|jsonl|parquet|npy|npz|txt))"),
    ("env", r"(?<![\w:\\-])(?P<path>\.env(?:\.[\w.-]+)?)"),
)
HINT_MARKERS = (
    "download",
    "wget",
    "curl",
    "drive.google",
    "huggingface.co",
    "http://",
    "https://",
    "create ",
    "place ",
    "set ",
    "configure ",
)
SCAN_SUFFIXES = {".py", ".json", ".yaml", ".yml", ".toml", ".ini"}


def detect_missing_assets(project_scan: ProjectScanResult) -> list[MissingAsset]:
    project_root = project_scan.root
    readme_lines = _read_lines(project_scan.readme_path)
    findings: dict[tuple[str, str], MissingAsset] = {}

    for path in project_scan.detected_files:
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        for raw_line in _read_lines(path):
            for category, asset_path in _extract_asset_references(raw_line):
                normalized = _normalize_asset_path(asset_path)
                if not normalized or _asset_exists(project_root, path, normalized):
                    continue
                key = (category, normalized)
                finding = findings.get(key)
                if finding is None:
                    finding = MissingAsset(
                        category=category,
                        asset_path=normalized,
                        evidence=[],
                        download_hints=[],
                    )
                    findings[key] = finding
                if raw_line not in finding.evidence:
                    finding.evidence.append(raw_line)

    for finding in findings.values():
        for line in readme_lines:
            lowered = line.lower()
            if not any(marker in lowered for marker in HINT_MARKERS):
                continue
            if (
                finding.asset_path.lower() in lowered
                or finding.category == "env" and ".env" in lowered
                or finding.category == "weights" and "weight" in lowered
                or finding.category == "data" and "data" in lowered
            ):
                if line not in finding.download_hints:
                    finding.download_hints.append(line)

    return sorted(findings.values(), key=lambda item: (item.category, item.asset_path))


def _extract_asset_references(line: str) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for category, pattern in ASSET_PATTERNS:
        for match in re.finditer(pattern, line, re.IGNORECASE):
            candidate = match.group("path").strip("\"'`()[]{} ,")
            if not candidate:
                continue
            references.append((category, candidate))
    return references


def _normalize_asset_path(candidate: str) -> str:
    normalized = candidate.strip().replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("http://")
        or normalized.startswith("https://")
        or normalized.startswith("//")
        or "://" in normalized
    ):
        return ""
    if normalized.startswith("../") or normalized.startswith("/"):
        return ""
    return normalized


def _asset_exists(project_root: Path, source_path: Path, relative_path: str) -> bool:
    if (project_root / relative_path).exists():
        return True
    return (source_path.parent / relative_path).exists()


def _read_lines(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]

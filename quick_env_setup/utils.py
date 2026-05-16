from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quick_env_setup.models import InstallPlan


@dataclass(slots=True)
class InstallWorkflowResult:
    plan: InstallPlan
    execution_succeeded: bool
    validation_passed: bool
    artifact_dir: Path
    artifact_paths: dict[str, Path]
    completed_action_ids: list[str]
    failed_action_id: str | None
    run_candidates: list[str]
    missing_assets: list[str]
    warnings: list[str]

    @property
    def succeeded(self) -> bool:
        return self.execution_succeeded and self.validation_passed


def render_execution_summary(result: InstallWorkflowResult) -> str:
    lines = [
        "Execution summary",
        f"  execution: {'passed' if result.execution_succeeded else 'failed'}",
        f"  validation: {'passed' if result.validation_passed else 'failed'}",
        f"  completed actions: {len(result.completed_action_ids)}",
    ]

    if result.failed_action_id is not None:
        lines.append(f"  failed action: {result.failed_action_id}")

    lines.append(f"  artifact dir: {result.artifact_dir}")
    lines.append("  artifact paths:")
    for name, path in sorted(result.artifact_paths.items()):
        lines.append(f"    - {name}: {path}")

    if result.run_candidates:
        lines.append("  run candidates:")
        lines.extend(f"    - {candidate}" for candidate in result.run_candidates)

    if result.missing_assets:
        lines.append("  missing assets:")
        lines.extend(f"    - {asset}" for asset in result.missing_assets)

    if result.warnings:
        lines.append("  warnings:")
        lines.extend(f"    - {warning}" for warning in result.warnings)

    return "\n".join(lines)

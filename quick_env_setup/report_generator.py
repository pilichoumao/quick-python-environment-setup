from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quick_env_setup.logger import artifact_path, ensure_log_dir
from quick_env_setup.models import FinalReport, InstallPlan, ValidationReport, dataclass_to_dict


def generate_final_report(
    *,
    base_dir: Path,
    plan: InstallPlan,
    validation: ValidationReport,
    run_candidates: list[str],
    missing_assets: list[str],
    error_summary_lines: list[str] | None = None,
    agent_trace_lines: list[str] | None = None,
) -> FinalReport:
    ensure_log_dir(base_dir)

    overview = _build_overview(plan, validation)
    next_steps = _build_next_steps(validation, missing_assets, run_candidates)
    merged_warnings = _merge_warnings(plan.warnings, validation.warnings)
    report = FinalReport(
        overview=overview,
        validation=validation,
        run_candidates=run_candidates,
        missing_assets=missing_assets,
        warnings=merged_warnings,
        next_steps=next_steps,
    )

    _write_json(
        artifact_path(base_dir, "detected_config.json"),
        _build_detected_config(plan, validation, run_candidates, missing_assets),
    )
    _write_json(artifact_path(base_dir, "install_plan.json"), plan.to_dict())
    _write_lines(artifact_path(base_dir, "error_summary.txt"), error_summary_lines or validation.failures)
    _write_lines(artifact_path(base_dir, "run_candidates.txt"), run_candidates)
    _write_lines(artifact_path(base_dir, "missing_assets.txt"), missing_assets)
    _write_lines(
        artifact_path(base_dir, "agent_trace_summary.txt"),
        agent_trace_lines or [],
    )
    artifact_path(base_dir, "final_report.txt").write_text(
        _render_final_report(report),
        encoding="utf-8",
    )
    return report


def _build_detected_config(
    plan: InstallPlan,
    validation: ValidationReport,
    run_candidates: list[str],
    missing_assets: list[str],
) -> dict[str, Any]:
    return {
        "source_type": plan.source_result.source.source_type,
        "source": plan.source_result.source.normalized,
        "local_project_path": str(plan.source_result.local_project_path),
        "os": plan.system_info.os_name,
        "arch": plan.system_info.arch,
        "project_type": plan.project_profile.project_type,
        "env_manager": plan.env_manager,
        "env_name": plan.env_name,
        "python_version": plan.python_requirement.version,
        "has_nvidia_gpu": plan.device_info.accelerator_type == "nvidia",
        "device_strategy": plan.device_info.accelerator_type,
        "needs_pytorch": plan.pytorch_strategy.required,
        "pytorch_install_type": plan.pytorch_strategy.variant,
        "use_china_mirror": plan.mirror_config.enabled,
        "mirror": plan.mirror_config.provider,
        "safety_level": plan.safety_level,
        "validation_status": "passed" if validation.passed else "failed",
        "run_candidate_count": len(run_candidates),
        "run_candidates": list(run_candidates),
        "missing_asset_count": len(missing_assets),
        "missing_assets": list(missing_assets),
    }


def _build_overview(plan: InstallPlan, validation: ValidationReport) -> dict[str, Any]:
    status = "ready" if validation.passed else "attention_needed"
    return {
        "status": status,
        "source": plan.source_result.source.normalized,
        "project_root": str(plan.source_result.local_project_path),
        "project_type": plan.project_profile.project_type,
        "env_manager": plan.env_manager,
        "env_name": plan.env_name,
        "python_version": plan.python_requirement.version,
        "device_strategy": plan.device_info.accelerator_type,
        "pytorch_variant": plan.pytorch_strategy.variant,
        "validation_status": "passed" if validation.passed else "failed",
        "os": plan.system_info.os_name,
        "action_count": len(plan.actions),
    }


def _build_next_steps(
    validation: ValidationReport,
    missing_assets: list[str],
    run_candidates: list[str],
) -> list[str]:
    steps: list[str] = []
    if missing_assets:
        steps.append("Resolve missing assets before executing project entrypoints.")
    if validation.failures:
        steps.append("Review error_summary.txt and address the reported failures.")
    if run_candidates:
        steps.append("Try one of the discovered run candidates after environment setup completes.")
    return steps


def _render_final_report(report: FinalReport) -> str:
    lines = [
        f"Status: {report.overview['status']}",
        f"Source: {report.overview['source']}",
        f"Local path: {report.overview['project_root']}",
        f"Project type: {report.overview['project_type']}",
        f"Environment manager: {report.overview['env_manager']}",
        f"Environment: {report.overview['env_name']}",
        f"Python version: {report.overview['python_version']}",
        f"Device strategy: {report.overview['device_strategy']}",
        f"PyTorch: {report.overview['pytorch_variant']}",
        f"Validation: {report.overview['validation_status']}",
        "",
        "Run candidates:",
    ]
    lines.extend(_section_lines(report.run_candidates))
    lines.append("")
    lines.append("Missing assets:")
    lines.extend(_section_lines(report.missing_assets))
    lines.append("")
    lines.append("Warnings:")
    lines.extend(_section_lines(report.warnings))
    lines.append("")
    lines.append("Next steps:")
    lines.extend(_section_lines(report.next_steps))
    activation_lines = _activation_lines(report)
    if activation_lines:
        lines.append("")
        lines.append("Activate and run:")
        lines.extend(activation_lines)
    return "\n".join(lines) + "\n"


def _section_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(dataclass_to_dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _merge_warnings(*warning_groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in warning_groups:
        for warning in group:
            if warning in seen:
                continue
            seen.add(warning)
            merged.append(warning)
    return merged


def _activation_lines(report: FinalReport) -> list[str]:
    env_manager = report.overview["env_manager"]
    if env_manager == "conda":
        lines = [f"- conda activate {report.overview['env_name']}"]
        if report.run_candidates:
            lines.append(f"- {report.run_candidates[0]}")
        return lines

    project_root = Path(report.overview["project_root"])
    os_name = report.overview["os"]
    if os_name == "windows":
        lines = [f"- {project_root / '.venv' / 'Scripts' / 'activate'}"]
        if report.run_candidates:
            lines.append(f"- {report.run_candidates[0]}")
        return lines

    lines = ["- source .venv/bin/activate"]
    if report.run_candidates:
        lines.append(f"- {report.run_candidates[0]}")
    return lines

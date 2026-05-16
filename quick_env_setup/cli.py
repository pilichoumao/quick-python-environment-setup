from __future__ import annotations

import argparse
from typing import Sequence

from quick_env_setup.interactive_prompt import confirm_low_risk_execution
from quick_env_setup.orchestrator import build_install_plan, execute_install_plan
from quick_env_setup.utils import render_execution_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quick-env-setup",
        description="Analyze a Python project and plan a safe environment setup.",
    )
    parser.add_argument("--source", required=True, help="Local project path or supported git URL.")
    parser.add_argument(
        "--env-manager",
        choices=("conda", "venv"),
        help="Override the recommended environment manager.",
    )
    parser.add_argument("--env-name", help="Override the planned environment name.")
    parser.add_argument("--python", dest="python_version", help="Override the planned Python version.")
    parser.add_argument("--clone-dir", help="Directory to use for planned git clones.")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU-only planning.")
    parser.add_argument(
        "--use-china-mirror",
        action="store_true",
        help="Enable the selected China mirror for pip/conda planning.",
    )
    parser.add_argument(
        "--mirror",
        choices=("tuna", "ustc", "aliyun"),
        help="Mirror provider to use when --use-china-mirror is enabled.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Render the install plan without executing it.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the execution confirmation prompt.",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=2,
        choices=(1, 2, 3),
        help="Safety level: 1=analyze only, 2=install plan, 3=allow high-risk execution planning.",
    )
    parser.add_argument(
        "--run-demo",
        action="store_true",
        help="Request demo execution planning (requires --level 3).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    plan = build_install_plan(
        source=args.source,
        env_manager=args.env_manager,
        env_name=args.env_name,
        python_version=args.python_version,
        clone_dir=args.clone_dir,
        cpu_only=args.cpu_only,
        use_china_mirror=args.use_china_mirror,
        mirror=args.mirror,
        safety_level=args.level,
        run_demo=args.run_demo,
    )

    print(render_plan_summary(plan))
    if args.dry_run:
        return 0

    if not confirm_low_risk_execution(injected_response=True if args.yes else None):
        print("Execution cancelled before making environment changes.")
        return 1

    workflow_result = execute_install_plan(plan)
    if not workflow_result.succeeded:
        print(render_failure_summary(workflow_result))
    print(render_execution_summary(workflow_result))
    return 0 if workflow_result.succeeded else 1


def render_plan_summary(plan: object) -> str:
    from quick_env_setup.models import InstallPlan

    if not isinstance(plan, InstallPlan):
        raise TypeError("render_plan_summary expects an InstallPlan")

    lines = [
        "Plan summary",
        f"  source: {plan.source_result.local_project_path}",
        f"  project type: {plan.project_profile.project_type}",
        f"  env manager: {plan.env_manager}",
        f"  env name: {plan.env_name}",
        f"  python: {plan.python_requirement.version}",
        f"  safety level: {plan.safety_level}",
        f"  mirror: {plan.mirror_config.provider}",
        "  actions:",
    ]
    for action in plan.actions:
        command = " ".join(action.command) if action.command else "(plan-only)"
        lines.append(
            f"    - {action.action_id} [{action.risk_level}] {action.description} :: {command}"
        )

    if plan.warnings:
        lines.append("  warnings:")
        lines.extend(f"    - {warning}" for warning in plan.warnings)

    if plan.assumptions:
        lines.append("  assumptions:")
        lines.extend(f"    - {assumption}" for assumption in plan.assumptions)

    return "\n".join(lines)


def render_failure_summary(workflow_result: object) -> str:
    from quick_env_setup.utils import InstallWorkflowResult

    if not isinstance(workflow_result, InstallWorkflowResult):
        raise TypeError("render_failure_summary expects an InstallWorkflowResult")

    category = ""
    summary = ""
    error_summary_path = workflow_result.artifact_paths.get("error_summary.txt")
    if error_summary_path is not None and error_summary_path.exists():
        for line in error_summary_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Category: "):
                category = line.removeprefix("Category: ").strip()
            elif line.startswith("Summary: "):
                summary = line.removeprefix("Summary: ").strip()
            if category and summary:
                break

    lines = ["Failure summary"]
    if workflow_result.failed_action_id is not None:
        lines.append(f"  failed action: {workflow_result.failed_action_id}")
    if category:
        lines.append(f"  category: {category}")
    if summary:
        lines.append(f"  summary: {summary}")
    if error_summary_path is not None:
        lines.append(f"  error summary: {error_summary_path}")
    lines.append(f"  artifact dir: {workflow_result.artifact_dir}")
    return "\n".join(lines)

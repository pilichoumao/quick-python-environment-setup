from __future__ import annotations

import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from quick_env_setup.logger import append_command_log_line, artifact_path
from quick_env_setup.models import ExecutionResult, InstallAction, InstallPlan


COMMAND_LOG_FILENAME = "commands.log"
_TAIL_LIMIT = 4000


def execute_install_plan(plan: InstallPlan) -> ExecutionResult:
    log_path = artifact_path(_resolve_log_base_dir(plan), COMMAND_LOG_FILENAME)
    completed_action_ids: list[str] = []
    last_stdout = ""
    last_stderr = ""

    for action in plan.actions:
        if not action.command:
            completed_action_ids.append(action.action_id)
            continue

        append_command_log_line(log_path, _format_action_start_line(action))

        try:
            completed = subprocess.run(
                action.command,
                cwd=_resolve_cwd(action),
                env=_build_env(action),
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as exc:
            _append_action_result(
                log_path,
                action=action,
                exit_code=None,
                stdout="",
                stderr=str(exc),
            )
            return ExecutionResult(
                success=False,
                completed_action_ids=completed_action_ids,
                failed_action_id=action.action_id,
                exit_code=None,
                log_path=log_path,
                stdout_tail="",
                stderr_tail=_tail(str(exc)),
            )

        last_stdout = completed.stdout
        last_stderr = completed.stderr
        _append_action_result(
            log_path,
            action=action,
            exit_code=completed.returncode,
            stdout=last_stdout,
            stderr=last_stderr,
        )
        if completed.returncode != 0:
            return ExecutionResult(
                success=False,
                completed_action_ids=completed_action_ids,
                failed_action_id=action.action_id,
                exit_code=completed.returncode,
                log_path=log_path,
                stdout_tail=_tail(last_stdout),
                stderr_tail=_tail(last_stderr),
            )

        completed_action_ids.append(action.action_id)

    return ExecutionResult(
        success=True,
        completed_action_ids=completed_action_ids,
        failed_action_id=None,
        exit_code=0,
        log_path=log_path,
        stdout_tail=_tail(last_stdout),
        stderr_tail=_tail(last_stderr),
    )


def _resolve_cwd(action: InstallAction) -> str | None:
    if action.cwd is None:
        return None
    return str(Path(action.cwd))


def _build_env(action: InstallAction) -> dict[str, str]:
    env = os.environ.copy()
    env.update(action.env_overrides)
    return env


def _resolve_log_base_dir(plan: InstallPlan) -> Path:
    project_root = plan.source_result.local_project_path
    if plan.source_result.source.source_type != "git_url" or project_root.exists():
        return project_root

    for action in plan.actions:
        if action.cwd is not None:
            return Path(action.cwd)
    return project_root.parent


def _format_action_start_line(action: InstallAction) -> str:
    parts = [
        f"action_id={action.action_id}",
        f"kind={action.kind}",
        f"command={_format_command(action.command or [])}",
    ]
    if action.cwd is not None:
        parts.append(f"cwd={Path(action.cwd)}")
    return " ".join(parts)


def _append_action_result(
    log_path: Path,
    *,
    action: InstallAction,
    exit_code: int | None,
    stdout: str,
    stderr: str,
) -> None:
    lines = [
        f"timestamp={datetime.now(timezone.utc).isoformat()}",
        f"action_id={action.action_id}",
        f"exit_code={exit_code if exit_code is not None else 'oserror'}",
    ]
    if action.cwd is not None:
        lines.append(f"cwd={Path(action.cwd)}")
    lines.extend(
        [
            "stdout_tail:",
            _tail(stdout) or "<empty>",
            "stderr_tail:",
            _tail(stderr) or "<empty>",
            "",
        ]
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _format_command(command: list[str]) -> str:
    return shlex.join(command)


def _tail(text: str) -> str:
    if len(text) <= _TAIL_LIMIT:
        return text
    return text[-_TAIL_LIMIT:]

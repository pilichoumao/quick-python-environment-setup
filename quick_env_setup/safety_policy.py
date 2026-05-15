from __future__ import annotations

from quick_env_setup.models import InstallAction, InstallActionKind, RiskLevel


ALLOWED_SAFETY_LEVELS = {1, 2, 3}

_ACTION_POLICY_BY_KIND: dict[InstallActionKind, tuple[int, RiskLevel]] = {
    "check": (1, "low"),
    "clone": (2, "medium"),
    "create_env": (2, "medium"),
    "upgrade_packaging_tools": (2, "medium"),
    "install_pytorch": (2, "medium"),
    "install_dependencies": (2, "medium"),
    "editable_install": (2, "medium"),
    "validate": (2, "high"),
    "discover": (1, "low"),
    "report": (1, "low"),
}


def validate_safety_level(level: int) -> int:
    if level not in ALLOWED_SAFETY_LEVELS:
        raise ValueError(f"Unsupported safety level: {level}")
    return level


def minimum_safety_level_for_action_kind(action_kind: InstallActionKind) -> int:
    return _ACTION_POLICY_BY_KIND.get(action_kind, (3, "high"))[0]


def risk_level_for_action_kind(action_kind: InstallActionKind) -> RiskLevel:
    return _ACTION_POLICY_BY_KIND.get(action_kind, (3, "high"))[1]


def validate_requested_operations(
    *,
    safety_level: int,
    run_demo: bool = False,
) -> None:
    validate_safety_level(safety_level)
    if run_demo and safety_level < 3:
        raise ValueError("run_demo requires safety level 3")
    if run_demo:
        raise NotImplementedError("run_demo planning is not supported yet")


def apply_safety_policy(
    actions: list[InstallAction],
    *,
    safety_level: int,
    allow_high_risk: bool = False,
) -> tuple[list[InstallAction], list[str]]:
    validate_safety_level(safety_level)

    allowed_actions: list[InstallAction] = []
    warnings: list[str] = []

    for action in actions:
        minimum_level = minimum_safety_level_for_action_kind(action.kind)
        if safety_level < minimum_level:
            warnings.append(
                f"Skipped {action.action_id} at safety level {safety_level}; "
                f"{action.kind} requires level {minimum_level}."
            )
            continue

        if action.risk_level == "high" and not allow_high_risk:
            warnings.append(
                f"Skipped {action.action_id}; high-risk actions require explicit approval flags."
            )
            continue

        allowed_actions.append(action)

    return allowed_actions, warnings

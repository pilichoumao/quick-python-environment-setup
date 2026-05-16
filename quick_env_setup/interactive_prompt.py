from __future__ import annotations

from collections.abc import Callable


InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]


def prompt_yes_no(
    message: str,
    *,
    default: bool = False,
    injected_response: bool | None = None,
    input_func: InputFunc = input,
    output_func: OutputFunc | None = None,
) -> bool:
    if injected_response is not None:
        if output_func is not None:
            output_func(_render_prompt_echo(message, injected_response))
        return injected_response

    suffix = "[Y/n]" if default else "[y/N]"
    prompt = f"{message} {suffix} "
    while True:
        raw_value = input_func(prompt).strip().lower()
        if not raw_value:
            return default
        if raw_value in {"y", "yes"}:
            return True
        if raw_value in {"n", "no"}:
            return False
        if output_func is not None:
            output_func("Please answer yes or no.")


def confirm_low_risk_execution(
    *,
    injected_response: bool | None = None,
    input_func: InputFunc = input,
    output_func: OutputFunc | None = None,
) -> bool:
    return prompt_yes_no(
        "Proceed with the planned environment setup actions?",
        default=False,
        injected_response=injected_response,
        input_func=input_func,
        output_func=output_func,
    )


def _render_prompt_echo(message: str, response: bool) -> str:
    answer = "yes" if response else "no"
    return f"{message} [auto-answer: {answer}]"

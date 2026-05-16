# Quick Python Environment Setup

This skill helps configure Python environments for open-source projects.

## When to Use

Use this skill when the user asks to:

- set up a Python project
- run a GitHub Python repository
- configure Conda or venv
- fix Python dependency installation issues
- install PyTorch with CPU, CUDA, or MPS

## Default Behavior

- Use Level 2 safety mode.
- Do not run project code by default.
- Ask before running demo commands.
- Ask before deleting environments.
- Ask before using `sudo`.

## Recommended Command

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Then show the plan to the user before running the non-dry path.

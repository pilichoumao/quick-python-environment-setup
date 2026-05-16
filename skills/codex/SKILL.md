# Quick Python Environment Setup

Use this skill when the user wants to configure a Python environment for an open-source project.

The user may provide:

- a GitHub URL
- a GitLab URL
- a local project path

## Workflow

1. Run a dry-run first.
2. Present the detected setup plan.
3. Ask for confirmation on key decisions when needed.
4. Run setup in Level 2 mode by default.
5. Do not run project demo code unless the user explicitly confirms.

## Commands

Dry run:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Default setup:

```bash
python -m quick_env_setup --source <path_or_url> --level 2
```

## Safety

Never automatically run:

- `python train.py`
- `python demo.py`
- `python app.py`
- `sudo` commands
- environment deletion

The CLI is the source of truth. If the CLI behavior changes, update this skill to match it.

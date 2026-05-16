# AGENTS.md

## Project Overview

This repository implements Quick Python Environment Setup, an agent-friendly CLI tool for configuring Python environments for open-source projects.

The tool accepts either:

- a GitHub or GitLab repository URL
- a local project path

It analyzes the project, detects Python version requirements, creates an isolated environment, installs dependencies, handles PyTorch CPU/CUDA/MPS strategies, diagnoses dependency conflicts, and generates a final setup report.

## Main Commands

Dry-run analysis:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Default Level 2 setup:

```bash
python -m quick_env_setup --source <path_or_url>
```

Use Conda explicitly:

```bash
python -m quick_env_setup --source <path_or_url> --env-manager conda
```

Use venv explicitly:

```bash
python -m quick_env_setup --source <path_or_url> --env-manager venv
```

## Safety Rules

Agents must not automatically:

- delete existing environments
- delete project directories
- execute `sudo` commands
- run training scripts
- run demo scripts
- run unknown project code
- download large model weights without confirmation

Default behavior is Level 2:

- analyze the project
- create an environment
- install dependencies
- run low-risk validation
- do not run project demo code automatically

Demo execution requires explicit user confirmation.

## Testing

Run the full unit suite:

```bash
pytest -q
```

Run a safe dry-run check:

```bash
python -m quick_env_setup --source tests/fixtures/deep_learning_project --dry-run
```

## Coding Guidelines

- Prefer standard library helpers where practical.
- Use `subprocess.run()` with argument lists and `shell=False`.
- Keep platform-specific logic isolated.
- Keep CLI behavior as the source of truth for all agent adapters.
- Keep agent-specific documents aligned with the actual CLI flags and safety behavior.

# Quick Python Environment Setup

Quick Python Environment Setup is an agent-friendly CLI for analyzing and setting up Python environments for open-source projects.

It accepts either:

- a GitHub or GitLab repository URL
- a local project path

Then it helps with:

- project type detection
- Python version inference
- Conda or venv selection
- CPU / NVIDIA CUDA / Apple MPS branching
- PyTorch install strategy
- dependency installation
- conflict analysis
- China mirror selection
- low-risk validation
- run command discovery
- missing asset hints
- final report generation

The core design goal is simple: keep the setup logic in a normal Python package and CLI so different coding agents can call the same tool without platform-specific glue.

## Status

This repository currently implements the MVP line of the project.

What is working now:

- local path and Git URL planning
- default Level 2 workflow
- Conda recommendation with venv support
- project scanning and classification
- Python version resolution
- CPU / NVIDIA / Apple Silicon device branching
- PyTorch strategy resolution
- execution logging and conflict analysis
- validation, run discovery, asset detection, and report artifacts
- Codex / Claude Code / Copilot / Qoder / generic agent docs

What is intentionally not in the current MVP:

- automatic demo execution
- Dockerfile generation
- Poetry / Pipenv workflows
- ROCm automation
- automatic model or dataset download
- full automatic dependency repair
- GUI

## Install

From the repository root:

```bash
python -m pip install -e .
```

Optional test dependencies:

```bash
python -m pip install -e .[test]
```

## Quick Start

Dry-run a local project:

```bash
python -m quick_env_setup --source /path/to/project --dry-run
```

Dry-run a repository URL:

```bash
python -m quick_env_setup --source https://github.com/owner/repo --dry-run
```

Run the default Level 2 setup flow:

```bash
python -m quick_env_setup --source /path/to/project --yes
```

Use Conda explicitly:

```bash
python -m quick_env_setup --source /path/to/project --env-manager conda
```

Use venv explicitly:

```bash
python -m quick_env_setup --source /path/to/project --env-manager venv
```

Use a China mirror:

```bash
python -m quick_env_setup --source /path/to/project --use-china-mirror --mirror tuna --dry-run
```

## Default Behavior

The CLI defaults to safety Level 2.

That means it will:

- analyze the project
- create an isolated environment
- install dependencies
- run low-risk validation
- generate logs and reports

That also means it will not:

- run project demo code automatically
- run training or inference scripts automatically
- delete environments automatically
- delete project directories automatically
- use `sudo` automatically

## CLI

Current help output:

```text
usage: quick-env-setup [-h] --source SOURCE [--env-manager {conda,venv}]
                       [--env-name ENV_NAME] [--python PYTHON_VERSION]
                       [--clone-dir CLONE_DIR] [--cpu-only]
                       [--use-china-mirror] [--mirror {tuna,ustc,aliyun}]
                       [--dry-run] [--yes] [--level {1,2,3}] [--run-demo]
```

Key flags:

- `--source`: local path or supported Git URL
- `--dry-run`: print the plan without executing it
- `--env-manager`: force `conda` or `venv`
- `--python`: override detected Python version
- `--cpu-only`: force CPU planning
- `--use-china-mirror --mirror <provider>`: mirror-aware planning
- `--yes`: skip the execution confirmation prompt
- `--level`: choose safety level

## Reports and Logs

Execution artifacts are written under `.env_setup_logs/`.

Current report set includes:

- `commands.log`
- `detected_config.json`
- `install_plan.json`
- `error_summary.txt`
- `run_candidates.txt`
- `missing_assets.txt`
- `final_report.txt`
- `agent_trace_summary.txt`

When setup fails, the CLI now prints a short failure summary before the full execution summary. That summary includes:

- the failed action
- the detected failure category when available
- a one-line explanation from `error_summary.txt`
- the exact `error_summary.txt` path to inspect next

## Development

Run the full test suite:

```bash
pytest -q
```

Run the main focused verification suite:

```bash
pytest tests/test_source_resolver.py \
  tests/test_project_type_detector.py \
  tests/test_python_version_resolver.py \
  tests/test_pytorch_resolver.py \
  tests/test_conflict_analyzer.py \
  tests/test_asset_detector.py \
  tests/test_orchestrator_planning.py \
  tests/test_env_managers.py \
  tests/test_report_generator.py -q
```

Try the fixture dry-run:

```bash
python -m quick_env_setup --source tests/fixtures/deep_learning_project --dry-run
```

## Agent Adapters

Agent-facing integration docs live in:

- [AGENTS.md](./AGENTS.md)
- [skills/codex/SKILL.md](./skills/codex/SKILL.md)
- [skills/claude-code/SKILL.md](./skills/claude-code/SKILL.md)
- [skills/copilot/instructions.md](./skills/copilot/instructions.md)
- [.qoder/rules/quick-python-environment-setup.md](./.qoder/rules/quick-python-environment-setup.md)

The CLI is the source of truth. Agent adapters should describe when and how to call the CLI, not reimplement its logic.

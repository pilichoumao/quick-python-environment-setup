# Quick Python Environment Setup

Use this skill when an agent needs to analyze or configure a Python environment for a local project path or a remote Git repository.

## Principles

- Prefer a dry-run first.
- Default to Level 2 behavior.
- Recommend Conda for deep-learning projects.
- Do not run project demo code by default.
- Ask before high-risk or destructive actions.

## Commands

Dry run:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Default setup:

```bash
python -m quick_env_setup --source <path_or_url>
```

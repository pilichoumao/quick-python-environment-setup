# GitHub Copilot Instructions

This repository implements an agent-friendly Python environment setup CLI.

When modifying this project:

- keep CLI behavior stable
- keep the CLI as the source of truth for agent adapters
- preserve Level 2 as the default safety mode
- do not introduce unsafe automatic demo execution
- do not run project demo code in tests
- maintain cross-platform behavior
- update `AGENTS.md` and adapter docs when CLI behavior changes

## Main Commands

Dry run:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Test suite:

```bash
pytest -q
```

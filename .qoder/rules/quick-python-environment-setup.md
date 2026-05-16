# Quick Python Environment Setup Rule

When working on this repository, treat it as an agent-friendly Python environment setup tool.

## Expected Behavior

- preserve cross-platform compatibility
- keep Codex, Claude Code, Qoder, Copilot, and generic adapter files aligned
- do not hard-code one agent platform into the core logic
- keep the CLI as the source of truth
- keep Level 2 as the default safety mode

## Safety

Do not implement automatic execution of project demo code unless it is gated behind explicit confirmation.

## Test Command

```bash
pytest -q
```

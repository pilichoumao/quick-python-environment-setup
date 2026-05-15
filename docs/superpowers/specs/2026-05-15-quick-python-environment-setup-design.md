# Quick Python Environment Setup Technical Design

> This document translates the product requirements in `REQUIREMENTS.md` into an implementation-oriented technical design. It defines architecture, module boundaries, data contracts, execution flow, safety enforcement, and testing strategy for the MVP.

## 1. Purpose

Quick Python Environment Setup is a cross-platform, agent-neutral Python environment setup tool for beginners and open-source project users. It accepts either a Git repository URL or a local project path, analyzes the project, creates an isolated environment, installs dependencies with device-aware strategies, performs low-risk validation, and generates a final report.

This document answers the engineering questions that the requirements document leaves open:

- How the system is decomposed
- Which modules own which decisions
- What data structures flow between modules
- How dry-run and execution share logic
- How safety rules are enforced consistently
- How agent adapters stay thin and CLI remains the source of truth

## 2. Design Goals

### 2.1 Primary goals

- Keep core logic independent from any specific agent platform.
- Make planning and execution deterministic and inspectable.
- Default to safe behavior for beginners.
- Support Windows, macOS, and Linux without hard-coding a single platform path model.
- Keep failure output understandable and actionable.

### 2.2 Non-goals for MVP

- Full Poetry or Pipenv workflow support
- Automatic Dockerfile generation
- Automatic model weight or dataset download
- Automatic ROCm configuration
- Automatic repair of all dependency conflicts
- Full GUI application

## 3. Architectural Overview

The architecture is organized as four layers:

```text
Agent adapters / docs
        |
CLI entrypoint
        |
Planning + orchestration
        |
Domain services + executors
```

### 3.1 Layer responsibilities

- Agent adapters:
  Human-readable instructions for Codex, Claude Code, Qoder, Copilot, and generic agents. They do not contain setup logic.
- CLI:
  Parses arguments, starts orchestration, renders output, and exits with a suitable code.
- Planning and orchestration:
  Resolves source, scans project, detects environment strategy, builds an install plan, enforces safety, and coordinates execution.
- Domain services and executors:
  Small focused modules that parse files, inspect the machine, classify project type, build commands, install dependencies, analyze errors, validate the environment, and produce reports.

### 3.2 Core principle

The install plan is the system's central contract.

Everything before plan creation is analysis.
Everything after plan creation is execution, validation, or reporting.

This lets the tool support:

- `--dry-run`: analyze and emit plan only
- Level 2 setup: analyze, execute, validate, report
- Level 3 setup: same as Level 2, plus explicit demo execution gate

## 4. High-Level Execution Flow

```text
Input source
  -> source resolution
  -> local project path acquisition
  -> system detection
  -> project scan
  -> project classification
  -> Python version resolution
  -> environment manager selection
  -> device detection
  -> PyTorch strategy resolution
  -> mirror strategy resolution
  -> install plan construction
  -> safety enforcement
  -> plan execution
  -> conflict analysis on failure
  -> validation on success
  -> run command discovery
  -> asset detection
  -> final report generation
```

## 5. Main Runtime Concepts

The MVP should be organized around a small set of explicit data models. `dataclasses` are sufficient for the first version and keep the code lightweight.

### 5.1 `SourceSpec`

Represents the user input before local materialization.

Suggested fields:

```python
@dataclass
class SourceSpec:
    raw: str
    source_type: Literal["git_url", "local_path"]
    normalized: str
```

### 5.2 `SourceResolutionResult`

Represents the resolved working project directory.

Suggested fields:

```python
@dataclass
class SourceResolutionResult:
    source: SourceSpec
    local_project_path: Path
    clone_performed: bool
    repo_url: str | None = None
```

### 5.3 `SystemInfo`

Describes host OS and architecture.

Suggested fields:

```python
@dataclass
class SystemInfo:
    os_name: Literal["windows", "macos", "linux"]
    arch: str
    is_apple_silicon: bool
    has_conda: bool
    has_git: bool
    python_executables: list[str]
```

### 5.4 `ProjectScanResult`

A raw inventory of files, markers, dependencies, and extracted hints.

Suggested fields:

```python
@dataclass
class ProjectScanResult:
    root: Path
    detected_files: list[Path]
    dependency_files: list[Path]
    readme_path: Path | None
    python_entry_candidates: list[str]
    notebook_paths: list[Path]
    keywords: set[str]
    parsed_dependency_hints: dict[str, Any]
```

### 5.5 `ProjectProfile`

The classified project view used by planning.

Suggested fields:

```python
@dataclass
class ProjectProfile:
    project_type: Literal[
        "deep_learning",
        "python_package",
        "web",
        "notebook",
        "cli_tool",
        "data_analysis",
        "uncertain",
    ]
    confidence: float
    needs_pytorch: bool
    recommended_env_manager: Literal["conda", "venv"]
    editable_install_recommended: bool
```

### 5.6 `PythonRequirement`

Represents the inferred interpreter recommendation.

Suggested fields:

```python
@dataclass
class PythonRequirement:
    version: str
    source: Literal[
        "environment_yml",
        "conda_yml",
        "pyproject_toml",
        "setup_py",
        "setup_cfg",
        "readme",
        "default",
        "user_override",
    ]
    rationale: str
```

### 5.7 `DeviceInfo`

Represents hardware and runtime hints relevant to dependency strategy.

Suggested fields:

```python
@dataclass
class DeviceInfo:
    accelerator_type: Literal["cpu", "nvidia", "apple_mps", "amd_unknown"]
    gpu_name: str | None
    cuda_driver_version: str | None
    cuda_runtime_version: str | None
    nvidia_smi_available: bool
```

### 5.8 `PyTorchStrategy`

Separates PyTorch handling from generic dependency installation.

Suggested fields:

```python
@dataclass
class PyTorchStrategy:
    required: bool
    install_separately: bool
    variant: Literal["none", "cpu", "cuda", "mps"]
    index_url: str | None
    packages: list[str]
    stripped_requirements_path: Path | None
    rationale: str
```

### 5.9 `MirrorConfig`

Defines optional package source acceleration.

Suggested fields:

```python
@dataclass
class MirrorConfig:
    enabled: bool
    provider: Literal["none", "tuna", "ustc", "aliyun"]
    pip_index_url: str | None
    conda_channels: list[str]
```

### 5.10 `InstallAction`

Represents one executable step. This is the smallest runtime execution unit.

Suggested fields:

```python
@dataclass
class InstallAction:
    action_id: str
    kind: Literal[
        "check",
        "clone",
        "create_env",
        "upgrade_packaging_tools",
        "install_pytorch",
        "install_dependencies",
        "editable_install",
        "validate",
        "discover",
        "report",
    ]
    command: list[str] | None
    cwd: Path | None
    env_overrides: dict[str, str]
    risk_level: Literal["low", "medium", "high"]
    description: str
    skippable: bool = False
```

### 5.11 `InstallPlan`

The central planning artifact.

Suggested fields:

```python
@dataclass
class InstallPlan:
    source_result: SourceResolutionResult
    system_info: SystemInfo
    project_scan: ProjectScanResult
    project_profile: ProjectProfile
    python_requirement: PythonRequirement
    env_manager: Literal["conda", "venv"]
    env_name: str
    device_info: DeviceInfo
    pytorch_strategy: PyTorchStrategy
    mirror_config: MirrorConfig
    safety_level: int
    actions: list[InstallAction]
    warnings: list[str]
    assumptions: list[str]
```

### 5.12 `ExecutionResult`

Captures the outcome of running the plan.

Suggested fields:

```python
@dataclass
class ExecutionResult:
    success: bool
    completed_action_ids: list[str]
    failed_action_id: str | None
    exit_code: int | None
    log_path: Path
    stdout_tail: str
    stderr_tail: str
```

### 5.13 `ConflictReport`

Translates low-level install failures into user-facing diagnosis.

Suggested fields:

```python
@dataclass
class ConflictReport:
    category: Literal[
        "python_version_incompatible",
        "package_conflict",
        "missing_build_tools",
        "missing_system_library",
        "pytorch_cuda_mismatch",
        "network_failure",
        "missing_assets",
        "project_code_issue",
        "unknown",
    ]
    summary: str
    evidence: list[str]
    recommendations: list[str]
```

### 5.14 `ValidationReport`

Represents low-risk checks run after successful setup.

Suggested fields:

```python
@dataclass
class ValidationReport:
    passed: bool
    checks_run: list[str]
    failures: list[str]
```

### 5.15 `FinalReport`

User-facing structured summary serialized to text and JSON.

Suggested fields:

```python
@dataclass
class FinalReport:
    overview: dict[str, Any]
    validation: ValidationReport
    run_candidates: list[str]
    missing_assets: list[str]
    warnings: list[str]
    next_steps: list[str]
```

## 6. Module Responsibilities

### 6.1 `cli.py`

Owns:

- Argument parsing
- Default values
- Human-facing output style
- Exit codes
- Invoking orchestration

Must not own:

- File parsing logic
- Device detection details
- Install command composition

### 6.2 `source_resolver.py`

Owns:

- Distinguishing Git URL vs local path
- Normalizing source input
- Producing `SourceSpec`

### 6.3 `git_handler.py`

Owns:

- Verifying `git` availability
- Cloning repositories
- Handling existing clone target conflicts

Must never:

- Delete directories without explicit approval path

### 6.4 `system_detector.py`

Owns:

- OS and architecture detection
- Conda presence check
- Git presence check
- Local Python executable discovery

### 6.5 `project_scanner.py`

Owns:

- Walking project files with ignore rules
- Detecting dependency files
- Extracting keyword markers
- Collecting candidate run files and notebooks

### 6.6 `project_type_detector.py`

Owns:

- Translating scan hints into `ProjectProfile`
- Deciding confidence and recommended environment manager

### 6.7 `dependency_file_parser.py`

Owns:

- Parsing `requirements.txt`, `environment.yml`, `pyproject.toml`, `setup.cfg`, and `setup.py` where practical
- Extracting dependency hints and Python constraints

Notes:

- MVP can parse `setup.py` conservatively with regex/text heuristics rather than AST execution.
- Never execute repository Python code to inspect metadata.

### 6.8 `python_version_resolver.py`

Owns:

- Source precedence
- Defaulting to Python `3.10`
- Generating `PythonRequirement`

### 6.9 `env_manager.py`

Owns:

- Shared environment-manager interface
- Selecting the manager implementation

Suggested abstraction:

```python
class EnvironmentManager(Protocol):
    def create_environment(self, env_name: str, python_version: str) -> InstallAction: ...
    def python_command(self, env_name: str) -> list[str]: ...
    def pip_install_command(self, env_name: str, args: list[str]) -> list[str]: ...
```

### 6.10 `conda_manager.py`

Owns:

- Conda-specific command composition
- `conda create`
- `conda run -n <env>`
- Optional mirror-aware channel command generation

### 6.11 `venv_manager.py`

Owns:

- `.venv` path conventions by platform
- `python -m venv`
- In-environment Python and pip command composition

### 6.12 `device_detector.py`

Owns:

- NVIDIA detection via `nvidia-smi`
- Apple Silicon and MPS branch detection
- Conservative AMD fallback

### 6.13 `pytorch_resolver.py`

Owns:

- Determining whether PyTorch is required
- Choosing CPU, CUDA, MPS, or none
- Choosing official index URLs
- Producing stripped requirements when separate install is needed

Must not own:

- Generic dependency installation

### 6.14 `mirror_manager.py`

Owns:

- Mapping mirror provider names to pip and conda config
- Avoiding global config overwrite by default

MVP recommendation:

- Prefer command-scoped mirror usage over mutating user global config.

### 6.15 `dependency_installer.py`

Owns:

- Turning `InstallPlan.actions` into subprocess calls
- Logging commands and outputs
- Returning `ExecutionResult`

Must use:

- `subprocess.run(..., shell=False)`

### 6.16 `conflict_analyzer.py`

Owns:

- Pattern matching install and validation failures
- Mapping failure evidence to `ConflictReport`

### 6.17 `run_command_discoverer.py`

Owns:

- Scanning `README`, known directories, and known filenames for run candidates
- Producing suggestions only

Must not:

- Run project code automatically

### 6.18 `asset_detector.py`

Owns:

- Detecting likely missing weights, datasets, configs, and `.env` requirements
- Extracting possible download references from `README`

### 6.19 `validator.py`

Owns:

- Low-risk verification only
- Environment-level checks like `python --version`, `pip --version`, import probes, and device-aware torch checks

### 6.20 `safety_policy.py`

Owns:

- Risk categorization
- Level-based action gating
- Confirmation requirements for high-risk actions

### 6.21 `report_generator.py`

Owns:

- Writing machine-readable JSON artifacts
- Rendering final human-readable report

### 6.22 `interactive_prompt.py`

Owns:

- Safe user prompts for ambiguous or risky decisions

Important rule:

- Core planning code must accept resolved values as parameters so non-interactive agents can bypass prompt logic with flags.

### 6.23 `logger.py`

Owns:

- Structured logging setup
- Log file paths
- Log formatting helpers

### 6.24 `utils.py`

Owns:

- Small pure helpers only

Must not become:

- A catch-all dumping ground for unrelated business logic

## 7. Planning vs Execution

The MVP should separate planning from execution cleanly.

### 7.1 Why this matters

- Dry-run becomes first-class, not a special case.
- Agent adapters can inspect the plan before approving execution.
- Reports can explain decisions even when nothing is executed.
- Tests can validate planning without touching the machine.

### 7.2 Planning phase responsibilities

Planning should:

- Resolve source
- Detect system and project attributes
- Resolve Python, device, mirror, and PyTorch strategy
- Construct ordered `InstallAction` objects
- Add warnings and assumptions

Planning should not:

- Run install commands
- Modify global package manager config
- Execute project code

### 7.3 Execution phase responsibilities

Execution should:

- Run plan actions in order
- Stream and persist logs
- Stop on failure
- Return structured failure state

Execution should not:

- Re-decide core strategy
- Discover entirely new plan branches mid-run unless explicitly modeled as optional follow-up actions

## 8. Install Plan Composition

The planner should build actions in a predictable order.

Suggested action sequence:

1. Preconditions:
   `git` presence if source is remote, `conda` presence if manager is conda
2. Source acquisition:
   clone if required
3. Environment creation:
   conda or venv
4. Packaging tools upgrade:
   `pip`, `setuptools`, `wheel`
5. PyTorch install:
   only if `PyTorchStrategy.required` and `install_separately`
6. Main dependency install:
   `requirements.txt`, `environment.yml`, or editable install
7. Optional package install:
   `pip install -e .` when package structure warrants it
8. Validation:
   low-risk import and version checks
9. Discovery:
   run candidate scan and asset scan
10. Report generation

### 8.1 Decision precedence

When user input conflicts with recommendations:

- Explicit CLI flags win.
- Safety policy can still block unsafe execution unless the user explicitly opted in through the corresponding flag.

Examples:

- `--env-manager venv` overrides recommended conda.
- `--python 3.9` overrides inferred `3.10`.
- `--cpu-only` overrides NVIDIA-based CUDA recommendation.

## 9. Safety Model

### 9.1 Risk categories

- Low risk:
  source analysis, file parsing, environment creation, dependency installation, import validation
- Medium risk:
  clone into filesystem, editable install, command-scoped mirror use
- High risk:
  deleting environments, deleting directories, running demo code, running training/inference/web services, `sudo`, downloading large assets

### 9.2 Level semantics

- Level 1:
  Build plan only. No environment creation, installs, or validation subprocesses.
- Level 2:
  Create environment, install dependencies, and run low-risk validation only.
- Level 3:
  Same as Level 2, plus user-confirmed project command execution.

### 9.3 Enforcement strategy

Enforcement belongs in `safety_policy.py`, not scattered across modules.

Suggested API:

```python
class SafetyPolicy:
    def validate_plan(self, plan: InstallPlan) -> None: ...
    def can_execute_action(self, action: InstallAction, level: int) -> bool: ...
```

This keeps policy centralized and testable.

## 10. Device and PyTorch Strategy

### 10.1 Device resolution rules

- If `--cpu-only` is set, use CPU regardless of host GPU.
- If NVIDIA GPU is detected, use CUDA strategy based on supported official wheel index.
- If Apple Silicon is detected, use non-CUDA PyTorch and validate MPS availability.
- If AMD or unknown accelerator is detected, default to CPU and explain the limitation.

### 10.2 PyTorch special handling rules

- If project does not appear to require PyTorch, do not install it separately.
- If project requires PyTorch and generic requirements contain torch packages, strip them from the generic dependency install path.
- Use official PyTorch index URLs for CPU and CUDA variants.
- Keep generated stripped requirements inside the log/artifact directory, not mixed into user project files by default.

## 11. Dependency Resolution Strategy

The MVP should support the following sources first:

- `requirements.txt`
- `environment.yml` or `conda.yml`
- `pyproject.toml`

### 11.1 Preferred install behavior

- Conda environment creation is separate from pip package install.
- For Conda mode, use `conda run -n <env>` to avoid shell activation coupling.
- For venv mode, run the environment-local Python executable directly.
- If a package project is detected and no better dependency file exists, support `pip install -e .`.

### 11.2 Conservative parsing rules

- Never execute project build hooks or arbitrary project Python during analysis.
- Parse config files statically.
- If metadata is ambiguous, downgrade confidence and explain assumptions.

## 12. Logging and Artifact Design

All run artifacts live under:

```text
.env_setup_logs/
```

### 12.1 Artifact responsibilities

- `setup.log`:
  append-only execution log with timestamped command records
- `detected_config.json`:
  normalized environment and project detection output
- `install_plan.json`:
  serialized `InstallPlan`
- `error_summary.txt`:
  human-readable failure analysis
- `run_candidates.txt`:
  discovered run suggestions
- `missing_assets.txt`:
  missing weights/config/dataset hints
- `final_report.txt`:
  final human-readable report
- `agent_trace_summary.txt`:
  short summary tailored for external agents or wrappers

### 12.2 Serialization strategy

- Use JSON for machine-readable artifacts.
- Use plain text for user-facing summaries.
- Keep artifact paths stable so agent wrappers can read them reliably.

## 13. Error Handling Strategy

Errors should be classified into three major buckets:

### 13.1 Planning errors

Examples:

- source path does not exist
- unsupported source string
- `conda` required but missing
- clone target conflict without approval path

Behavior:

- fail fast
- explain the blocking condition
- do not emit partial execution results as if install started

### 13.2 Execution errors

Examples:

- package resolution failure
- wheel build failure
- network timeout
- CUDA mismatch

Behavior:

- stop at first failing action
- persist full logs
- summarize failure through `ConflictReport`

### 13.3 Validation warnings

Examples:

- `cv2` import missing
- torch import passes but CUDA unavailable
- MPS unavailable on Apple Silicon

Behavior:

- do not hide successful install if validation is partial
- surface warnings and suggested next actions

## 14. Interface Between CLI and Agent Adapters

Agent adapters must remain thin and declarative.

### 14.1 Rules for adapters

- They describe when to call the tool and how to interpret results.
- They never embed platform-specific setup logic that diverges from CLI behavior.
- They should prefer `--dry-run` first.
- They should surface plan summary before execution where the host agent supports it.

### 14.2 Source of truth

The CLI is the source of truth for:

- accepted inputs
- default flags
- plan behavior
- safety defaults
- artifact output

Adapters are documentation and invocation affordances, not alternate implementations.

## 15. Testing Strategy

Testing should be layered so most behavior is validated without mutating the machine.

### 15.1 Unit tests

Target pure or near-pure logic:

- source classification
- project type classification
- Python version precedence
- PyTorch strategy selection
- conflict analysis
- asset detection

These tests should use fixtures with small fake project directories.

### 15.2 Contract tests for planning

Test the planner end-to-end without execution:

- remote repo dry-run plan
- local path dry-run plan
- deep learning project plan on CPU
- NVIDIA project plan with CUDA branch
- notebook project plan with kernel recommendation

Assertions should focus on plan contents and action ordering.

### 15.3 Execution tests

Keep these narrow:

- subprocess command composition
- environment-manager command generation
- log writing

Use mocks or fakes for subprocess calls.

### 15.4 Fixture design

Recommended fixture directories:

```text
tests/fixtures/
├── deep_learning_project/
├── web_project/
├── notebook_project/
├── package_project/
└── broken_project/
```

### 15.5 Cross-platform testing posture

Unit tests should avoid hard-coded path assumptions.
Where platform-specific behavior exists, isolate it behind helpers and test expected command generation rather than actual environment creation.

## 16. Recommended Package Structure

The requirements document's structure is solid. For implementation clarity, the MVP should add one orchestration-focused module:

```text
quick_env_setup/
├── __init__.py
├── cli.py
├── orchestrator.py
├── models.py
├── source_resolver.py
├── git_handler.py
├── system_detector.py
├── project_type_detector.py
├── env_manager.py
├── conda_manager.py
├── venv_manager.py
├── project_scanner.py
├── dependency_file_parser.py
├── python_version_resolver.py
├── device_detector.py
├── pytorch_resolver.py
├── mirror_manager.py
├── dependency_installer.py
├── conflict_analyzer.py
├── asset_detector.py
├── run_command_discoverer.py
├── validator.py
├── safety_policy.py
├── report_generator.py
├── interactive_prompt.py
├── logger.py
└── utils.py
```

### 16.1 Why add `orchestrator.py`

Without it, `cli.py` becomes a dumping ground for workflow assembly. `orchestrator.py` should own the end-to-end sequence while leaving each decision in focused service modules.

### 16.2 Why add `models.py`

The MVP needs shared runtime contracts. Keeping dataclasses in one place reduces circular imports and makes plan serialization easier.

## 17. Recommended MVP Build Order

### Phase 1: Skeleton and models

- project packaging
- `cli.py`
- `models.py`
- `orchestrator.py`
- `logger.py`

### Phase 2: Analysis pipeline

- `source_resolver.py`
- `system_detector.py`
- `project_scanner.py`
- `dependency_file_parser.py`
- `project_type_detector.py`
- `python_version_resolver.py`
- `device_detector.py`

### Phase 3: Planning pipeline

- `env_manager.py`
- `conda_manager.py`
- `venv_manager.py`
- `pytorch_resolver.py`
- `mirror_manager.py`
- `safety_policy.py`
- plan serialization

### Phase 4: Execution and diagnostics

- `dependency_installer.py`
- `validator.py`
- `conflict_analyzer.py`
- `report_generator.py`

### Phase 5: Discovery and agent compatibility

- `run_command_discoverer.py`
- `asset_detector.py`
- `AGENTS.md`
- skill adapter docs
- examples

## 18. Open Design Decisions

These are the remaining decisions worth making before implementation starts:

1. Should `environment.yml` be treated as an install source only in Conda mode, or also mined for pip dependencies in venv mode.
2. Whether `--yes` should silently accept all low-risk defaults or still print a confirmation summary.
3. Whether generated stripped requirements files should be cleaned up automatically after success or retained in artifacts.
4. Whether notebook kernel registration belongs in MVP execution or should stay as a recommendation only.
5. How aggressive README parsing should be for extracting run commands and asset download links.

## 19. Recommended Default Decisions

To keep MVP scope under control, this document recommends:

1. `environment.yml` is parsed for hints in all modes, but directly executed only in Conda mode.
2. `--yes` accepts low-risk defaults without extra prompt, but the final plan summary must still record those assumptions.
3. Generated stripped requirements files are retained in `.env_setup_logs/` for traceability.
4. Notebook kernel registration is recommended, not executed automatically, in MVP.
5. README parsing should use targeted heuristics rather than full natural-language extraction.

## 20. Implementation Readiness Summary

The requirements are mature enough to proceed.

What was missing before this document:

- explicit runtime models
- planner vs executor boundary
- module ownership
- safety enforcement location
- logging and artifact contracts
- testing layers

With this design in place, the next step should be a task-level implementation plan, not immediate free-form coding.

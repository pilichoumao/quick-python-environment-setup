# Quick Python Environment Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP of an agent-neutral CLI tool that analyzes a Python project source, creates an isolated environment, installs dependencies safely, validates the setup, and produces structured logs and reports.

**Architecture:** The implementation centers on an explicit planning pipeline that produces an `InstallPlan` from source analysis, system detection, project classification, Python/device resolution, and safety policy decisions. Execution, validation, and reporting consume that plan without re-deciding core strategy, keeping `--dry-run` and real execution on the same contract.

**Tech Stack:** Python 3.10+, standard library, `pytest`, `tomllib` when available, `yaml` parsing through optional dependency or conservative text fallback, subprocess-based command execution with `shell=False`

---

## File Structure

Planned file responsibilities for the MVP:

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `quick_env_setup/__init__.py`
- Create: `quick_env_setup/__main__.py`
- Create: `quick_env_setup/cli.py`
- Create: `quick_env_setup/orchestrator.py`
- Create: `quick_env_setup/models.py`
- Create: `quick_env_setup/logger.py`
- Create: `quick_env_setup/source_resolver.py`
- Create: `quick_env_setup/git_handler.py`
- Create: `quick_env_setup/system_detector.py`
- Create: `quick_env_setup/project_scanner.py`
- Create: `quick_env_setup/project_type_detector.py`
- Create: `quick_env_setup/dependency_file_parser.py`
- Create: `quick_env_setup/python_version_resolver.py`
- Create: `quick_env_setup/env_manager.py`
- Create: `quick_env_setup/conda_manager.py`
- Create: `quick_env_setup/venv_manager.py`
- Create: `quick_env_setup/device_detector.py`
- Create: `quick_env_setup/pytorch_resolver.py`
- Create: `quick_env_setup/mirror_manager.py`
- Create: `quick_env_setup/safety_policy.py`
- Create: `quick_env_setup/dependency_installer.py`
- Create: `quick_env_setup/conflict_analyzer.py`
- Create: `quick_env_setup/validator.py`
- Create: `quick_env_setup/run_command_discoverer.py`
- Create: `quick_env_setup/asset_detector.py`
- Create: `quick_env_setup/report_generator.py`
- Create: `quick_env_setup/interactive_prompt.py`
- Create: `quick_env_setup/utils.py`
- Create: `skills/codex/SKILL.md`
- Create: `skills/claude-code/SKILL.md`
- Create: `skills/copilot/instructions.md`
- Create: `skills/generic/SKILL.md`
- Create: `.qoder/rules/quick-python-environment-setup.md`
- Create: `examples/codex_prompt.md`
- Create: `examples/claude_code_prompt.md`
- Create: `examples/qoder_prompt.md`
- Create: `examples/generic_agent_prompt.md`
- Create: `tests/conftest.py`
- Create: `tests/test_source_resolver.py`
- Create: `tests/test_project_type_detector.py`
- Create: `tests/test_python_version_resolver.py`
- Create: `tests/test_pytorch_resolver.py`
- Create: `tests/test_conflict_analyzer.py`
- Create: `tests/test_asset_detector.py`
- Create: `tests/test_orchestrator_planning.py`
- Create: `tests/test_env_managers.py`
- Create: `tests/test_report_generator.py`
- Create: `tests/fixtures/deep_learning_project/`
- Create: `tests/fixtures/web_project/`
- Create: `tests/fixtures/notebook_project/`
- Create: `tests/fixtures/package_project/`
- Create: `tests/fixtures/broken_project/`

## Task 1: Bootstrap the package and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `quick_env_setup/__init__.py`
- Create: `quick_env_setup/__main__.py`
- Create: `quick_env_setup/cli.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing packaging smoke test**

Create a simple CLI smoke test in `tests/conftest.py` or a dedicated bootstrap test file that imports `quick_env_setup` and verifies `python -m quick_env_setup --help` can be invoked later.

- [ ] **Step 2: Run the targeted test to confirm the package does not exist yet**

Run: `pytest tests/test_source_resolver.py -q`
Expected: FAIL because the package and test file are not created yet

- [ ] **Step 3: Add project packaging and entrypoint files**

Implement:

- `pyproject.toml` with package metadata and `pytest` test dependency
- `quick_env_setup/__init__.py`
- `quick_env_setup/__main__.py` delegating to `cli.main`
- `quick_env_setup/cli.py` with minimal `argparse` skeleton and `--help`

- [ ] **Step 4: Add or adjust a real smoke test once the package exists**

Create a small test that imports `quick_env_setup.cli` and asserts the parser can be created.

- [ ] **Step 5: Run the smoke test**

Run: `pytest tests/test_env_managers.py -q`
Expected: PASS or a narrower initial bootstrap PASS if you place the smoke test elsewhere

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md quick_env_setup/__init__.py quick_env_setup/__main__.py quick_env_setup/cli.py tests
git commit -m "chore: bootstrap package and CLI entrypoint"
```

## Task 2: Define shared runtime models and logging primitives

**Files:**
- Create: `quick_env_setup/models.py`
- Create: `quick_env_setup/logger.py`
- Modify: `quick_env_setup/cli.py`
- Test: `tests/test_report_generator.py`

- [ ] **Step 1: Write failing tests for core model serialization assumptions**

Add tests that instantiate representative dataclasses such as `SourceSpec`, `ProjectProfile`, and `InstallPlan`, then assert required fields exist and can be converted into serializable dictionaries.

- [ ] **Step 2: Run the model-focused test**

Run: `pytest tests/test_report_generator.py -q`
Expected: FAIL because the models and serializer helpers do not exist yet

- [ ] **Step 3: Implement the shared dataclasses**

In `quick_env_setup/models.py`, add the MVP dataclasses described in the design document:

- `SourceSpec`
- `SourceResolutionResult`
- `SystemInfo`
- `ProjectScanResult`
- `ProjectProfile`
- `PythonRequirement`
- `DeviceInfo`
- `PyTorchStrategy`
- `MirrorConfig`
- `InstallAction`
- `InstallPlan`
- `ExecutionResult`
- `ConflictReport`
- `ValidationReport`
- `FinalReport`

- [ ] **Step 4: Implement minimal logging/artifact path helpers**

In `quick_env_setup/logger.py`, add helpers for:

- creating `.env_setup_logs/`
- computing artifact file paths
- appending timestamped command log lines

- [ ] **Step 5: Run the model and logger test**

Run: `pytest tests/test_report_generator.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add quick_env_setup/models.py quick_env_setup/logger.py quick_env_setup/cli.py tests/test_report_generator.py
git commit -m "feat: add shared runtime models and logging helpers"
```

## Task 3: Build source resolution and system detection

**Files:**
- Create: `quick_env_setup/source_resolver.py`
- Create: `quick_env_setup/git_handler.py`
- Create: `quick_env_setup/system_detector.py`
- Test: `tests/test_source_resolver.py`

- [ ] **Step 1: Write failing tests for source classification**

Cover:

- GitHub HTTPS URL
- GitLab SSH URL
- local POSIX path
- local Windows-like path string
- invalid/unsupported source

- [ ] **Step 2: Run the source resolver tests**

Run: `pytest tests/test_source_resolver.py -q`
Expected: FAIL because resolver and detector functions do not exist

- [ ] **Step 3: Implement source parsing and normalization**

In `source_resolver.py`, implement helpers that:

- classify `git_url` vs `local_path`
- normalize local paths
- return `SourceSpec`

- [ ] **Step 4: Implement system detection primitives**

In `system_detector.py`, implement pure and near-pure helpers for:

- OS name mapping
- architecture detection
- Apple Silicon detection
- `git` and `conda` presence checks

- [ ] **Step 5: Add conservative git clone helpers**

In `git_handler.py`, add command composition or thin execution helpers for:

- checking `git`
- clone target path selection
- safe conflict detection without deleting anything

- [ ] **Step 6: Re-run the source resolver tests**

Run: `pytest tests/test_source_resolver.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add quick_env_setup/source_resolver.py quick_env_setup/git_handler.py quick_env_setup/system_detector.py tests/test_source_resolver.py
git commit -m "feat: add source resolution and system detection"
```

## Task 4: Add fixture projects, project scanning, and project type detection

**Files:**
- Create: `tests/fixtures/deep_learning_project/`
- Create: `tests/fixtures/web_project/`
- Create: `tests/fixtures/notebook_project/`
- Create: `tests/fixtures/package_project/`
- Create: `tests/fixtures/broken_project/`
- Create: `quick_env_setup/project_scanner.py`
- Create: `quick_env_setup/project_type_detector.py`
- Test: `tests/test_project_type_detector.py`

- [ ] **Step 1: Create fake fixture projects**

Each fixture should include only the smallest files needed to express its type:

- deep learning fixture with `requirements.txt`, `train.py`, torch keywords
- web fixture with `app.py` or `main.py`, FastAPI or Flask markers
- notebook fixture with `.ipynb` placeholder and notebook directory
- package fixture with `pyproject.toml` or `setup.cfg`
- broken fixture with ambiguous or missing markers

- [ ] **Step 2: Write failing tests for scan and classification**

Assert:

- keywords are discovered
- dependency files are listed
- notebook paths are detected
- project type and recommended env manager are inferred

- [ ] **Step 3: Run the project type tests**

Run: `pytest tests/test_project_type_detector.py -q`
Expected: FAIL because scanner and classifier do not exist

- [ ] **Step 4: Implement project scanning**

In `project_scanner.py`, add directory traversal and marker extraction with a small ignore list for noisy directories like `.git`, `.venv`, `__pycache__`, and `node_modules`.

- [ ] **Step 5: Implement project type detection**

In `project_type_detector.py`, convert scan results into `ProjectProfile` using the heuristics from the requirements and design docs.

- [ ] **Step 6: Re-run the classification tests**

Run: `pytest tests/test_project_type_detector.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures quick_env_setup/project_scanner.py quick_env_setup/project_type_detector.py tests/test_project_type_detector.py
git commit -m "feat: add project scanning and project classification"
```

## Task 5: Implement dependency file parsing and Python version resolution

**Files:**
- Create: `quick_env_setup/dependency_file_parser.py`
- Create: `quick_env_setup/python_version_resolver.py`
- Test: `tests/test_python_version_resolver.py`

- [ ] **Step 1: Write failing tests for Python version precedence**

Cover:

- `environment.yml` takes precedence over `pyproject.toml`
- `pyproject.toml` takes precedence over `setup.cfg`
- `README.md` fallback
- default `3.10` fallback
- user override case

- [ ] **Step 2: Run the Python version tests**

Run: `pytest tests/test_python_version_resolver.py -q`
Expected: FAIL because the parser and resolver do not exist

- [ ] **Step 3: Implement static dependency and metadata parsing**

In `dependency_file_parser.py`, add conservative parsers for:

- `requirements.txt`
- `environment.yml` / `conda.yml`
- `pyproject.toml`
- `setup.cfg`
- text-based fallback parsing for `setup.py`

- [ ] **Step 4: Implement Python version resolution**

In `python_version_resolver.py`, consume parsed metadata and return `PythonRequirement` with source and rationale.

- [ ] **Step 5: Re-run the Python version tests**

Run: `pytest tests/test_python_version_resolver.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add quick_env_setup/dependency_file_parser.py quick_env_setup/python_version_resolver.py tests/test_python_version_resolver.py
git commit -m "feat: add dependency parsing and python version resolution"
```

## Task 6: Implement environment managers and mirror strategy

**Files:**
- Create: `quick_env_setup/env_manager.py`
- Create: `quick_env_setup/conda_manager.py`
- Create: `quick_env_setup/venv_manager.py`
- Create: `quick_env_setup/mirror_manager.py`
- Test: `tests/test_env_managers.py`

- [ ] **Step 1: Write failing tests for command generation**

Cover:

- conda environment creation command
- conda pip install command
- venv creation command
- venv-local Python executable path composition
- command-scoped pip mirror configuration

- [ ] **Step 2: Run the environment manager tests**

Run: `pytest tests/test_env_managers.py -q`
Expected: FAIL because the manager implementations do not exist

- [ ] **Step 3: Implement the shared environment manager protocol**

In `env_manager.py`, define the common interface and selection helper.

- [ ] **Step 4: Implement Conda and venv command builders**

Add `conda_manager.py` and `venv_manager.py` with command composition only, keeping execution elsewhere.

- [ ] **Step 5: Implement mirror configuration mapping**

In `mirror_manager.py`, map `tuna`, `ustc`, and `aliyun` to command-scoped pip URLs and optional conda channel hints.

- [ ] **Step 6: Re-run the environment manager tests**

Run: `pytest tests/test_env_managers.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add quick_env_setup/env_manager.py quick_env_setup/conda_manager.py quick_env_setup/venv_manager.py quick_env_setup/mirror_manager.py tests/test_env_managers.py
git commit -m "feat: add environment manager and mirror strategy"
```

## Task 7: Implement device detection and PyTorch strategy resolution

**Files:**
- Create: `quick_env_setup/device_detector.py`
- Create: `quick_env_setup/pytorch_resolver.py`
- Test: `tests/test_pytorch_resolver.py`

- [ ] **Step 1: Write failing tests for device-aware strategy selection**

Cover:

- CPU-only flag forces CPU
- NVIDIA detection chooses CUDA strategy
- Apple Silicon chooses MPS path
- no accelerator yields CPU
- non-torch project yields `required=False`
- torch dependencies trigger stripped requirements behavior

- [ ] **Step 2: Run the PyTorch strategy tests**

Run: `pytest tests/test_pytorch_resolver.py -q`
Expected: FAIL because the device detector and strategy resolver do not exist

- [ ] **Step 3: Implement `DeviceInfo` resolution helpers**

In `device_detector.py`, add:

- host inspection helpers
- `nvidia-smi` parsing helper
- Apple Silicon detection bridge from `SystemInfo`

- [ ] **Step 4: Implement PyTorch strategy resolution**

In `pytorch_resolver.py`, determine:

- whether PyTorch is required
- CPU, CUDA, MPS, or none
- official index URL
- stripped requirements path under `.env_setup_logs/`

- [ ] **Step 5: Re-run the PyTorch strategy tests**

Run: `pytest tests/test_pytorch_resolver.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add quick_env_setup/device_detector.py quick_env_setup/pytorch_resolver.py tests/test_pytorch_resolver.py
git commit -m "feat: add device detection and pytorch resolution"
```

## Task 8: Build safety policy and orchestration planning

**Files:**
- Create: `quick_env_setup/safety_policy.py`
- Create: `quick_env_setup/orchestrator.py`
- Modify: `quick_env_setup/cli.py`
- Test: `tests/test_orchestrator_planning.py`

- [ ] **Step 1: Write failing tests for dry-run planning**

Cover:

- local path produces an `InstallPlan`
- `--dry-run` avoids execution actions being run
- deep learning fixture defaults to conda
- explicit `--env-manager venv` overrides recommendation
- Level 1 plan excludes install execution
- high-risk actions are not allowed without proper flags

- [ ] **Step 2: Run the orchestrator planning tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: FAIL because the planner and policy do not exist

- [ ] **Step 3: Implement centralized safety policy**

In `safety_policy.py`, add risk-level gating and level semantics for Levels 1, 2, and 3.

- [ ] **Step 4: Implement the orchestration planning pipeline**

In `orchestrator.py`, wire together:

- source resolution
- system detection
- project scan
- project type detection
- Python resolution
- env manager selection
- device detection
- PyTorch strategy
- mirror config
- ordered `InstallAction` construction

- [ ] **Step 5: Connect the CLI to planning mode**

Update `cli.py` so `--dry-run` runs the planner and renders a useful plan summary.

- [ ] **Step 6: Re-run the planning tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add quick_env_setup/safety_policy.py quick_env_setup/orchestrator.py quick_env_setup/cli.py tests/test_orchestrator_planning.py
git commit -m "feat: add install planning and safety policy"
```

## Task 9: Implement execution, validation, and conflict analysis

**Files:**
- Create: `quick_env_setup/dependency_installer.py`
- Create: `quick_env_setup/validator.py`
- Create: `quick_env_setup/conflict_analyzer.py`
- Test: `tests/test_conflict_analyzer.py`

- [ ] **Step 1: Write failing tests for conflict classification**

Cover representative logs for:

- package conflict
- Python version incompatibility
- missing build tools
- missing dynamic library
- CUDA mismatch
- network failure

- [ ] **Step 2: Run the conflict analyzer tests**

Run: `pytest tests/test_conflict_analyzer.py -q`
Expected: FAIL because the analyzer does not exist

- [ ] **Step 3: Implement action execution and log persistence**

In `dependency_installer.py`, add subprocess-based plan action execution with:

- `shell=False`
- append-only command logging
- stop-on-first-failure behavior
- `ExecutionResult`

- [ ] **Step 4: Implement low-risk validation**

In `validator.py`, add command builders or execution helpers for:

- `python --version`
- `pip --version`
- import probes for `torch`, `numpy`, and `cv2` when appropriate
- `torch.cuda.is_available()` or MPS availability checks when relevant

- [ ] **Step 5: Implement conflict analysis**

In `conflict_analyzer.py`, map stderr/stdout evidence to `ConflictReport`.

- [ ] **Step 6: Re-run the conflict tests**

Run: `pytest tests/test_conflict_analyzer.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add quick_env_setup/dependency_installer.py quick_env_setup/validator.py quick_env_setup/conflict_analyzer.py tests/test_conflict_analyzer.py
git commit -m "feat: add execution validation and conflict analysis"
```

## Task 10: Implement run discovery, asset detection, and final reporting

**Files:**
- Create: `quick_env_setup/run_command_discoverer.py`
- Create: `quick_env_setup/asset_detector.py`
- Create: `quick_env_setup/report_generator.py`
- Test: `tests/test_asset_detector.py`
- Test: `tests/test_report_generator.py`

- [ ] **Step 1: Write failing tests for run candidate and missing asset detection**

Cover:

- README command extraction
- demo/app/inference script candidate discovery
- missing weight/config/data hints
- `.env` requirement hints

- [ ] **Step 2: Run the asset and report tests**

Run: `pytest tests/test_asset_detector.py tests/test_report_generator.py -q`
Expected: FAIL because these modules do not exist or are incomplete

- [ ] **Step 3: Implement run discovery**

In `run_command_discoverer.py`, add heuristic extraction for likely commands from filenames and README text.

- [ ] **Step 4: Implement asset detection**

In `asset_detector.py`, scan for likely missing files and extract download hint lines when possible.

- [ ] **Step 5: Implement final report generation**

In `report_generator.py`, write:

- `detected_config.json`
- `install_plan.json`
- `error_summary.txt`
- `run_candidates.txt`
- `missing_assets.txt`
- `final_report.txt`
- `agent_trace_summary.txt`

- [ ] **Step 6: Re-run the asset and report tests**

Run: `pytest tests/test_asset_detector.py tests/test_report_generator.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add quick_env_setup/run_command_discoverer.py quick_env_setup/asset_detector.py quick_env_setup/report_generator.py tests/test_asset_detector.py tests/test_report_generator.py
git commit -m "feat: add run discovery asset checks and reports"
```

## Task 11: Complete the CLI flow and interactive prompt seams

**Files:**
- Create: `quick_env_setup/interactive_prompt.py`
- Create: `quick_env_setup/utils.py`
- Modify: `quick_env_setup/cli.py`
- Modify: `quick_env_setup/orchestrator.py`

- [ ] **Step 1: Write a failing CLI behavior test**

Add a test that verifies:

- `--dry-run` returns a plan summary
- default mode selects Level 2 behavior
- `--yes` bypasses low-risk prompts through injected values

- [ ] **Step 2: Run the targeted CLI behavior test**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: FAIL on the new CLI expectation

- [ ] **Step 3: Implement prompt seam helpers**

In `interactive_prompt.py`, add functions that can be used by humans but are easy to bypass through CLI flags for agents.

- [ ] **Step 4: Finish CLI wiring**

In `cli.py` and `orchestrator.py`, ensure the normal command path can:

- plan only
- execute Level 2
- refuse Level 3 demo execution without explicit request
- emit clear terminal summaries and artifact paths

- [ ] **Step 5: Re-run the CLI planning tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add quick_env_setup/interactive_prompt.py quick_env_setup/utils.py quick_env_setup/cli.py quick_env_setup/orchestrator.py tests/test_orchestrator_planning.py
git commit -m "feat: finish CLI behavior and prompt seams"
```

## Task 12: Add agent compatibility docs and examples

**Files:**
- Create: `AGENTS.md`
- Create: `skills/codex/SKILL.md`
- Create: `skills/claude-code/SKILL.md`
- Create: `skills/copilot/instructions.md`
- Create: `skills/generic/SKILL.md`
- Create: `.qoder/rules/quick-python-environment-setup.md`
- Create: `examples/codex_prompt.md`
- Create: `examples/claude_code_prompt.md`
- Create: `examples/qoder_prompt.md`
- Create: `examples/generic_agent_prompt.md`

- [ ] **Step 1: Write a failing documentation checklist**

Create a lightweight test or manual checklist that verifies all compatibility files exist and mention:

- dry-run first
- Level 2 default
- no automatic demo execution
- CLI as source of truth

- [ ] **Step 2: Implement the compatibility documents**

Write the docs according to `REQUIREMENTS.md` and the design spec, keeping all adapters consistent with CLI behavior.

- [ ] **Step 3: Review the docs for consistency**

Check that:

- command examples match actual CLI flags
- safety language is consistent across adapters
- no adapter introduces platform-specific setup logic

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md skills .qoder examples
git commit -m "docs: add agent compatibility guides and examples"
```

## Task 13: Final verification pass for MVP

**Files:**
- Modify: any touched files if fixes are needed

- [ ] **Step 1: Run the focused unit and planning suite**

Run: `pytest tests/test_source_resolver.py tests/test_project_type_detector.py tests/test_python_version_resolver.py tests/test_pytorch_resolver.py tests/test_conflict_analyzer.py tests/test_asset_detector.py tests/test_orchestrator_planning.py tests/test_env_managers.py tests/test_report_generator.py -q`
Expected: PASS

- [ ] **Step 2: Run a dry-run against a local fixture project**

Run: `python -m quick_env_setup --source tests/fixtures/deep_learning_project --dry-run`
Expected: plan summary plus artifact generation without executing installs

- [ ] **Step 3: Run a safe non-demo execution against a trivial fixture if the test harness supports it**

Run: `python -m quick_env_setup --source tests/fixtures/package_project --env-manager venv --yes`
Expected: Level 2 behavior only, no project demo execution

- [ ] **Step 4: Fix any remaining defects found during verification**

Update code or docs based on actual failures rather than anticipated ones.

- [ ] **Step 5: Re-run the relevant verification commands**

Run the minimal subset needed to prove the fixes.
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "test: verify quick python environment setup mvp"
```

## Notes for Execution

- Keep planning pure where possible so `--dry-run` remains easy to test.
- Prefer dataclasses and small helper functions over large stateful classes.
- Treat `orchestrator.py` as workflow assembly, not as a second home for business logic.
- Keep `interactive_prompt.py` optional by design so agents can provide explicit flags and avoid blocking prompts.
- Do not execute project demo code in tests.
- Do not mutate user global pip or conda config by default.
- Keep generated stripped requirements files and reports under `.env_setup_logs/`.

## Risks to Watch

- `setup.py` parsing can turn into scope creep if it tries to be too smart.
- Cross-platform venv path handling is easy to get subtly wrong.
- `environment.yml` parsing and pip fallback behavior should stay conservative.
- README command extraction can become noisy if heuristics are too broad.
- Test expectations should assert behavior, not exact prose wording, wherever possible.

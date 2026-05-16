# Phase 2 Conflict Diagnostics Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen installation-failure diagnosis so the tool can classify more real-world failures, explain them in project-aware language, and generate sharper recovery guidance in artifacts and CLI output.

**Architecture:** Keep the current `analyze -> plan -> execute -> validate -> report` pipeline intact, but split failure handling into three clearer layers: signal extraction from raw logs, contextual classification with plan/project metadata, and recovery-advice rendering. The execution path should still produce one `ConflictReport`, but that report should carry enough structure for `error_summary.txt`, final reports, and future CLI UX to reuse the same diagnosis contract.

**Tech Stack:** Python 3.10+, standard library, `pytest`, dataclasses, regex-based log parsing, existing artifact/report pipeline

---

## File Structure

Phase 2 should stay tightly scoped around diagnostics and reporting:

- Modify: `quick_env_setup/models.py`
- Modify: `quick_env_setup/conflict_analyzer.py`
- Create: `quick_env_setup/recovery_advisor.py`
- Modify: `quick_env_setup/orchestrator.py`
- Modify: `quick_env_setup/report_generator.py`
- Modify: `quick_env_setup/cli.py`
- Create: `tests/fixtures/error_logs/python_requires.txt`
- Create: `tests/fixtures/error_logs/no_matching_distribution.txt`
- Create: `tests/fixtures/error_logs/network_dns_failure.txt`
- Create: `tests/fixtures/error_logs/network_ssl_failure.txt`
- Create: `tests/fixtures/error_logs/pytorch_cuda_mismatch.txt`
- Create: `tests/fixtures/error_logs/missing_build_tools_windows.txt`
- Modify: `tests/test_conflict_analyzer.py`
- Create: `tests/test_recovery_advisor.py`
- Modify: `tests/test_orchestrator_planning.py`
- Modify: `tests/test_report_generator.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md`

The new `recovery_advisor.py` module is the main decomposition choice in this phase. `conflict_analyzer.py` should keep responsibility for recognizing failure type and extracting evidence. Recovery-template logic should move out of the classifier so category detection stays readable and adding new advice variants does not turn the analyzer into a long conditional file.

## Scope

This phase should improve:

- category coverage for common resolver, Python-version, network, CUDA, and native-build failures
- scenario-specific recovery suggestions instead of generic next steps
- structured `ConflictReport` fields that can drive both text artifacts and future UX
- `error_summary.txt` readability
- final report next steps when setup fails

This phase should not include:

- automatic dependency-conflict repair
- running project demo code
- Poetry or Pipenv support
- ROCm support
- large CLI redesign

## Task 1: Expand the conflict-report contract for richer diagnosis

**Files:**
- Modify: `quick_env_setup/models.py`
- Modify: `tests/test_conflict_analyzer.py`

- [ ] **Step 1: Write the failing model and analyzer tests**

Add tests that assert `ConflictReport` can carry richer data without breaking the current happy path. Cover fields such as:

- `category`
- `summary`
- `evidence`
- `recommendations`
- `confidence`
- `recovery_tags`
- `related_packages`
- `suggested_python_versions`

The tests should verify missing optional fields still serialize cleanly and existing callers can continue to use the report.

- [ ] **Step 2: Run the focused test to confirm the new fields do not exist yet**

Run: `pytest tests/test_conflict_analyzer.py -q`
Expected: FAIL with dataclass construction or attribute assertions because the richer report contract is not implemented yet

- [ ] **Step 3: Extend `ConflictReport` conservatively**

In `quick_env_setup/models.py`, extend `ConflictReport` with optional structured fields, for example:

```python
@dataclass(slots=True)
class ConflictReport:
    category: ConflictCategory
    summary: str
    evidence: list[str]
    recommendations: list[str]
    confidence: float = 0.0
    recovery_tags: list[str] = field(default_factory=list)
    related_packages: list[str] = field(default_factory=list)
    suggested_python_versions: list[str] = field(default_factory=list)
```

Keep defaults safe so older call sites do not need immediate changes.

- [ ] **Step 4: Re-run the focused analyzer tests**

Run: `pytest tests/test_conflict_analyzer.py -q`
Expected: PASS for model-shape assertions while behavior tests that depend on richer analysis may still be pending

- [ ] **Step 5: Commit**

```bash
git add quick_env_setup/models.py tests/test_conflict_analyzer.py
git commit -m "feat: extend conflict report structure"
```

## Task 2: Separate signal extraction from recovery guidance

**Files:**
- Modify: `quick_env_setup/conflict_analyzer.py`
- Create: `quick_env_setup/recovery_advisor.py`
- Create: `tests/fixtures/error_logs/python_requires.txt`
- Create: `tests/fixtures/error_logs/no_matching_distribution.txt`
- Create: `tests/fixtures/error_logs/network_dns_failure.txt`
- Create: `tests/fixtures/error_logs/network_ssl_failure.txt`
- Create: `tests/fixtures/error_logs/pytorch_cuda_mismatch.txt`
- Create: `tests/fixtures/error_logs/missing_build_tools_windows.txt`
- Modify: `tests/test_conflict_analyzer.py`
- Create: `tests/test_recovery_advisor.py`

- [ ] **Step 1: Add failing fixture-driven tests for representative scenarios**

Create fixture log snippets and tests that cover at least these cases:

- package resolver conflict with pinned versions
- `Requires-Python` mismatch
- `No matching distribution found` caused by interpreter or platform mismatch
- DNS / index reachability failure
- SSL certificate failure
- PyTorch / CUDA build mismatch
- missing MSVC or native build tools

For each case, assert both category and scenario-specific recovery hints. Example expectations:

- Python mismatch suggests `3.8` or `3.10` style fallback candidates when discoverable
- DNS failure recommends retry / mirror, not Python downgrade
- CUDA mismatch recommends matching `torch/torchvision/torchaudio` builds

- [ ] **Step 2: Run the targeted diagnostics tests**

Run: `pytest tests/test_conflict_analyzer.py tests/test_recovery_advisor.py -q`
Expected: FAIL because the analyzer still returns mostly generic recommendations and `recovery_advisor.py` does not exist

- [ ] **Step 3: Refactor the analyzer into a clearer pipeline**

In `quick_env_setup/conflict_analyzer.py`, keep category matching but introduce explicit helper stages such as:

- `_detect_category(...)`
- `_collect_evidence(...)`
- `_extract_related_packages(...)`
- `_extract_python_version_hints(...)`

The analyzer should return a richer `ConflictReport`, but it should not own long-form recovery prose.

- [ ] **Step 4: Implement recovery templates in `recovery_advisor.py`**

Add a dedicated function such as:

```python
def build_recovery_guidance(report: ConflictReport) -> ConflictReport:
    ...
```

or:

```python
def enrich_conflict_report(report: ConflictReport) -> ConflictReport:
    ...
```

Use the structured fields to attach more specific recommendations by scenario. Prefer deterministic templates over “AI-like” freeform text.

- [ ] **Step 5: Re-run the diagnostics suite**

Run: `pytest tests/test_conflict_analyzer.py tests/test_recovery_advisor.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add quick_env_setup/conflict_analyzer.py quick_env_setup/recovery_advisor.py tests/fixtures/error_logs tests/test_conflict_analyzer.py tests/test_recovery_advisor.py
git commit -m "feat: add structured recovery guidance for install failures"
```

## Task 3: Thread install-plan context into failure analysis

**Files:**
- Modify: `quick_env_setup/orchestrator.py`
- Modify: `tests/test_orchestrator_planning.py`

- [ ] **Step 1: Write failing orchestration tests for context-aware diagnosis**

Add tests proving that failed setup output can be interpreted using known plan context, for example:

- when `plan.python_requirement.version == "3.10"` and the log shows `Requires-Python >=3.11`, the report should mention upgrading the environment Python version
- when `plan.pytorch_strategy.variant == "cpu"`, a CUDA mismatch should recommend CPU fallback rather than only generic CUDA advice
- when a China mirror is enabled and a network failure occurs, the summary should not suggest mirror adoption as the first step

- [ ] **Step 2: Run the orchestrator-focused tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: FAIL because `execute_install_plan()` does not yet pass plan context into failure analysis

- [ ] **Step 3: Update the execution failure path**

Modify `quick_env_setup/orchestrator.py` so failed execution calls a context-aware path, for example:

```python
conflict_report = analyze_install_error(
    stdout=execution_result.stdout_tail,
    stderr=execution_result.stderr_tail,
    plan=plan,
)
```

If you do not want `analyze_install_error()` to import the whole plan, pass a slimmer context object derived from it. Keep the API explicit and testable.

- [ ] **Step 4: Re-run orchestrator tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add quick_env_setup/orchestrator.py tests/test_orchestrator_planning.py
git commit -m "feat: use install context in failure analysis"
```

## Task 4: Improve `error_summary.txt` and failed final-report guidance

**Files:**
- Modify: `quick_env_setup/conflict_analyzer.py`
- Modify: `quick_env_setup/orchestrator.py`
- Modify: `quick_env_setup/report_generator.py`
- Modify: `tests/test_orchestrator_planning.py`
- Modify: `tests/test_report_generator.py`

- [ ] **Step 1: Write failing report-generation tests**

Add tests that verify failure artifacts are easier to scan. Assert that `error_summary.txt` contains stable sections such as:

- `Category:`
- `Summary:`
- `Why this likely happened:`
- `Evidence:`
- `Recommended next steps:`

Also add a failed-report test ensuring `final_report.txt` points the user toward diagnosis and recovery, not only generic “review error summary” wording.
Because the current failure path returns before `generate_final_report()` runs, at least one test in `tests/test_orchestrator_planning.py` should assert that failed execution now persists both `error_summary.txt` and a compact `final_report.txt` with aligned next steps.

- [ ] **Step 2: Run report tests to confirm the output shape is not there yet**

Run: `pytest tests/test_report_generator.py tests/test_conflict_analyzer.py -q`
Expected: FAIL because current text output is simpler and does not include the richer sections

- [ ] **Step 3: Update rendering helpers and final-report next steps**

Enhance the conflict renderer so it can emit a stable, compact diagnostic block. Then update `quick_env_setup/orchestrator.py` and `report_generator.py` so failed runs also produce a minimal `FinalReport` artifact and reference:

- the detected category
- the most actionable first recovery step
- when relevant, Python version or CUDA alignment guidance

Keep the output plain text and artifact-friendly.

- [ ] **Step 4: Re-run the report-focused tests**

Run: `pytest tests/test_report_generator.py tests/test_conflict_analyzer.py -q`
Expected: PASS

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add quick_env_setup/conflict_analyzer.py quick_env_setup/orchestrator.py quick_env_setup/report_generator.py tests/test_orchestrator_planning.py tests/test_report_generator.py tests/test_conflict_analyzer.py
git commit -m "feat: improve failure artifacts and report guidance"
```

## Task 5: Surface better failure summaries in CLI output and refresh docs

**Files:**
- Modify: `quick_env_setup/cli.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md`
- Modify: `tests/test_orchestrator_planning.py`

- [ ] **Step 1: Write failing CLI and docs-oriented tests**

Add or extend CLI tests so a failed execution prints a concise summary with:

- failure category
- one-line explanation
- artifact directory or `error_summary.txt` path

Do not dump the entire diagnostics block to stdout.

- [ ] **Step 2: Run the CLI-focused tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: FAIL because the CLI currently only surfaces the older, thinner warning path

- [ ] **Step 3: Update CLI failure rendering and documentation**

Modify `quick_env_setup/cli.py` so failed runs print a short summary derived from the richer report contract. Then refresh:

- `README.md` to explain the stronger failure-diagnosis behavior
- `docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md` to record that conflict diagnosis has moved beyond basic-category classification

- [ ] **Step 4: Re-run the focused CLI suite and full tests**

Run: `pytest tests/test_orchestrator_planning.py -q`
Expected: PASS

Run: `pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add quick_env_setup/cli.py README.md docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md tests/test_orchestrator_planning.py
git commit -m "docs: describe enhanced failure diagnosis behavior"
```

## Task 6: Final verification and release checkpoint

**Files:**
- Modify: `README.md` if final command examples drifted during implementation
- Modify: `docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md` if the final status wording needs tightening

- [ ] **Step 1: Run the full suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 2: Run a dry-run sanity check**

Run: `python -m quick_env_setup --source tests/fixtures/deep_learning_project --dry-run`
Expected: PASS with unchanged planning behavior

- [ ] **Step 3: Run at least one failure-focused regression path**

Use an existing test seam or fixture-driven invocation to confirm the richer diagnostics render into `error_summary.txt` and the CLI summary points to the artifact path. Prefer a deterministic test seam over a flaky network-dependent reproduction.

- [ ] **Step 4: Review docs for contract drift**

Confirm `README.md`, `AGENTS.md`, and the MVP status doc still describe the current behavior accurately. Only edit `AGENTS.md` if the CLI safety contract actually changed.

- [ ] **Step 5: Commit and publish through the active repo workflow**

```bash
git add README.md docs/superpowers/specs/2026-05-16-quick-python-environment-setup-mvp-status.md
git commit -m "test: verify phase 2 conflict diagnostics enhancements"
```

If this work is being delivered on a review branch, push that branch and open or update the corresponding PR. If the repository is intentionally using direct-to-main delivery for documentation-only work, publish with the repo's current convention.

## Notes for Execution

- Stay disciplined about not broadening the scope into package-manager support or demo execution.
- Prefer fixture-driven logs over brittle command reproductions for most diagnosis tests.
- Keep the failure contract deterministic: a given stderr snippet and install context should produce the same category and first-step recommendation every time.
- Preserve backwards compatibility for existing report artifacts unless the new structure clearly improves readability.

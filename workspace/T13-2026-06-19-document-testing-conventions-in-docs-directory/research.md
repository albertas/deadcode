# Research Findings

Scope: the `tests/` directory, the `BaseTestCase` helper, `tests/files/`
fixtures, determinism/parallel-safety practices, the `Makefile` / `Justfile` /
`pyproject.toml` automation, and existing testing docs under `docs/`.

## Q1: How is `tests/` structured, and what naming patterns are used?

### Findings
- **Subdirectories** (mirror the package areas): `tests/actions/`,
  `tests/cli_args/`, `tests/code_item/`, `tests/fix/`, `tests/nested_scope/`,
  `tests/noqa/`, `tests/utils/`, `tests/visitor/`, plus `tests/files/` (fixture
  inputs, not test modules).
- **Top-level test modules** (6, directly under `tests/`):
  `tests/test_deadcode.py`, `tests/test_output.py`, `tests/test_imports.py`,
  `tests/test_accurate_usage_detection.py`, `tests/test_line_number_detection.py`,
  `tests/test_variable_parsing_from_ast_dump.py`.
- **File names**: all `test_<snake_case_subject>.py` — e.g.
  `tests/fix/test_class_def.py`, `tests/actions/test_merge_overlaping_file_parts.py`,
  `tests/cli_args/test_ignore_names_in_files.py`.
- **Class names**: dominant `Test<DescriptiveName>` plus a minority
  `<DescriptiveName>Tests` — e.g. `tests/fix/test_assign.py:11`
  `TestAssignmentExpressionRemoval`; `tests/cli_args/test_parsing.py:11`
  `CommandLineArgParsingTests`; `tests/test_deadcode.py:13`
  `DeadCodeIntegrationTests`; `tests/test_deadcode.py:82` `CliEntrypointTests`.
- **Method names**: all `test_<behavior_in_snake_case>` — e.g.
  `tests/test_deadcode.py:19` `test_unused_variable_name_found_successfully`;
  `tests/code_item/test_code_item.py:8` `test_code_item_comparison_with_a_string`;
  `tests/visitor/test_find_unused_code_visitor.py:16` `test_async_function_def`.
- **`__init__.py`**: only in `tests/cli_args/__init__.py` and
  `tests/utils/__init__.py` (both empty). Other subdirs have none.
  `tests/files/subdir/another_subdir/__init__.py` is a fixture, not a marker.
- **`conftest.py`**: none anywhere under `tests/`.
- **Style**: all tests are `unittest`-style classes; no plain pytest functions.
  ~40 of ~50 classes subclass `BaseTestCase`; ~10 subclass `unittest.TestCase`
  directly.

## Q2: What does `BaseTestCase` provide, and how is it used / bypassed?

### Findings
- Defined at `deadcode/utils/base_test_case.py:10` (extends
  `unittest.TestCase`). Provides:
  - `patch(path)` helper that auto-registers cleanup (`base_test_case.py:15-18`).
  - `setUp` (`base_test_case.py:37-57`) patches the I/O/discovery seams:
    `find_python_filenames` in `deadcode.cli` (returns `self.files.keys()`),
    `open` in `find_unused_code_visitor`, `fix_unused_code_visitor`, and
    `actions.fix_or_show_unused_code`, `os.remove`, and
    `parse_arguments.parse_pyproject_toml` (returns `{}`). Creates fresh
    `self.args = Args()` and `self.updated_files = {}`.
  - `_read_file_side_effect` (`base_test_case.py:23-35`) serves `self.files`
    content through `fix_indent`, capturing writes into `self.updated_files`.
  - Assertions `assertFiles(files, removed=None)` (`base_test_case.py:59-85`) and
    `assertUpdatedFiles(expected)` (`base_test_case.py:87-96`).
- **`files` input pattern**: tests set `self.files = {'foo.py': "..."}` (usually
  inside the test method), call `main([...])`, then assert. Examples:
  `tests/fix/test_assign.py:13,20,26`; `tests/fix/test_class_def.py:12-22`
  (empty `assertFiles({})` == file fully removed via `os.remove` mock);
  `tests/noqa/test_noqa_comments.py:9,16,18`;
  `tests/fix/test_unused_imports_in_a_single_file.py:11-39`.
- Some `BaseTestCase` subclasses never set `files`/call `main()`; they call
  lower-level functions directly — e.g.
  `tests/actions/test_merge_overlaping_file_parts.py:10` (calls
  `merge_overlaping_file_parts`, `does_overlap`); `tests/cli_args/test_parsing.py:11`
  (calls `parse_arguments`). They inherit `BaseTestCase` for `self.args` / `patch`.
- **Deliberate bypasses (plain `unittest.TestCase`)** — pure logic or real I/O,
  no mocking needed:
  - `tests/code_item/test_code_item.py:7` — `CodeItem` behavior in isolation.
  - `tests/visitor/test_utils.py:18,32,46` — AST utils / logging collections.
  - `tests/utils/test_fix_indent.py:6`, `tests/utils/test_add_colors_to_diff.py:7`,
    `tests/utils/test_nested_scopes.py:8`, `tests/visitor/test_lines.py:7` — pure
    utility functions.
  - `tests/visitor/test_fix_unused_code_visitor.py:10` — `TestConvert1dPartTo2d`.
  - `tests/test_deadcode.py:13` `DeadCodeIntegrationTests` and
    `tests/test_deadcode.py:82` `CliEntrypointTests` — real filesystem (see Q4).
- `tests/test_deadcode.py` is mixed: `DeadCodeTests(BaseTestCase)` (line ~74)
  uses the mock layer with inline `self.files`; the two integration classes use
  real files.
- **Temp-dir variant**: `tests/actions/test_find_python_filenames.py:8` and
  `tests/cli_args/test_exclude.py:8` subclass `BaseTestCase`, call
  `super().setUp()`, then create `tempfile.TemporaryDirectory()` and write real
  files (`__init__`-level lines 9-21 / 9-20). They call `find_python_filenames`
  directly (real `os.walk`), bypassing the `open`/discovery mocks in practice.

## Q3: What fixture data exists under `tests/files/`, and how referenced?

### Findings
- Fixture files (each a small unused/used code sample):
  - `tests/files/classes.py` — `UnusedClass`, `AnotherUnusedClass` (unused),
    `ThisClassIsUsed` (instantiated).
  - `tests/files/variables.py` — three unused module vars + `THIS_ONE_IS_USED`.
  - `tests/files/functions.py` — `unused_function`, `this_one_is_used` (called),
    `another_unused_function`, nested `this_is_unused_closure`.
  - `tests/files/subdir/one_more_file.py` — single unused function.
  - `tests/files/subdir/another_subdir/__init__.py` — `UNUSED_VARIABLE = 123`.
- **On-disk reference (real paths)**: only the integration classes in
  `tests/test_deadcode.py` pass real `tests/files/...` paths to `main()` —
  `tests/test_deadcode.py:20,32,44,59-60`.
- **Inline string-dict reference**: the dominant style across all other modules.
  `BaseTestCase.files: dict[str,str]` (`base_test_case.py:11`) is served via the
  patched `open`. Examples: `tests/test_output.py:97-104` (key looks like a
  `tests/files/` path but content is inline); `tests/test_deadcode.py:76`
  (inline invalid content); `tests/fix/test_unused_imports_in_a_multiple_files.py:22`;
  `tests/fix/test_scope.py:15`; `tests/test_imports.py:8`.
- **Temporary directories**: `tests/actions/test_find_python_filenames.py:11`
  and `tests/cli_args/test_exclude.py:11` build real trees in
  `tempfile.TemporaryDirectory()` with `addCleanup`.

## Q4: What keeps the suite deterministic and parallel-safe?

### Findings
- **Sorted directory walk**: `deadcode/actions/find_python_filenames.py:24` —
  `paths += sorted(str(p) for p in path.glob('*'))`. The LIFO `paths` stack
  (`paths.pop()`, line 14) plus the sort make traversal order independent of
  filesystem entry order / `PYTHONHASHSEED`.
- **Sorted output**: `deadcode/visitor/find_unused_code_visitor.py:171` —
  final sort by `(item.filename, item.name_line or 0)`; intermediate per-category
  sort by `item.name.lower()` at `deadcode/visitor/ignore.py:41`; merge-overlap
  ordering at `deadcode/actions/merge_overlaping_file_parts.py:95`.
- **cwd anchoring for integration tests**: `tests/test_deadcode.py:10`
  `REPO_ROOT = Path(__file__).parents[1]`; `setUp` at lines 14-17 saves
  `Path.cwd()`, `os.chdir(REPO_ROOT)`, and `self.addCleanup(os.chdir,
  self._prev_cwd)`. `CliEntrypointTests.setUp` (lines 83-86) repeats this. The
  cleanup restores cwd per test even on failure, so xdist workers don't leak cwd.
- **Config isolation**: `BaseTestCase.setUp` mocks `parse_pyproject_toml` to
  return `{}` (`base_test_case.py:54-55`), decoupling unit tests from the repo's
  real `[tool.deadcode]` block.
- **No real FS in most tests**: the `BaseTestCase` mock layer means most tests
  never touch disk, which is inherently parallel-safe.
- **No `PYTHONHASHSEED` pinning and no xdist-specific fixtures** (e.g.
  `worker_id`) exist; determinism comes from the explicit sorts and cwd cleanup.
  `pytest-xdist` is listed at `pyproject.toml:32`.

## Q5: How are tests/coverage/lint/type/complexity defined and invoked?

### Findings
- **Makefile** (`Makefile`):
  - `test` (`Makefile:20-21`): `.venv/bin/pytest -n "$(nproc --ignore=1)" -vv
    $(PYTEST_ME_PLEASE)`.
  - `lint` (`Makefile:23-24`): `ruff check deadcode tests`.
  - `format` (`Makefile:39-40`): `ruff format deadcode tests`.
  - `mypy` (`Makefile:29-30`): `mypy deadcode`.
  - `deadcode` (`Makefile:32-33`): `deadcode deadcode tests -v` (self-check).
  - `audit` (`Makefile:42-43`): `pip-audit`.
  - `check` (`Makefile:5`): `test lint mypy audit deadcode`.
  - `fix` (`Makefile:6` and overridden `Makefile:26`): `format fixlint`.
  - No dedicated complexity target; complexity is a ruff rule (see below).
- **Justfile** (`Justfile`):
  - `test *args` (`Justfile:10-11`): `uv run pytest -n "$(nproc --ignore=1)"`.
  - `format` / `lint` / `typecheck` (`Justfile:13-20`).
  - `check-format` / `check-lint` / `check-complexity` / `check-typecheck`
    (`Justfile:22-32`); `check-complexity` runs `ruff check --select C901`.
  - `check` (`Justfile:34`): `check-format check-lint check-complexity
    check-typecheck test`.
  - `sync` (`Justfile:6-8`) and `lifecycle` (`Justfile:1-4`).
- **pyproject.toml** settings:
  - Pytest `addopts` (`pyproject.toml:215`): `--cov=deadcode --no-cov-on-fail
    --cov-fail-under=95.0`.
  - Coverage (`pyproject.toml:217-219`): `source = ["deadcode"]`, omits
    `deadcode/utils/base_test_case.py`.
  - Ruff (`pyproject.toml:60-160`): `line-length = 120`, `select = ["ALL"]` with
    ~70 ignores; `mccabe.max-complexity = 8` (`pyproject.toml:71`); per-file
    `tests/*` ignores `S101, PT009, ANN201, SLF001, D` (`pyproject.toml:153-160`).
  - MyPy (`pyproject.toml:163-171`): `strict = true`, `python_version = "3.11"`,
    excludes `build/dist/.venv`.
  - `[tool.deadcode]` (`pyproject.toml:179-206`): self-config; ignores names,
    ignores `deadcode/utils/base_test_case.py`, excludes `tests`.

## Q6: What testing content already exists in `docs/`, and how organized?

### Findings
- `docs/` holds 8 Markdown guides plus `_static/` assets:
  `architecture.md`, `cli-and-configuration.md`, `data-types.md`,
  `fix-and-output.md`, `index.md`, `invocation.md`, `overview.md`,
  `testing-and-tooling.md`, `unused-detection-and-ignoring.md`,
  `visitor-layer.md`.
- **`docs/testing-and-tooling.md`** already documents (203 lines): test-suite
  organization by area and top-level modules; `tests/files/` fixtures;
  `BaseTestCase` setUp/mocking/assertions with `file:line` refs; tests outside
  `BaseTestCase`; deterministic-testing section (sorted walk, config mocking,
  temp-dir unit tests, e2e cwd anchoring); Make/Just recipes; pyproject
  config (pytest/ruff/mypy/`[tool.deadcode]`); ruff policy ignores; a
  contributor workflow.
- **`docs/index.md`** is the hub: a "Documentation index" (lines 9-17) links to
  every guide, including `[Testing & tooling](testing-and-tooling.md)` (line 17).
  Each guide carries a one-line summary.
- **Cross-linking convention**: docs reference each other and the repo by
  relative links — e.g. `testing-and-tooling.md:3` links back to `index.md`;
  `index.md:7` links to `../README.md`. Docs prefer `file:line` references and
  cite `pyproject.toml` for numeric gates rather than copying numbers.

## Cross-Cutting Observations
- The repo already has a mature, accurate testing doc
  (`docs/testing-and-tooling.md`) indexed from `docs/index.md`; the conventions
  it describes match the code (verified against `base_test_case.py`,
  `find_python_filenames.py:24`, `test_deadcode.py:10-17`).
- Two-tier test strategy: fast mock-backed unit tests via `BaseTestCase` (no
  disk) and a small set of real-filesystem integration tests anchored to
  `REPO_ROOT`. A third hybrid uses `BaseTestCase` + temp dirs to exercise real
  `os.walk`.
- Determinism is achieved structurally (explicit sorts + cwd cleanup), not via
  seed pinning; this is what makes `-n auto` xdist runs reproducible.
- `Makefile` and `Justfile` both run `pytest -n "$(nproc --ignore=1)"`, keeping
  parallel behavior identical across the two runners. They diverge on extras:
  Makefile adds `audit` + self-`deadcode`; Justfile adds `check-complexity`.

## Open Areas
- Per-file line numbers for some agent-reported references (e.g. exact `setUp`
  spans in the two temp-dir test modules) were sampled, not exhaustively
  re-read; the cited anchor lines were verified for `test_deadcode.py` and
  `base_test_case.py`.
- The questions are about existing conventions only; no gaps in coverage of the
  asked topics were found in the codebase.

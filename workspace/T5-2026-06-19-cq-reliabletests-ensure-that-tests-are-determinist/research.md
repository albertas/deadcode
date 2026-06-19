# Research Findings

## Q1: How is the test suite invoked and configured (runner commands, parallelism, coverage), and where?

### Findings
- **Runner with parallelism + coverage** — `Justfile:10-11`: `test *args: sync` then
  `uv run pytest -n "$(nproc --ignore=1)" {{args}}`. The `-n` flag is **pytest-xdist**
  parallelism, sized to `nproc --ignore=1` (all CPUs minus one), so tests run across
  multiple worker processes by default.
- **pytest-xdist + pytest-cov are declared deps** — `pyproject.toml:33-34` (`pytest-cov`,
  `pytest-xdist`) under the `test` optional-dependency group.
- **Coverage options** — `pyproject.toml:210-211`: `[tool.pytest.ini_options]`
  `addopts = "--cov=deadcode --no-cov-on-fail --cov-fail-under=95.0"`. Coverage always
  runs (addopts is unconditional), gated at 95%, suppressed on failure.
- **Coverage source/omit** — `pyproject.toml:213-215`: `source = ["deadcode"]`,
  `omit = ["deadcode/utils/base_test_case.py"]`. `[tool.coverage.report]` (216-219) keeps
  defaults (honors `# pragma: no cover`).
- **Second, divergent runner** — `Makefile:18-19`: `test: .venv` →
  `.venv/bin/pytest -vv $(PYTEST_ME_PLEASE)`. No `-n` parallelism, no explicit coverage
  flags (coverage still applied via addopts). `-vv` verbose. `Makefile:1` `.PHONY` declares
  it. `check: test lint mypy audit deadcode` (`Makefile:3`).
- **Justfile `check`** — `Justfile:34`: `check: check-format check-lint check-complexity
  check-typecheck test`. Every recipe depends on `sync` (`Justfile:6-8`) which runs
  `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]`.
- No `pytest.ini`/`tox.ini`/`setup.cfg`; all pytest config is in `pyproject.toml`.

## Q2: How does the shared base test case set up mocks, what assertion helpers does it provide, which modules inherit vs define own setup?

### Findings
- **Class** `BaseTestCase(TestCase)` — `deadcode/utils/base_test_case.py:10`. Class attr
  `files: Dict[str, str] = {}` (`:11`), `maxDiff = None` (`:13`).
- **`patch()` helper** (`:15-18`) wraps `unittest.mock.patch` and registers `addCleanup`.
- **`setUp` mocks** (`:37-54`):
  - `:38` resets `self.updated_files = {}` each test.
  - `:40-41` patches `deadcode.cli.find_python_filenames` → returns `list(self.files.keys())`.
  - `:43-44` patches `deadcode.visitor.find_unused_code_visitor.open` → `_read_file_side_effect`.
  - `:46-47` patches `deadcode.visitor.fix_unused_code_visitor.open` → same.
  - `:49-50` patches `deadcode.actions.fix_or_show_unused_code.open` → same.
  - `:52` patches `deadcode.actions.fix_or_show_unused_code.os.remove` (MagicMock).
  - `:54` `self.args = Args()`.
- **File-read mock** `_read_file_side_effect` (`:23-35`) serves `self.files[filename]` via
  `fix_indent`, wiring `.read()`, `.readlines()`, and a `.write` side effect
  (`cache_file_content`, `:27-29`) that captures writes into `self.updated_files`.
- **`_get_filenames`** (`:20-21`) returns `list(self.files.keys())`.
- **Assertion helpers**: `assertFiles(files, removed=None)` (`:56-82`) — compares removed
  filenames (from `os.remove` mock calls), unchanged + updated file contents, and the full
  key set. `assertUpdatedFiles(expected_updated_files)` (`:84-93`). Note: the locator agent
  found `assertUpdatedFiles` is **never called** by any test; only `assertFiles` is used.
- **Inheritance map** (from locator agent): the large majority of test classes subclass
  `BaseTestCase`. Classes that subclass plain `unittest.TestCase` instead:
  `tests/test_deadcode.py` `DeadCodeIntegrationTests`:9 and `CliEntrypointTests`:73;
  `tests/code_item/test_code_item.py:7`; `tests/utils/test_add_colors_to_diff.py:7`,
  `test_fix_indent.py:6`, `test_flatten_lists.py:6`, `test_nested_scopes.py:8`;
  `tests/visitor/test_find_unused_code_visitor.py:57` (`TestVisitorDirectUnits`),
  `test_fix_unused_code_visitor.py:10`, `test_utils.py:18/32/46`, `test_lines.py:7`.
- **Only one `setUp` override** in the whole suite: `tests/cli_args/test_parsing.py:12`
  (a `BaseTestCase` subclass). No `setUpClass` anywhere.
- **Empty test files**: `tests/cli_args/test_ignore_names_in_files.py`, `test_no_color.py`,
  `test_quiet.py`, `test_count.py`, `test_verbose.py` (zero content).
- **`test_variable_parsing_from_ast_dump.py:11`** subclasses `BaseTestCase` but body is `pass`.

## Q3: Which test modules touch the live filesystem / depend on cwd, and how do they locate inputs?

### Findings
- **`tests/test_deadcode.py` `DeadCodeIntegrationTests`** (plain `TestCase`, no mocks) reads
  real files via hardcoded relative paths passed to `main()`:
  `:11` `'tests/files/variables.py'`, `:23` `'tests/files/functions.py'`,
  `:35` `'tests/files/classes.py'`, `:48-54` `'tests/files/variables.py'` +
  nonexistent `'deadcode/tests/files/variables.py'`.
- **`tests/test_deadcode.py` `CliEntrypointTests.test_module_runs_as_script`** (`:73-77`):
  `runpy.run_module('deadcode.cli', run_name='__main__')` with argv containing real relative
  path `'deadcode/data_types.py'` (`:75`).
- **`tests/actions/test_find_python_filenames.py`** — subclasses `BaseTestCase` but imports
  `find_python_filenames` **directly** (`:1`), so the `deadcode.cli.find_python_filenames`
  mock does **not** intercept it; calls hit the real filesystem. Real relative paths:
  `:7` `'deadcode/cli.py'`, `:12` `'deadcode/.'`, `:23` `'deadcode'`,
  `:33` `'path_does_not_exist'`, `:40` `'deadcode/cli.py'`.
- **`tests/cli_args/test_exclude.py`** — same bypass pattern: imports `find_python_filenames`
  directly (`:2`); real paths `:7` `'deadcode/.'`, `:18` `'deadcode/.'`, `:13/:22`
  `'deadcode/cli.py'`.
- **cwd dependency is implicit**: every real path is a bare relative string literal anchored
  to nothing (no `__file__`, no `Path(__file__).parent`, no `os.getcwd`/`chdir`/`Path.cwd`).
  They only resolve when cwd == repo root.
- **`tests/files/` sample dir** holds: `variables.py`, `functions.py`, `classes.py`,
  `subdir/one_more_file.py`, `subdir/another_subdir/__init__.py`. Only the integration tests
  above open them from disk; other tests reference filenames only as `self.files` dict keys
  (labels), e.g. `tests/test_output.py:98,121` uses key `'tests/files/variables.py'` with
  no disk access.

## Q4: Where do I/O boundaries occur in `deadcode/`, and does any code contact the network?

### Findings
- **Directory walking** — `deadcode/actions/find_python_filenames.py`: `:22` `path.is_file()`,
  `:24` `path.is_dir()`, `:25` `path.glob('*')` (only one directory level, stack/LIFO walk),
  `:26` `path.exists()`. No `os.walk`, `os.listdir`, `glob` module, or `rglob` anywhere.
- **Reading source files** — `deadcode/visitor/find_unused_code_visitor.py:102`
  `with open(file_path) as f:`, `:107` `f.read()`. Second independent read pass in
  `deadcode/visitor/fix_unused_code_visitor.py:102` / `:107`.
- **Read/write/remove during fix** — `deadcode/actions/fix_or_show_unused_code.py`:
  `:41` `open(filename)` + `readlines()`, `:48` `open(filename, 'r')` (dry-run diff),
  `:61` `open(filename, 'w')`, `:63` `f.write(...)`, `:65` `os.remove(filename)` when result
  is empty.
- **Config discovery/read** — `deadcode/actions/parse_arguments.py`: `:219`
  `pyproject_toml_filename = 'pyproject.toml'` (cwd-relative, **no upward search**),
  `:220` `os.path.isfile(...)` (returns `{}` if absent), `:223` `open(..., 'rb')`,
  `:224` `tomllib.load(f)` (stdlib `tomllib` ≥3.11 at `:7`, third-party `tomli` at `:9`).
- **Network**: a full search for `requests`/`urllib`/`socket`/`http` (import and `from`)
  across all `.py` returned **zero** matches in source and tests. No network or external
  service contact anywhere.

## Q5: What sources of non-determinism exist in runtime data structures and output?

### Findings
- **Primary source — unsorted filesystem walk**: `find_python_filenames.py:25`
  `paths += [str(p) for p in path.glob('*')]`. `Path.glob('*')` returns entries in
  filesystem/OS order (not sorted); combined with `paths.pop()` (LIFO at `:14`) the file
  **discovery order is OS/filesystem-dependent**. The resulting `filenames` list is **not
  sorted** and is consumed directly as `FindUnusedCodeVisitor.filenames`
  (`find_unused_names.py:14`, iterated `find_unused_code_visitor.py:101`).
- **`used_names` is a `set`** (`LoggingSet`, `find_unused_code_visitor.py:66`;
  `visitor/utils.py:77-86`), and `|=` union at `:354`. However it is used **only for
  membership tests** (`in`/`not in`), never iterated for output → no output effect.
- **Per-type sorting** — `deadcode/visitor/ignore.py:40-42`: unused items filtered then
  `.sort(key=lambda item: item.name.lower())` (alphabetical, case-insensitive,
  deterministic).
- **Final output re-sorted** — `find_unused_code_visitor.py:156-169`: `chain(...)` of all
  unused-item lists then `sorted(unused_code, key=lambda item: (item.filename, item.name_line
  or 0))`. This **overwrites** the alphabetical order; key is `(Path, lineno-or-0)`. Stable
  and deterministic for a fixed set of paths (Path compares as strings per-OS).
- **`fix_or_show_unused_code.py:28-34`** builds a `defaultdict(list)` from the already-sorted
  `unused_items`, so `.items()` iteration follows sorted insertion order (deterministic).
- **`noqa.py:55-63`** `defaultdict(set)` — set values used only for membership tests, never
  iterated for output.
- **`nested_scopes.py:18`** `_scopes: dict[str|CodeItem, ...]`; `:57-60` iterates
  `current_scope.keys()` in **insertion order** (AST traversal order, deterministic).
  `CodeItem.__hash__` = `hash(self.name)` (`code_item.py:140`) affects dict bucket placement
  (subject to `PYTHONHASHSEED`) but not `list(keys())` order.
- **Module-level `set` constants** `IGNORED_VARIABLE_NAMES`, `PYTEST_FUNCTION_NAMES`,
  `PYTEST_METHOD_NAMES` (`ignore.py:9-21`) — membership tests only, never iterated for output.
- Net: the one place output ordering could vary across machines is the unsorted
  `glob('*')` discovery, but the final `sorted(...)` by `(filename, name_line)` normalizes
  the emitted order for a given path set.

## Q6: How are fixtures organized/shared, and is there shared mutable state persisting across tests?

### Findings
- **On-disk fixtures**: `tests/files/` (5 files, see Q3). Consumed only by the integration
  tests in `tests/test_deadcode.py`.
- **In-memory fixtures**: the dominant mechanism is `self.files = {...}` reassigned at the
  top of each test body in `BaseTestCase` subclasses (e.g. `tests/cli_args/test_fix.py:9`,
  `tests/fix/test_assign.py:13`, `tests/cli_args/test_ignore_names.py:7`). Maps a filename
  key → source string.
- **No `conftest.py`** anywhere in `tests/` or repo root (only inside `.venv`). No
  `@pytest.fixture`, no shared/session/module-scoped fixtures.
- **Class-level mutable default** — `BaseTestCase.files: Dict[str, str] = {}`
  (`base_test_case.py:11`) is shared across all instances/subclasses. Tests **rebind**
  `self.files = {...}` (instance attribute shadowing); the class dict is **never mutated
  in-place** (`update`/`files[x]=`), so no cross-test leakage occurs through it. A test that
  skipped setting `self.files` would read the empty class dict.
- **`self.updated_files`** reset fresh per test in `setUp` (`base_test_case.py:38`); pure
  instance state.
- **Source module-level mutable globals** (all read-only at runtime, never mutated):
  `ignore.py:9-36` (`IGNORED_VARIABLE_NAMES`, `PYTEST_FUNCTION_NAMES`, `PYTEST_METHOD_NAMES`,
  `ERROR_CODES`), `noqa.py:17` (`NOQA_CODE_MAP`), `constants.py:36` (`ERROR_TYPE_TO_ERROR_CODE`).
- **No `lru_cache`/`functools.cache`** anywhere in `deadcode/`. The "cached" comments at
  `find_unused_code_visitor.py:128,136` refer to instance attribute `self.file_content_lines`
  (`:138`); a fresh `FindUnusedCodeVisitor` is built per `main()` call
  (`find_unused_names.py:14`), so no visitor state persists between tests.

## Cross-Cutting Observations
- **Two divergent runners** exist: `Justfile` (parallel xdist, `-n nproc-1`) and `Makefile`
  (serial, `-vv`). pytest-xdist parallelism + per-process `PYTHONHASHSEED` is the main lever
  by which any latent hash/order dependence could surface.
- **The mock seam is path-specific**: `BaseTestCase` patches `find_python_filenames` only at
  `deadcode.cli` import site. Tests importing the function directly
  (`test_find_python_filenames.py`, `test_exclude.py`) bypass the mock and hit the real FS.
- **cwd coupling**: real-FS tests + config discovery (`parse_arguments.py:219`) all assume
  cwd == repo root; nothing anchors paths to `__file__`.

## Open Areas
- Whether tests currently *fail* under parallel/hash-randomized runs was not executed here;
  this is a static description of the order/state structures, not an empirical flakiness run.
- The exact emission order of the integration tests' real-FS output depends on the host
  filesystem's `glob('*')` ordering for `tests/files/` and `deadcode/`, which was not
  enumerated per-OS.

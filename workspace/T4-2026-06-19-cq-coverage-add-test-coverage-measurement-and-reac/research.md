# Research Findings

## Q1: How is the test suite run and configured (pytest-cov, source, omit/exclude, fail-under)?

### Findings
- **pytest config** lives in `pyproject.toml:[tool.pytest.ini_options]`. The only key is:
  `addopts = "--cov=. --no-cov-on-fail --cov-fail-under=88.0"` (`pyproject.toml`, last line).
  - `--cov=.` measures the **entire repo** (both `deadcode/` and `tests/`), not just the package.
  - `--no-cov-on-fail` suppresses the coverage report if tests fail.
  - `--cov-fail-under=88.0` fails the run if total coverage < 88.0%.
- There is **no `[tool.coverage.*]` section** anywhere — no `source`, `omit`, `exclude_lines`, or `branch` settings are declared (only `[tool.deadcode]`, `[tool.ruff*]`, `[tool.mypy]`, `[tool.isort]`, `[tool.black]`, `[tool.hatch*]` exist).
- **Justfile `test` recipe**: `uv run pytest -n "$(nproc --ignore=1)" {{args}}` — runs pytest under `pytest-xdist` (parallel `-n`). It adds **no** coverage flags itself; coverage comes solely from `addopts`. The recipe depends on `sync` (installs `requirements-dev.txt` + `-e .[test]`).
- **Makefile `test` recipe**: `.venv/bin/pytest -vv $(PYTEST_ME_PLEASE)` — verbose, no `-n`, no explicit coverage flags (again relies on `addopts`). `make check: test lint mypy audit deadcode`.
- **CI**: only one workflow, `.github/workflows/check-deadcode-on-python38.yml`. It sets up Python 3.8, runs `make .venv`, then `make check`. So CI invokes coverage transitively via `make test` → pytest `addopts`. The fail-under (88.0) is the enforced gate. No separate coverage-upload/badge step exists.
- Coverage deps are declared in `pyproject.toml` `[project.optional-dependencies].test`: `pytest`, `pytest-cov`, `pytest-xdist` (`pyproject.toml:33-41`).

## Q2: Current measured line coverage and uncovered modules/paths

### Findings
Measured via `pytest -o addopts="" --cov=deadcode --cov-report=term-missing` (deadcode package only): **1190 statements, 110 missing → ~90.8%**. With the default `addopts` (`--cov=.`, includes test files) the run reports **TOTAL 90.14%** and prints `Required test coverage of 88.0% reached`. Suite result: **127 passed, 18 skipped**.

Per-module deadcode/ misses (statements / missed / % / missing lines):
- `actions/find_python_filenames.py` — 25/3/88% — lines `19, 32-33`
- `actions/merge_overlaping_file_parts.py` — 72/4/94% — `14, 86-87, 114`
- `actions/parse_arguments.py` — 54/3/94% — `9, 25, 222`
- `actions/remove_file_parts_from_content.py` — 158/21/87% — `28-34, 38-41, 47-57, 112, 219, 290-291`
- `cli.py` — 20/1/95% — `35`
- `utils/base_test_case.py` — 52/3/94% — `87-90` (the `assertUpdatedFiles` helper)
- `utils/fix_indent.py` — 24/2/92% — `12-13`
- `utils/flatten_lists.py` — 10/1/90% — `18`
- `utils/nested_scopes.py` — 32/1/97% — `24`
- `utils/print_ast.py` — 3/1/67% — `5`
- `visitor/code_item.py` — 41/3/93% — `91, 129, 137`
- `visitor/find_unused_code_visitor.py` — **280/47/83%** (lowest absolute miss count) — `204-210, 251, 265-267, 343, 347, 358, 366-368, 378, 381-397, 402, 428-430, 440, 447, 449, 459, 493-496, 503-504, 556-557, 599-607`
- `visitor/fix_unused_code_visitor.py` — 143/1/99% — `184`
- `visitor/lines.py` — 35/4/89% — `64-65, 80-81`
- `visitor/utils.py` — **48/15/69%** (lowest %) — `23-27, 29, 55-62, 73, 85`
- **100% modules**: `actions/find_unused_names.py`, `actions/fix_or_show_unused_code.py`, `actions/get_unused_names_error_message.py`, `actions/parse_abstract_syntax_tree.py`, `constants.py`, `data_types.py`, `utils/add_colors_to_diff.py`, `utils/remove_from_list.py`, `visitor/ignore.py`, `visitor/noqa.py`, and all `__init__.py`.
- The biggest gaps are concentrated in `visitor/find_unused_code_visitor.py` (47 lines, incl. `_add_aliases`/format-string/Call/conditional/unreachable-code paths) and `visitor/utils.py` (`_safe_eval`, `condition_is_always_*`, `get_decorator_name`).
- Note: tests/ files also appear in the default `--cov=.` report; several test modules are partly uncovered because of `@skip` classes (e.g. `tests/fix/test_scope.py` 32%, `tests/test_accurate_usage_detection.py` 60%).

## Q3: Module organization of deadcode/ and CLI→analysis control flow

### Findings
Public entry points:
- `deadcode/cli.py:12` — `main(command_line_args=None) -> Optional[str]`; the only orchestrator. (`[project.scripts] deadcode = "deadcode.cli:main"`.)
- `deadcode/constants.py` — type literals `UnusedCodeType` (`:4`), `UnusedCodeErrorCode` (`:20`), mapping `ERROR_TYPE_TO_ERROR_CODE` (`:36`).
- `deadcode/data_types.py` — `Args` dataclass (`:13`), `Part` NamedTuple (`:37`), type aliases `AbstractSyntaxTree`/`FileContent`/`Filename`/`Pathname` (`:7-10`).
- `actions/` one public function each: `parse_arguments` (`parse_arguments.py:15`), `find_python_filenames` (`find_python_filenames.py:11`), `find_unused_names` (`find_unused_names.py:9`), `parse_abstract_syntax_tree` (`parse_abstract_syntax_tree.py:6`), `get_unused_names_error_message` (`get_unused_names_error_message.py:7`), `fix_or_show_unused_code` (`fix_or_show_unused_code.py:15`), `remove_file_parts_from_content` (`remove_file_parts_from_content.py:127`), `merge_overlaping_file_parts` (`merge_overlaping_file_parts.py:99`).
- `visitor/` — `CodeItem` class (`code_item.py:39`), `FindUnusedCodeVisitor` (`find_unused_code_visitor.py:42`), `FixUnusedCodeVisitor` (`fix_unused_code_visitor.py:82`), plus helpers `ignore.py`, `lines.py`, `noqa.py`, `utils.py` (`LoggingList`/`LoggingSet`, `_safe_eval`, `get_decorator_name`).
- `utils/` — leaf helpers: `add_colors_to_diff`, `base_test_case` (`BaseTestCase`), `fix_indent`, `flatten_lists`, `nested_scopes` (`NestedScope`), `print_ast`, `remove_from_list`.

Control flow from `cli.main()`:
1. `parse_arguments()` (`cli.py:15`) → `Args`. Builds argparse, flattens comma-separated list args via `flatten_lists_of_comma_separated_values` (`parse_arguments.py:196`), merges `[tool.deadcode]` from `pyproject.toml` via `parse_pyproject_toml()` (`:214`), resolves `--dry`/`--fix` interplay.
2. `find_python_filenames(args)` (`cli.py:17`) → BFS over `args.paths`, skipping `_match(path, args.exclude)` (`find_python_filenames.py:14-25`).
3. `find_unused_names(filenames, args)` (`cli.py:20`) → runs `FindUnusedCodeVisitor.visit_abstract_syntax_trees()` (registers defs/uses, builds `CodeItem`s, scopes), then `FixUnusedCodeVisitor` to compute `additional_code_parts_to_remove`. Returns `(unused_items, additional_parts)`.
4. `fix_or_show_unused_code(...)` (`cli.py:23`, only if `args.fix or args.dry` and unused found) → groups by file, `merge_overlaping_file_parts`, `remove_file_parts_from_content`, writes file / prints diff / `os.remove` empties.
5. `get_unused_names_error_message(unused, args)` (`cli.py:26`) → builds message (or `None`/`''`/count). `cli.py:29-30` prints "Well done!" if nothing unused.
(Full trace incl. visitor dispatch methods captured in agent report; see `find_unused_code_visitor.py:506` `visit()` recursion and `_define()` at `:274`.)

## Q4: tests/ structure and behavior categories

### Findings
7 subdirectories + top-level `test_*.py`. Naming: files `test_<topic>.py`, classes `TestCamelCase`/`*Tests`, methods `test_*`. (Ignoring `.pyc`/`__pycache__`.)
- **Top-level**: `test_deadcode.py` (integration: `main()` over real `tests/files/` fixtures + invalid-file case), `test_output.py` (`--count`/`--quiet`/`--verbose`, color), `test_imports.py` (cross-file import tracking), `test_line_number_detection.py` (counts via `--count`), `test_accurate_usage_detection.py` (**entirely `@skip`**), `test_variable_parsing_from_ast_dump.py` (**stub `pass`**).
- **actions/**: `test_find_python_filenames.py`, `test_merge_overlaping_file_parts.py`, `test_remove_file_parts_from_content.py` — unit tests of standalone action functions on raw tuples/`Part`s.
- **cli_args/**: per-flag tests — `test_parsing.py` (asserts `Args` fields), `test_fix.py`, `test_dry.py`, `test_ignore_names.py`, `test_exclude.py`, `test_ignore_definitions.py`, `test_ignore_definitions_if_inherits_from.py`, `test_ignore_bodies_if_inherits_from.py`. **Empty stubs**: `test_count.py`, `test_quiet.py`, `test_verbose.py`, `test_no_color.py`, `test_ignore_names_in_files.py`.
- **fix/**: removal by construct — `test_assign.py`, `test_class_def.py`, `test_method_def.py`, `test_empty_files.py`, `test_unreachable_code.py`, `test_unused_imports_in_a_single_file.py`, `test_unused_imports_in_a_multiple_files.py`, `test_scope.py` (**entirely `@skip`**). Several individual cases in assign/class_def also `@skip`.
- **noqa/**: `test_noqa_comments.py` (`# noqa`/`# noqa: DCxx`; DC05/06/08/09/13 cases `@skip`).
- **nested_scope/**: `test_nested_scope.py` (scope tracking, inheritance; 2 type-tracking cases `@skip`).
- **code_item/**: `test_code_item.py` (`CodeItem.__eq__`/`__hash__`).
- **utils/**: `test_fix_indent.py`, `test_add_colors_to_diff.py`.
- **files/**: static fixtures used only by `test_deadcode.py` (`variables.py`, `functions.py`, `classes.py`, `subdir/one_more_file.py`, `subdir/another_subdir/__init__.py`).

## Q5: Shared test infrastructure and assertion patterns

### Findings
- **`deadcode/utils/base_test_case.py` `BaseTestCase(unittest.TestCase)`** is the sole shared harness. (Note: it lives **inside the package**, not under `tests/`, and is referenced in `[tool.deadcode].ignore_names_in_files`.)
  - Class attrs: `files: Dict[str,str] = {}` (`:11`), `maxDiff = None` (`:13`).
  - `setUp()` (`:37-54`): resets `self.updated_files`; patches `deadcode.cli.find_python_filenames` → returns `self.files` keys; patches `open` in 3 modules (`visitor.find_unused_code_visitor`, `visitor.fix_unused_code_visitor`, `actions.fix_or_show_unused_code`); patches `actions.fix_or_show_unused_code.os.remove` → `self.os_remove` MagicMock; sets `self.args = Args()`.
  - `_read_file_side_effect()` (`:23-35`): mock file CM; runs source through `fix_indent()`, exposes `.read()`/`.readlines()`, and a `.write` side-effect caching into `self.updated_files`.
  - `patch()` helper (`:15-18`) auto-registers `patcher.stop` cleanup.
  - `assertFiles(files, removed=None)` (`:56-82`): primary assertion — checks `os.remove` calls, compares `fix_indent(expected)` vs `fix_indent(actual)` for written+unchanged files.
  - `assertUpdatedFiles()` (`:84-93`) — stricter; **uncovered** (lines 87-90, see Q2).
  - **No `conftest.py`** anywhere under `tests/` (only one in `.venv/`). `tests/utils/__init__.py` and `tests/cli_args/__init__.py` are empty package markers.
- **Dominant patterns** (subagent excerpts):
  - Pattern A (`tests/cli_args/test_fix.py:8-33`): set `self.files = {name: "..."}`, call `main(['name','--no-color','--fix'])`, `assertEqual` on returned string, then `assertFiles({...})`.
  - Pattern B (`tests/fix/test_empty_files.py:10-22`): `assertFiles({}, removed=['foo.py'])` to verify deletion via `os.remove` mock.
  - Pattern C (`tests/cli_args/test_dry.py:7-30`): wrap expected multi-line output in `fix_indent("""...""")`; CLI args via `'foo.py --no-color --fix --dry'.split()`.
  - Some tests subclass `BaseTestCase` with virtual FS; `test_deadcode.py` `DeadCodeIntegrationTests` instead runs against **real** `tests/files/` paths.

## Q6: Explicit exclusions from analysis/coverage

### Findings
- **No coverage omit/exclude config** exists — there is no `[tool.coverage.run] omit` or `[tool.coverage.report] exclude_lines`, and `--cov=.` has no source filter. So coverage measures everything it imports (incl. test files).
- **No `# pragma: no cover`** comments anywhere in `deadcode/` (grep returned no matches).
- **`[tool.deadcode]` (analysis, not coverage) exclusions** in `pyproject.toml`:
  - `ignore_names = [...]` — names exempt from dead-code analysis, incl. `ERROR_CODES`, `fix`, `fix_indent`, `ignore_*` config setters, `parse_noqa`, `scoped_name`, `show`, and glob `visit_*` (covers all visitor dispatch methods).
  - `ignore_names_in_files = ["deadcode/utils/base_test_case.py"]` — the whole test base class file is exempt from name analysis.
  - `exclude = ["tests"]` — the `tests/` directory is excluded from deadcode's own self-analysis (used by `make deadcode` / `make check`).
- **Build packaging exclusion** (`[tool.hatch.build]`): `include = ["**/*.py"]`, `exclude = ["tests/**"]` — tests are not shipped in the wheel (separate from coverage).
- **mypy** `exclude = ["build","dist",".venv"]`; **ruff** `per-file-ignores."tests/*"` relaxes `S101`/`PT009`/`ANN201`/`D` — style only, not coverage.

## Cross-Cutting Observations
- Coverage is wired entirely through pytest `addopts` (`--cov=.`); no dedicated coverage config block, no per-module `source`/`omit`. Both Just and Make rely on this; CI enforces only the 88.0 fail-under.
- `--cov=.` conflates package and test coverage; the package-only figure (~90.8%) and the reported TOTAL (90.14%) differ because skipped test modules drag in uncovered test lines.
- A meaningful share of "missing" lines trace to **18 skipped tests** (`@skip` classes/methods in `test_scope.py`, `test_accurate_usage_detection.py`, `test_variable_parsing_from_ast_dump.py`, parts of noqa/nested_scope/assign/class_def) and to **empty stub test files** in `cli_args/`.
- The shared `BaseTestCase` deliberately lives in the shipped package (`deadcode/utils/`) and is doubly protected from deadcode's own analysis via `ignore_names` + `ignore_names_in_files`.

## Open Areas
- The exact intended target/threshold beyond the current 88.0 fail-under is not specified in any config — only the existing value is recorded here.
- Branch coverage is not enabled (no `branch = true`); all figures are statement (line) coverage only.

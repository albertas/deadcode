# Research Findings

Focus: how `deadcode/` parses and analyzes source, how `tests/` is organized,
and how interpreter-version assumptions are encoded across code + tooling.

## Q1: How does the tool turn a source file into an AST, and which `ast` APIs/options does it use?

### Findings
- Single entry point: `deadcode/actions/parse_abstract_syntax_tree.py:6`
  `parse_abstract_syntax_tree(file_content, args, filename)`.
- Core call: `ast.parse(file_content, filename=filename, type_comments=True)`
  (`parse_abstract_syntax_tree.py:9`). The only parsing option used is
  `type_comments=True` (enables `# type:` comment capture).
- Bare `except:` (`parse_abstract_syntax_tree.py:10`, `# noqa: E722`) — ANY parse
  failure (e.g. `SyntaxError` from syntax newer than the running interpreter)
  is swallowed; prints `Error: Failed to parse {filename} file, ignoring it.`
  (unless `args.count`/`args.quiet`) and returns an empty
  `ast.Module(body=[], type_ignores=[])` (`:13`). So unsupported syntax silently
  yields zero findings for that file.
- Called from `FindUnusedCodeVisitor.visit_abstract_syntax_trees` at
  `find_unused_code_visitor.py:111`, reading each file via `open(file_path)`.
- Type comments are re-parsed downstream: `find_unused_code_visitor.py:564-568`
  `_visit_type_comment` calls `ast.parse(type_comment, mode='func_type'|'eval')`.
- `ast.unparse(node)` is used in the fix path: `fix_unused_code_visitor.py:140`
  (stdlib 3.9+).

## Q2: Which AST node types/visitor methods are implemented, and how are `match`, `type` aliases, and PEP 695 generics handled?

### Findings
- `FindUnusedCodeVisitor(ast.NodeVisitor)` — `find_unused_code_visitor.py:42`.
  `visit_*` methods (node → line):
  `AsyncFunctionDef:348` (delegates to FunctionDef), `Attribute:351`,
  `BinOp:357`, `Call:371`, `ClassDef:438`, `FunctionDef:446`, `If:467`,
  `IfExp:470`, `Import:473`, `Import_after_visiting_child_nodes:478` (pass),
  `ImportFrom:481`, `Name:497`, `Assign:510`, `AugAssign:513`, `AnnAssign:516`,
  `While:519`, `MatchClass:523`.
- `visit_arg` is commented out (`:344-346`); positional-only/keyword-only args
  have no dedicated visitor.
- Traversal does NOT use `generic_visit`. `visit()` (`:588-618`) is fully
  overridden: pre-dispatch (`_dispatch_pre_visit:549`), then ALWAYS recurse via
  `_visit_children` (`:570-581`, iterates `ast.iter_fields`), then post-dispatch
  (`visit_*_after_visiting_child_nodes`). **Every child node is visited
  unconditionally**, even nodes lacking a `visit_*` method — so new syntax is
  walked into, just without specialized usage tracking.
- **`match` statements**: no `visit_Match`; the `match`/`case` body is recursed
  into, and `visit_MatchClass:523` marks `node.kwd_attrs` names as used. No
  handling for `MatchValue`, `MatchAs`, `MatchOr`, `MatchMapping`, `MatchStar`,
  `MatchSingleton`, `MatchSequence`. Note `visit_MatchClass` signature is
  untyped (`node`) — typed version commented at `:522`.
- **`type` alias (`ast.TypeAlias`, 3.12)**: no `visit_TypeAlias`. Recursed into
  generically; the alias name node handling is not specialized.
- **PEP 695 generics (`ast.TypeVar`/`ParamSpec`/`TypeVarTuple`, `type_params`)**:
  no visitor methods; recursed generically.
- **Walrus (`ast.NamedExpr`)**: no `visit_NamedExpr`; target is an `ast.Name`
  Store node, so `visit_Name:497-501` registers it as a defined variable.
- `FixUnusedCodeVisitor(ast.NodeVisitor)` — `fix_unused_code_visitor.py:60`.
  `visit_*`: `With:269`, `ClassDef:286`, `ImportFrom:327`, `Import:333`,
  `Assign:406`. Its `visit()` (`:430-451`) also overrides and recurses into all
  children unconditionally; no match/type-alias/PEP695 handling.
- Supporting modules:
  - `visitor/lines.py`: `_get_last_child_with_lineno:5` (special-cases
    `ast.Call:22`), `get_last_line_number:41`, `get_first_line_number:69`.
  - `visitor/ignore.py`: `ERROR_CODES:23` (DC01–DC13), `_get_unused_items:39`,
    `_match:49`, `_match_many:54`, `_assigns_special_variable__all__:66`
    (branches on `ast.Assign` vs `AugAssign`/`AnnAssign`), per-category ignore
    predicates `:74-106`.
  - `visitor/utils.py`: `_safe_eval:7` (BoolOp/UnaryOp/`ast.literal_eval`),
    `condition_is_always_false/true:37/41`, `get_decorator_name:53`,
    `LoggingList:64`, `LoggingSet:76`.
  - `visitor/code_item.py`: `CodeItem` class (`:38`, `__slots__:43`); `__eq__`
    compares by `name` only (`:130`), `__hash__` by name (`:138`).

## Q3: How is `tests/` organized — `BaseTestCase`, fixtures, and conventions?

### Findings
- `BaseTestCase(TestCase)` — `deadcode/utils/base_test_case.py:10`. Fixtures are
  declared as `self.files: dict[str, str]` (fake filename → source string).
- `setUp:37` patches the I/O seams: `cli.find_python_filenames` returns
  `list(self.files.keys())` (`_get_filenames:20`);
  `find_unused_code_visitor.open` and `fix_unused_code_visitor.open` →
  `_read_file_side_effect:23` (serves content through `fix_indent`);
  `fix_or_show_unused_code.open` → same, with `.write` capturing into
  `self.updated_files` (`:27-29`); `fix_or_show_unused_code.os.remove` mocked
  (`:52`); `parse_arguments.parse_pyproject_toml` → `{}` (`:54`).
- Entry point: tests import `from deadcode.cli import main` and call
  `main(argv: list[str])` with paths + flags (`--no-color`, `--fix`, `--count`,
  `--quiet`, `--dry`, `-v`). Return value: `None` when nothing found / syntax
  error; a formatted `path:line:col: DCxx ...` string otherwise; `+ "\n\nRemoved
  N unused code item(s)!"` under `--fix`; count string under `--count`.
- Assertions: `assertEqual`/`assertIsNone` on return value; `assertFiles:59`
  (full file-state union, normalized via `fix_indent`); `assertUpdatedFiles:87`
  (only written files). Examples: `tests/test_imports.py:59-67`,
  `tests/fix/test_assign.py:11-32`, `tests/fix/test_class_def.py:37-59`.
- `fix_indent` (`deadcode/utils/fix_indent.py:25`) strips common leading margin
  so fixtures can be written as indented triple-quoted strings. Applied both
  when serving fixture content (`base_test_case.py:31`) and when comparing
  expected vs actual (`:79`, `:94`); also called directly on expected strings
  (e.g. `tests/fix/test_unused_imports_in_a_single_file.py:31`).
- Directory layout under `tests/`: `files/` (real on-disk fixtures used by
  `test_deadcode.py` integration tests), `actions/`, `cli_args/`, `code_item/`,
  `fix/`, `nested_scope/`, `noqa/`, `utils/`, `visitor/`, plus top-level
  `test_*.py`. Three test styles: `BaseTestCase` functional tests (majority),
  real-file integration (`test_deadcode.py:13`, `os.chdir(REPO_ROOT)`), and pure
  `unittest.TestCase` unit tests (`visitor/test_lines.py`, `visitor/test_utils.py`,
  `utils/test_fix_indent.py`). Some classes fully `@skip`ped
  (`test_accurate_usage_detection.py:7`, `fix/test_scope.py:11`).
- New-test convention: subclass `BaseTestCase`, set `self.files`, call `main([...])`,
  assert return value and/or `assertFiles`/`assertUpdatedFiles`. Fake filenames
  are arbitrary (`'foo.py'`, multi-segment `'eggs/spam/bar.py'`).
- Existing syntax-targeted tests (`tests/visitor/test_find_unused_code_visitor.py`):
  `async def:16`, decorators `:90-100`, `@property:31`, old/new format strings
  `:22-29`; `MatchClass` test (`:102-106`) uses `types.SimpleNamespace` to AVOID
  literal `match` syntax in the test file. **No tests** exist for walrus,
  `type` alias, PEP 695 generics, or literal `match`/`case` syntax.

## Q4: Where are Python-version assumptions encoded, and what is the lowest target?

### Findings
- Declared minimum: `pyproject.toml:9` `requires-python = ">= 3.11"`; classifiers
  3.11–3.14 (`:16-19`); `Makefile:3` `PYTHON_VERSION ?= 3.11`; CI matrix
  `.github/workflows/check.yml:19` `["3.11","3.12","3.13","3.14"]`.
- Tool targets: mypy `python_version = "3.11"` (`pyproject.toml:165`); black
  `target_version = ["py311"]` (`:211`). Ruff has **no** explicit `target-version`
  in `[tool.ruff]` (`:60-61`).
- **No `sys.version_info` branches** anywhere in `deadcode/` or `tests/`.
- **No `from __future__ import annotations`** anywhere.
- Hard 3.11 floor comes from unconditional `tomllib` use:
  `deadcode/actions/parse_arguments.py:6` (import), `:221` (`tomllib.load(f)`) —
  `tomllib` is stdlib only in 3.11+.
- Other modern-syntax usage (would permit <3.11 if not for tomllib): PEP 604
  `X | Y` unions throughout (e.g. `find_unused_code_visitor.py:88,201,278`;
  `data_types.py:48`); PEP 585 builtin generics `list[...]`/`dict[...]`
  throughout; walrus `:=` (`cli.py:24`, `find_unused_code_visitor.py:425`,
  `remove_file_parts_from_content.py:29,33,377`); `ast.unparse`
  (`fix_unused_code_visitor.py:140`, 3.9+).
- The source itself does NOT use `match`/`case`, `type` aliases, or PEP 695
  generics. Lowest version the code targets: **3.11**.

## Q5: How do build/CI configs select and pin Python versions, and wire the test matrix?

### Findings
- `Makefile`: `PYTHON_VERSION ?= 3.11` (`:3`); `.venv` target creates the venv
  with `uv venv -p $(PYTHON_VERSION)` (`:11`); `check: test lint mypy audit
  deadcode` (`:5`); `test` runs `pytest -n $(nproc --ignore=1)` (`:21`).
- CI (`.github/workflows/check.yml`): matrix `python-version`
  `["3.11","3.12","3.13","3.14"]` (`:19`); each job sets up the interpreter via
  `actions/setup-python@v5` (`:23-26`), then
  `make .venv PYTHON_VERSION=${{ matrix.python-version }}` (`:29`) and
  `make check` (`:32`). So the same `make check` gate runs once per interpreter.
- `Justfile`: `sync` re-syncs deps; `test *args: sync` →
  `uv run pytest -n "$(nproc --ignore=1)" {{args}}` (`:10-11`); `check`
  aggregates `check-format check-lint check-complexity check-typecheck test`
  (`:34`). No interpreter pinning in the Justfile — uses the ambient `uv`/venv.
- `pyproject.toml` pins requested versions via `requires-python` and classifiers
  (Q4); deps compiled for 3.11 in `Makefile:50-51` (`uv pip compile --python 3.11`).

## Q6: What coverage/lint/type gates does `pyproject.toml` define, and how do new test files interact?

### Findings
- Coverage: `[tool.pytest.ini_options] addopts = "--cov=deadcode --no-cov-on-fail
  --cov-fail-under=95.0"` (`pyproject.toml:215`). `[tool.coverage.run]
  source=["deadcode"]`, omits `deadcode/utils/base_test_case.py` (`:217-219`).
  Coverage is measured on `deadcode/` only — new test files do not add to the
  measured surface but can RAISE coverage by exercising more of `deadcode/`.
- mypy: `strict = true`, `python_version = "3.11"`, `exclude = ["build","dist",
  ".venv"]` (`:163-171`). `Makefile:30` runs `mypy deadcode` (source only);
  `Justfile:19` `mypy deadcode/` — tests are NOT type-checked by either.
- ruff: `select = ["ALL"]` with a large `ignore` list (`:73-151`),
  `line-length=120` (`:61`), `mccabe max-complexity = 8` (`:71`). Per-file
  ignores for `tests/*`: `S101`, `PT009`, `ANN201`, `SLF001`, `D` (`:153-160`) —
  so test files may use bare `assert`, skip annotations/docstrings, and read
  private members. `Makefile:23`/`Justfile:16` lint BOTH `deadcode tests`.
- `[tool.deadcode]` (self-scan): `ignore_names` includes `visit_*`, `show`,
  `parse_noqa`, etc. (`:179-201`); `exclude = ["tests"]` (`:206`) — the tool does
  not scan its own tests for dead code.
- Net effect for adding test files: they run under pytest (counted by `-n`
  xdist), are linted with the relaxed `tests/*` ruff profile, are exempt from
  mypy and the deadcode self-scan, and contribute to (never reduce) the 95%
  coverage-of-`deadcode/` gate.

## Cross-Cutting Observations
- The tool degrades silently on unparseable input (Q1 bare-except → empty
  Module), so syntax newer than the running interpreter produces no findings
  rather than an error — relevant to any version-specific test fixture.
- Generic, unconditional child recursion (Q2) means new syntax is structurally
  walked; specialized usage tracking exists only for the enumerated node types.
- Tests avoid embedding literal `match`/walrus/`type`-alias syntax today; the one
  match-related test sidesteps it with `SimpleNamespace`
  (`test_find_unused_code_visitor.py:102-106`).
- Version policy is consistent across `pyproject.toml`, `Makefile`, CI, mypy, and
  black at **3.11**; the only mechanical 3.11 floor is `tomllib`.

## Open Areas
- Ruff's effective `target-version` is implicit (no setting at
  `pyproject.toml:60`); whichever interpreter runs ruff in CI (3.11–3.14)
  determines its syntax baseline — not pinned in config.
- No existing tests assert behavior on `match`/`case`, `type X = ...`, PEP 695
  generics, or walrus targets, so current behavior for those constructs is only
  inferable from the recursion logic, not from test coverage.

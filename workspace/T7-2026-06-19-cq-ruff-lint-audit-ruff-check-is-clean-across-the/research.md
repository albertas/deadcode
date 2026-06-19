# Research Findings

Scope: the `deadcode/` package, the sibling `tests/` suite, and tooling config in
`pyproject.toml` / `Justfile`. Targets Python 3.11+.

## Q1: How are type annotations expressed across the package?

### Findings
- `typing`-module forms (`List`, `Dict`, `Optional`, `Union`, `Tuple`, `Set`,
  `Iterable`, `Callable`, `Any`, `TextIO`, `TypeVar`, `NamedTuple`, `Literal`)
  dominate. Import sites (one per module):
  - `constants.py:1` (`Dict, Literal`), `data_types.py:4` (`Iterable, NamedTuple`),
    `cli.py:1` (`List, Optional`), `utils/fix_indent.py:2` (`Optional`),
    `utils/nested_scopes.py:1`, `utils/base_test_case.py:2`,
    `utils/remove_from_list.py:1`, `utils/flatten_lists.py:1`,
    `visitor/code_item.py:32`, `visitor/utils.py:2`, `visitor/lines.py:2`,
    `visitor/noqa.py:3` (`Dict, List, Set`), `visitor/ignore.py:4`,
    `visitor/find_unused_code_visitor.py:13`, `visitor/fix_unused_code_visitor.py:51`,
    `actions/find_python_filenames.py:2`, `actions/find_unused_names.py:1`,
    `actions/fix_or_show_unused_code.py:3`, `actions/parse_arguments.py:2`,
    `actions/get_unused_names_error_message.py:1`,
    `actions/merge_overlaping_file_parts.py:1`,
    `actions/remove_file_parts_from_content.py:2`.
- Annotation positions: function params/returns are dominant (e.g.
  `cli.py:13-14`, `code_item.py:58-69`, `find_unused_code_visitor.py:199,271-280`,
  `lines.py:5`, `find_unused_names.py:9-12`, `nested_scopes.py:37`). Inline
  variable annotations: `base_test_case.py:11,38`, `find_unused_code_visitor.py:50,56-64,66,69,72,78`,
  `nested_scopes.py:18,48`, `utils.py:32`, `lines.py:29,80`.
- Class-body annotations: `@dataclass Args` fields `data_types.py:13-34`;
  `Part(NamedTuple)` fields `data_types.py:37-50`.
- Type-alias assignments (plain `=`, not annotations): `constants.py:4-17,20-33`
  (`Literal` aliases), `data_types.py:7-10`, `flatten_lists.py:3` /
  `remove_file_parts_from_content.py:6` (`TypeVar('T')`).
- **No file** in `deadcode/` or `tests/` uses `from __future__ import annotations`
  (zero occurrences).
- Runtime annotation evaluation: `@dataclass` (`data_types.py:13`) and
  `NamedTuple` (`data_types.py:37`) read class-body annotations at class-creation
  time. No `get_type_hints()` and no direct `__annotations__` access anywhere.
  Type *comments* are AST-parsed at runtime in `find_unused_code_visitor.py:550-553`.
- Built-in generic/union syntax (PEP 585/604) appears in only 5 spots:
  `find_unused_code_visitor.py:82`, `fix_unused_code_visitor.py:96,98`,
  `data_types.py:47,50`. Everything else uses `typing` forms.

## Q2: How does `deadcode/visitor/noqa.py` define and parse `# noqa` directives?

### Findings
- Regex `NOQA_REGEXP` at `noqa.py:5-15`:
  `r'# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?'` with `re.IGNORECASE`.
  Accepts bare `# noqa`, `# noqa: E123`, comma/space lists `# noqa: E123,W451`,
  any casing. Matched via `.search()` (unanchored).
- `_parse_error_codes` (`noqa.py:50-52`): `(matches_dict['codes'] or 'all').split(',')`
  with per-token `.strip()`; bare noqa → code key `'all'`.
- `parse_noqa(code)` (`noqa.py:55-63`): takes whole-file string, iterates
  `code.splitlines(True)` with `enumerate(..., start=1)`, looks each code up through
  `NOQA_CODE_MAP`, accumulates `defaultdict(set)` → `{code: {linenos}}`.
- `ignore_line(noqa_lines, lineno, error_code)` (`noqa.py:66-68`):
  `return lineno in noqa_lines[error_code] or lineno in noqa_lines['all']`.
- `NOQA_CODE_MAP` (`noqa.py:17-47`): flake8 aliases `F401→DC07`, `F841→DC01`;
  short `DC01`–`DC13` identity (no `DC10`); long `DC001`→`DC01` … `DC013`→`DC13`.
- Error-code dicts (two parallel maps): `ERROR_CODES` in `ignore.py:23-36`
  (`UnusedCodeType → DCxx`, key `'empty_file'`); `ERROR_TYPE_TO_ERROR_CODE` in
  `constants.py:36-49` (same, but key `'unused_file'`), consumed at
  `code_item.py:83`. `UnusedCodeErrorCode` Literal at `constants.py:20-33`.
- Consumers (only two): `find_unused_code_visitor.py` imports module at `:22`,
  inits `self.noqa_lines` at `:78`, calls `parse_noqa` per file at `:109`, and
  `noqa.ignore_line(self.noqa_lines, lineno, ERROR_CODES[type_])` inside `_define()`'s
  `ignored()` closure at `:295`. `fix_unused_code_visitor.py` imports at `:61`, calls
  `parse_noqa` at `:109`, but **never calls `ignore_line`**. `code_item.py` does not
  use `noqa.py`.
- Fixture/intentional noqa strings: `tests/noqa/test_noqa_comments.py` embeds
  `# noqa: DC01`–`DC13` and bare `# noqa` as triple-quoted source (lines 11, 32, 51,
  71 [intentionally wrong `DC02` on a DC01 item], 96, 117, 148, 177, 203, 225, 253,
  277, 297, 317). Source-level tool-suppression noqa: `parse_abstract_syntax_tree.py:10`
  (`except:  # noqa: E722`), `find_unused_code_visitor.py:23` and
  `fix_unused_code_visitor.py:62` (`...import print_ast as show  # noqa: F401`).

## Q3: Exception raising/handling conventions

### Findings
- Exactly **one `raise`** in the whole package: `fix_unused_code_visitor.py:182`
  `raise ValueError('Conversion from 1D to 2D code part failed')` — inline string
  literal, no f-string/constant.
- **Zero custom exception classes** (no `class *Error`/`class *Exception`). Only
  built-ins used.
- Broad/`except` clauses:
  - Bare `except:  # noqa: E722` at `parse_abstract_syntax_tree.py:10` — catches any
    `ast.parse(..., type_comments=True)` failure (incl. `SyntaxError`), optionally
    prints `Error: Failed to parse {filename} file, ignoring it.` and returns
    `ast.Module()`. Only bare except in the package; no explicit `SyntaxError` handler.
  - `except UnicodeError` `fix_indent.py:12` → returns `None`.
  - `except ValueError` `utils.py:34` (`ast.literal_eval`) → returns `default`.
  - `except AttributeError` `lines.py:30` (`continue`) and `lines.py:64` (`pass`).
  - `except IndexError` `find_unused_code_visitor.py:591` → `continue`.
  - `except UnicodeEncodeError` `find_unused_code_visitor.py:204` → byte-encode fallback
    (comment: "Some terminals can't print Unicode symbols.").
  - `except ValueError` `find_unused_code_visitor.py:383` → `names = []` (invalid format string).
  - No `except Exception`, multi-tuple, or `BaseException` clauses anywhere.
- Degrade-not-raise pattern: many functions return `None` as a sentinel instead of
  raising (e.g. `fix_indent.py:13`, `lines.py:38`, `nested_scopes.py:24,52,62`,
  `get_unused_names_error_message.py:11`, `merge_overlaping_file_parts.py:92`,
  `remove_file_parts_from_content.py:12`, `find_unused_code_visitor.py:410,601`).
  Parse failure prints instead of raising (`parse_abstract_syntax_tree.py:12`).

## Q4: Unused imports / locals / unpacking, and `__init__.py` surface

### Findings
- All package `__init__.py` files are **empty** (no exports, no `__all__`):
  `deadcode/__init__.py`, `deadcode/actions/__init__.py`,
  `deadcode/visitor/__init__.py`, `deadcode/utils/__init__.py`. Public entry point is
  `deadcode.cli:main` (`pyproject.toml:39`). Test `__init__.py` files mostly empty;
  fixture `tests/files/subdir/another_subdir/__init__.py:1` holds `UNUSED_VARIABLE = 123`.
- `[tool.deadcode] ignore_names` (`pyproject.toml:180-197`) deliberately keeps names
  the tool can't see as used: dynamically-dispatched `visit_*`
  (`find_unused_code_visitor.py:527`, `fix_unused_code_visitor.py:448` via `getattr`),
  `parse_noqa`/`ignore_line`/`ERROR_CODES`/`scoped_name`/`show`, and the `ignore_*` Args
  fields. `ignore_names_in_files = ["deadcode/utils/base_test_case.py"]`.
- Deliberate kept imports: `show` import carries `# noqa: F401` at
  `find_unused_code_visitor.py:23` and `fix_unused_code_visitor.py:62`.
- Imports present but not referenced in their own module body (per analyzer):
  - `find_unused_code_visitor.py:2` `SequenceMatcher` (used only in fix file);
    `:13` `Tuple` (only `ast.Tuple` used); `:39` `logger = getLogger()` never called.
  - `fix_unused_code_visitor.py` has a large copied import block with many unreferenced
    names: `:41` `chain`, `:43` `re`, `:44` `string`, `:45` `sys`, `:46` `getLogger`
    (`:79` `logger` unused), `:51` `Callable/Set/TextIO/Union/Iterable`,
    `:52` `UnusedCodeType`, `:55` `LoggingList/LoggingSet`, `:56` `utils`,
    `:58` `NestedScope`, `:65-77` all names from `deadcode.visitor.ignore`.
- Unused/placeholder unpacking:
  - `fix_unused_code_visitor.py:439` `node_name` assigned in `visit()`, never read
    (contrast `find_unused_code_visitor.py` where it is used).
  - `merge_overlaping_file_parts.py:6-7,21-22,34-35` unpack `insert_code_b/s` (and
    `_insert_condition_*` with `_`-prefix convention) but use only line/col values.
  - `remove_file_parts_from_content.py:101,108,118,160` unpack `insert_condition`, read
    only in a debug f-string at `:162`.
- Note: many of these "unused" symbols are precisely what `[tool.deadcode]
  ignore_names` and the `# noqa: F401` markers protect; Ruff's `select=["ALL"]`
  config does not flag them because the relevant rules are either suppressed or the
  names are referenced via attribute access (`noqa.ignore_line`, `ast.Tuple`).

## Q5: Static-analysis / quality tooling configuration and invocation

### Findings
- Ruff config in `pyproject.toml`: `[tool.ruff] line-length = 120` (`:53`);
  `[tool.ruff.format] quote-style = 'single', docstring-code-format = true`;
  `[tool.ruff.lint.flake8-quotes] inline-quotes = 'single'`.
- `[tool.ruff.lint] select = ["ALL"]` (`:62`) with a long `ignore` list (`:63-156`)
  — disables specific docstring (`D1xx/D2xx/D4xx`), annotation (`ANN0xx/ANN101/ANN401`),
  complexity (`C901`, `PLR09xx`), boolean-arg (`FBT00x`), and stylistic rules
  (`COM812`, `ISC001`, `G004`, `T201` print, `S101` assert, `RUF100`, `RUF012`, etc.).
- `[tool.ruff.lint.per-file-ignores]` (`:158-163`): `"tests/*"` ignores
  `S101`, `PT009`, `ANN201`, `D` (all docstring rules).
- mypy `[tool.mypy]` (`:166-174`): `strict = true`, `python_version = "3.11"`,
  `exclude = ["build","dist",".venv"]`, `pretty`, `warn_return_any`,
  `warn_unused_configs`. `[tool.isort]` profile black; `[tool.black]` line 120.
- pytest `[tool.pytest.ini_options]` (`:210-211`):
  `addopts = "--cov=deadcode --no-cov-on-fail --cov-fail-under=95.0"`.
  `[tool.coverage.run]` source `deadcode`, omit `base_test_case.py`.
- `Justfile` recipes (each depends on `sync` = `uv pip sync requirements-dev.txt`
  then `uv pip install -e .[test]`):
  - `format` → `uv run ruff format deadcode/ tests/`
  - `lint` / `check-lint` → `uv run ruff check deadcode/ tests/`
  - `check-format` → `ruff format --check deadcode/ tests/`
  - `check-complexity` → `ruff check --select C901 deadcode/ tests/`
  - `typecheck` / `check-typecheck` → `uv run mypy deadcode/`
  - `test *args` → `uv run pytest -n "$(nproc --ignore=1)" {{args}}`
  - `check` → `check-format check-lint check-complexity check-typecheck test`.
  Note: `C901` is globally ignored in `[tool.ruff.lint]` but re-enabled explicitly via
  `--select C901` in `check-complexity`.

## Q6: String/collection manipulation and simple control flow

### Findings
- String splitting: `.split('.')` on scope strings `nested_scopes.py:26,50`;
  `.split(',')` in comprehensions `flatten_lists.py:12`, `noqa.py:52`
  (`(... or 'all').split(',')`); regex-clean then split `find_unused_code_visitor.py:390`;
  `.split()` (no arg) on CLI strings throughout tests (e.g.
  `'file.py --no-color --fix -v'.split()`); `.splitlines(True)` at
  `add_colors_to_diff.py:3`, `find_unused_code_visitor.py:138`, `noqa.py:57`.
- List/set building: flat comprehensions `flatten_lists.py:19`,
  `find_unused_code_visitor.py:382,412,431`, `fix_unused_code_visitor.py:195,305,343,416-417`,
  filter comprehension `ignore.py:40`; dict comprehension `parse_arguments.py:227`;
  imperative `.append()` loops `add_colors_to_diff.py:9`,
  `get_unused_names_error_message.py:19-35`, `find_python_filenames.py:12-23`;
  `.add()` on sets `find_unused_code_visitor.py:95`, `noqa.py:62`; `.extend()`
  `find_unused_code_visitor.py:418`, `fix_or_show_unused_code.py:37`;
  `defaultdict(list)/(set)` `fix_or_show_unused_code.py:28-30`, `noqa.py:56`.
- Boolean returns: explicit `if ...: return True / return False`
  `merge_overlaping_file_parts.py:13-15,38-41`; single-expression boolean returns
  `ignore.py:46,68,74,83,87`, `noqa.py:68`, `utils.py:38-43`; mixed
  `code_item.py:132-137` (`__eq__`).
- Other control flow: ternaries `cli.py:27`,
  `get_unused_names_error_message.py:30`, `find_unused_code_visitor.py:433`,
  `ignore.py:50`; guard-clause early returns `flatten_lists.py:10-12`,
  `get_unused_names_error_message.py:10-17`, `nested_scopes.py:23-24`,
  `parse_arguments.py:220-221`, `fix_unused_code_visitor.py:349-351`; walrus `:=`
  `cli.py:26`, `find_unused_code_visitor.py:409,416-418`, `lines.py:79-80`; `for/else`
  with `break` `find_unused_code_visitor.py:422-428`.

## Q7: Test suite structure

### Findings
- `BaseTestCase` (`deadcode/utils/base_test_case.py`) extends `unittest.TestCase`.
  `files: Dict[str, str] = {}` (`:11`) maps virtual filenames → source strings; never
  written to disk. `setUp` (`:37-57`) patches `find_python_filenames`, `open` in three
  modules (`find_unused_code_visitor`, `fix_unused_code_visitor`,
  `fix_or_show_unused_code`), `os.remove`, and `parse_pyproject_toml`(→`{}`); inits
  `self.updated_files` and `self.args = Args()`.
- `patch` helper (`:15-18`) auto-registers `addCleanup`. `_get_filenames` (`:20-21`)
  returns `list(self.files.keys())`. `_read_file_side_effect` (`:23-35`) returns a
  `MagicMock` context manager whose `.read()`/`.readlines()` serve
  `fix_indent(self.files[filename])` and whose `.write()` caches into
  `self.updated_files`. `assertFiles` (`:59-85`) inspects `os_remove.mock_calls`,
  partitions changed vs unchanged files, and compares content/keys (both sides run
  through `fix_indent`); `removed=[...]` asserts deletions. `assertUpdatedFiles`
  (`:87-96`) checks only modified files.
- Inline source-string fixtures: each test assigns `self.files = {'foo.py': """ ... """}`
  at method top (e.g. `tests/noqa/test_noqa_comments.py:9-14`,
  `tests/fix/test_class_def.py:37-47`); trivial cases use single-line strings
  (`tests/test_imports.py:9-10`). Tests call `main([...])` and assert return string +
  `assertFiles`. `fix_indent` (`fix_indent.py:5-43`) normalizes leading indentation.
- Directory layout under `tests/`: `files/` (real on-disk fixtures incl. `subdir/`),
  `actions/` (action-helper unit tests), `code_item/` (CodeItem unit tests), `noqa/`
  (DC0x suppression e2e), `fix/` (`--fix` removal e2e), `nested_scope/`, `cli_args/`
  (one file per flag + `test_parsing.py`), `visitor/`, `utils/`, plus top-level
  `test_deadcode.py`, `test_output.py`, `test_imports.py`,
  `test_accurate_usage_detection.py` (skipped), `test_line_number_detection.py`,
  `test_variable_parsing_from_ast_dump.py`.
- Running the suite: `just test` → `sync` then `uv run pytest -n "$(nproc --ignore=1)"`
  (pytest-xdist). `addopts` enforces `--cov=deadcode --cov-fail-under=95.0`
  (`pyproject.toml:210-211`), with `base_test_case.py` omitted from coverage
  (`:213-215`). Full gate: `just check`.

## Cross-Cutting Observations
- Two near-identical visitor files (`find_unused_code_visitor.py`,
  `fix_unused_code_visitor.py`) share a large copied import header; the `fix` file
  carries many imports it does not use (Q4) — none flagged because the relevant Ruff
  rules are not effective here (suppressions / attribute-access usage).
- The project enforces `single` quotes, line-length 120, and `select=["ALL"]` with a
  curated `ignore` list rather than an opt-in `select` — the ignore list is the de
  facto policy surface (Q5).
- `# noqa: DCxx` is the project's own suppression mechanism (parsed by `noqa.py`),
  distinct from flake8/ruff `# noqa` used twice on source lines for tool output (Q2).
- "Degrade at boundaries, raise loudly internally" holds: one internal `ValueError`
  vs. many sentinel-`None`/print fallbacks around AST parsing and I/O (Q3).

## Open Areas
- Whether `ruff check` is currently clean was not executed as part of this research
  (the questions ask about configuration and patterns, not a live run). The `ignore`
  list, `per-file-ignores`, and `# noqa: F401`/`ignore_names` markers are the
  mechanisms that would keep it clean; verifying a clean run would require executing
  `just check-lint`.
- `fix_unused_code_visitor.py` computes `self.noqa_lines` but never calls
  `ignore_line` (Q2) — the behavioral consequence was not traced further.

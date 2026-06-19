# Research Findings

## Q1: Ruff lint config in `pyproject.toml` & `Justfile` complexity invocation

### Findings
- `[tool.ruff]` sets `line-length = 120` (`pyproject.toml:120`). Format settings:
  `quote-style = "single"`, `docstring-code-format = true` (`pyproject.toml:122-124`);
  `inline-quotes = "single"` (`pyproject.toml:126-127`).
- Lint rule selection: `select = ["ALL"]` (`pyproject.toml:130`) with a large
  `ignore` list (`pyproject.toml:131-218`).
- **`C901` (mccabe complexity) is in the global `ignore` list** (`pyproject.toml:87`,
  inside the `[tool.deadcode]`-adjacent ignore array — actually the ruff ignore array).
  So normal `ruff check` does NOT flag complexity. Other ignored complexity-adjacent
  rules: `PLR0912` (too-many-branches), `PLR0913` (too-many-args), `PLR0915`
  (too-many-statements) — all ignored.
- **There is NO `[tool.ruff.lint.mccabe]` section and NO `max-complexity` setting**
  anywhere in `pyproject.toml` (confirmed by grep — only hit is `C901` at line 87).
  This means ruff uses its **default mccabe `max-complexity = 10`** when C901 is
  selected.
- Per-file ignores: `"tests/*"` ignores `S101`, `PT009`, `ANN201`, `SLF001`, `D`
  (`pyproject.toml:220-227`).
- `Justfile` recipe `check-complexity` runs:
  `uv run ruff check --select C901 deadcode/ tests/` (after `sync`). The explicit
  `--select C901` re-enables the rule that the config-level `ignore` disabled.
- Related recipes: `lint` = `ruff check deadcode/ tests/`; `check-lint` = same;
  `check-format` = `ruff format --check`; `check-typecheck` = `mypy deadcode/`.
  Aggregate `check` = `check-format check-lint check-complexity check-typecheck test`.
- Note: the task title references "cyclomatic complexity stays 8", but the repo has
  no `max-complexity` override — the effective threshold from tooling is the ruff
  default of 10. (Open area: where "8" comes from is not encoded in config.)

## Q2: Control flow of `remove_file_parts_from_content`

### Findings
- Signature: `def remove_file_parts_from_content(content_lines: list[str], unused_file_parts: list[Part]) -> list[str]`
  (`deadcode/actions/remove_file_parts_from_content.py:128`).
- `Part` is a `NamedTuple` with 6 fields (`deadcode/data_types.py:38-51`):
  `line_start, line_end, col_start, col_end, insert_code: str|None,
  insert_code_if_character_is_not_removed: tuple[int,int]|None`. Used both unpacked
  and positionally (`code_part[0]` etc.).
- State init (`...py:131-141`): `updated_content_lines`, `unused_part_index`,
  `previous_non_removed_line`, `has_block_started`, `was_block_removed`,
  `next_line_after_removed_block`, `indentation_of_first_removed_line`, and two blank-line
  buffers (`empty_lines_in_a_row_list`, `empty_lines_before_removed_block_list`).
- Main loop `for current_lineno, line in enumerate(content_lines, start=1)` (`...py:153`),
  peeking current part via `list_get` (`...py:159`). Four-way dispatch on lineno vs part range:
  - **Branch A** interior of multi-line removal `from_line < lineno < to_line` → `continue` (`...py:167`).
  - **Branch B** first line `lineno == from_line` (`...py:172`): two inner ifs — single-line
    (`from_line == to_line`, `...py:176`) calls `remove_unused_fragments_from_a_line`
    (`...py:185`); multi-line (`...py:228`) truncates to `line[:from_col]`. Shared tail appends
    kept line (`...py:238-244`).
  - **Branch C** last line `lineno == to_line` (`...py:247`): calls
    `remove_unused_fragments_from_a_line` (`...py:250`), sub-branches C1/C2 append to output or
    blank buffer (`...py:284-290`), swaps buffers (`...py:309-312`), block-end flag handling
    (`...py:324-327`).
  - **Branch D** `else` normal line (`...py:331`): D1 blank line (`...py:332`), D2 non-blank no
    prior block (`...py:341`), D3 non-blank after block (`...py:346`) — uses
    `ends_with_semicolon` + `indentation_is_not_childs` to emit `f'{indent}pass\n'`
    (`...py:351-376`). Shared tail (`...py:378-381`).
- Post-loop (`...py:385-387`): if `was_block_removed` and last kept line ends with `:`, append
  `pass` to avoid syntax error.
- Helpers (all in same file): `list_get` (9-12), `get_indentation` (23-24),
  `remove_unused_fragments_from_a_line` (61-125), `ends_with_semicolon` (15-16),
  `indentation_is_not_childs` (19-20). `remove_as_from_end` (27) and
  `remove_comma_from_begining` (37) appear only in commented-out code.
- Cyclomatic complexity: function body alone ~30 decision points; with
  `remove_unused_fragments_from_a_line` (~10) the coupled pair is ~40. Far above 10.

## Q3: The `visit` method in `find_unused_code_visitor.py`

### Findings
- Class `FindUnusedCodeVisitor(ast.NodeVisitor)` (`deadcode/visitor/find_unused_code_visitor.py:42`).
  Overrides `visit` entirely and does NOT use `ast.NodeVisitor.generic_visit`.
- Signature `def visit(self, node: ast.AST) -> None` (`...py:518`), body `518-597`.
- Flow:
  - `node_name = getattr(node, 'name', None)` (`...py:519`).
  - inheritance annotation via walrus `if inherits_from := self.get_inherits_from(node)`
    (`...py:527`, helper at `...py:422`).
  - `should_ignore_new_definitions` activation block (`...py:530-540`) — boolean
    `_match`/`_match_many` checks against `args.ignore_definitions` /
    `ignore_definitions_if_inherits_from`.
  - Pre-children dynamic dispatch: `visit_<ClassName>` via `getattr` (`...py:543-547`).
  - Scope push for `ClassDef`/`FunctionDef`/`AsyncFunctionDef` (`...py:550-556`).
  - Second flag check for `ignore_bodies_if_inherits_from` (`...py:559-562`).
  - Type-comment handling: recursively `self.visit(ast.parse(type_comment, ...))`
    (`...py:566-569`).
  - Child traversal replacing `generic_visit`: `for _, value in ast.iter_fields(node)`,
    list fields go through `self._handle_ast_list(value)` (`...py:599`) then recurse;
    single AST fields recurse (`...py:575-583`).
  - Post-children dispatch `visit_<ClassName>_after_visiting_child_nodes` (`...py:586-589`;
    only `visit_Import_after_visiting_child_nodes` exists, `...py:478`, body `pass`).
  - Teardown: reset flag, pop scope (`...py:592-597`).
- Concrete `visit_*` dispatch targets (same file): `visit_AsyncFunctionDef` (348),
  `visit_Attribute` (351), `visit_BinOp` (357), `visit_Call` (371), `visit_ClassDef` (438),
  `visit_FunctionDef` (446), `visit_If` (467), `visit_IfExp` (470), `visit_Import` (473),
  `visit_ImportFrom` (481), `visit_Name` (497), `visit_Assign` (503), `visit_While` (510),
  `visit_MatchClass` (514).
- Entry: `visit_abstract_syntax_trees` calls `self.visit(root_module)` (`...py:143`);
  `visit` recurses into itself (`...py:569,581,583`). Returns `None`.
- Cyclomatic complexity of `visit`: ~23 (base 1 + 22 decision points incl. boolean ops).
  Above 10.

## Q4: `fix_or_show_unused_code`

### Findings
- Signature (`deadcode/actions/fix_or_show_unused_code.py:15-19`):
  `def fix_or_show_unused_code(unused_items: Iterable[CodeItem],
  additional_code_parts_to_remove: dict[Filename, list[Part]], args: Args) -> str`.
- Step 1 group items by filename into `defaultdict(list)` (`...py:28-30`, loop at `...py:29`).
- Step 2 per-file loop `for filename, file_unused_items in filename_to_unused_items.items()`
  (`...py:34`):
  - `flatten_list([item.code_parts ...])` (`...py:35`,
    `deadcode/utils/flatten_lists.py:15`).
  - merge additional parts if present (`...py:36-37`, compound `and`).
  - `merge_overlaping_file_parts(file_parts)` (`...py:39`,
    `deadcode/actions/merge_overlaping_file_parts.py:89`).
  - read file `f.readlines()` (`...py:41-42`).
  - `remove_file_parts_from_content(...)` (`...py:44`) → join (`...py:45`).
- Step 3 branch `if updated_file_content.strip()` (`...py:46`):
  - A1 dry run: `if args.dry and ('__all_files__' in args.dry or _match(filename, args.dry))`
    (`...py:47`) → `difflib.unified_diff` (`...py:49`), color sub-branch
    `if args.no_color / else add_colors_to_diff` (`...py:55-58`,
    `deadcode/utils/add_colors_to_diff.py:1`).
  - A2 `elif args.fix` → write file (`...py:60-63`).
  - B `else` → `os.remove(filename)` (`...py:65`).
- Step 4 `if result: return ''.join(result)` else `''` (`...py:67-69`).
- Coordinated functions: `flatten_list`, `merge_overlaping_file_parts`,
  `remove_file_parts_from_content`, `_match` (`deadcode/visitor/ignore.py:49`),
  `add_colors_to_diff`, stdlib `unified_diff`/`os.remove`.
- Data types: `CodeItem` (`deadcode/visitor/code_item.py:38`), `Part`/`Args`/`Filename`
  (`deadcode/data_types.py`).
- Cyclomatic complexity: ~11 decision points (counting boolean operands). At/above 10.

## Q5: `fix_indent` — definition, behavior, branching, siblings

### Findings
- Defined at `deadcode/utils/fix_indent.py:4`: `def fix_indent(doc: str) -> str | None`.
- Purpose (docstring `...py:5-8`): like `inspect.cleandoc` but keeps trailing lines.
  Removes common leading indentation from a multi-line string.
- Branching/loops:
  - `try ... except UnicodeError: return None` around `doc.expandtabs().splitlines(True)`
    (`...py:9-12`); `else` block (`...py:13-42`).
  - Loop 1 `for line in lines[0:]` with `if content:` to compute margin (`...py:18-22`).
  - `if lines:` strip first line (`...py:24-25`).
  - `if margin < sys.maxsize:` (`...py:26`) → Loop 2 `for i in range(1, len(lines))`
    (`...py:27`) with walrus `if prefix_without_spaces := prefix.rstrip(' '):` / else
    (`...py:30-33`).
  - Loop 3 `while lines and not lines[0]:` pop leading blanks (`...py:40-41`).
  - `return ''.join(lines)` (`...py:42`).
- Cyclomatic complexity: ~9 (base 1 + 8 decision points). Below 10 but close.
- **It is a single-function module** — no other helpers alongside it in `fix_indent.py`.
- Sibling modules in `deadcode/utils/`: `add_colors_to_diff.py:1` (ANSI color diff),
  `base_test_case.py:10` (`BaseTestCase`), `flatten_lists.py` (`flatten_lists_of_comma_separated_values:6`,
  `flatten_list:15`), `nested_scopes.py:6` (`NestedScope`), `print_ast.py:4` (debug, `# pragma: no cover`),
  `remove_from_list.py:7` (`remove_from_list`).
- `fix_indent` is listed in `[tool.deadcode] ignore_names` (`pyproject.toml`), so deadcode
  itself won't flag it as unused.

## Q6: Test coverage for the four targets

### Findings
- **`remove_file_parts_from_content`**: dedicated file
  `tests/actions/test_remove_file_parts_from_content.py`. Direct function calls with handcrafted
  `Part` tuples. Tests: `test_no_overlaping_parts_from_content` (`:12`), plus tests for
  `remove_as_from_end` (`:26-32`), `remove_comma_from_begining` (`:37-40`),
  `get_code_parts_for_the_same_line` (`:45`). Classes extend `BaseTestCase` (only for TestCase
  inheritance; no I/O). Also exercised indirectly by every `--fix`/`--dry` CLI test.
- **`visit`**: `tests/visitor/test_find_unused_code_visitor.py`. Two strategies:
  `TestVisitorPathsViaMain` (`:11-50`) drives via `main([...])` + `BaseTestCase` mocks;
  `TestVisitorDirectUnits` (`:57-79`) instantiates `FindUnusedCodeVisitor` via `_visitor()`
  factory (`:53-54`) and calls methods on hand-built AST nodes. Covers async def, attribute
  store, format strings, getattr, property, ternaries, `__all__`, type comment, unreachable code,
  decorators whitelist, `visit_MatchClass`. Also covered indirectly by every `main()` test.
- **`fix_or_show_unused_code`**: **no dedicated test file**; covered only via CLI tests.
  `BaseTestCase.setUp` patches `deadcode.actions.fix_or_show_unused_code.open` and
  `...os.remove` (`deadcode/utils/base_test_case.py:49-52`). Exercising files:
  `tests/cli_args/test_fix.py`, `tests/cli_args/test_dry.py`, and `tests/fix/*` (assign,
  class_def, method_def, empty_files, unreachable_code, imports, scope). Asserts write branch,
  diff branch, color branch, and file-removal branch (`test_empty_files.py:10` checks
  `os_remove`).
- **`fix_indent`**: dedicated file `tests/utils/test_fix_indent.py` using plain
  `unittest.TestCase` (not `BaseTestCase`). Tests: `test_indentation_is_not_removed_from_second_line`
  (`:7`), `test_fix_indent_for_empty_lines` (`:12`), `test_fix_indent_last_empty_line` (`:49`).
  Also used as a helper across many tests (`base_test_case.py:31,79`; `tests/cli_args/test_dry.py`;
  `tests/fix/test_unused_imports_in_a_single_file.py`; `tests/utils/test_add_colors_to_diff.py`).
- **`BaseTestCase`** (`deadcode/utils/base_test_case.py:10`): `unittest.TestCase` subclass with a
  `files` dict virtual filesystem; `setUp` (`:37-57`) patches `find_python_filenames`, the three
  module-level `open`s, `os.remove`, and `parse_pyproject_toml`. Provides `assertFiles`/
  `assertUpdatedFiles` (`:59,87`) and `_read_file_side_effect` applying `fix_indent` to dedent
  inline test content (`:23-31`). Excluded from coverage (`pyproject.toml` `omit`) and from
  deadcode (`ignore_names_in_files`).

## Cross-Cutting Observations
- Coverage gate: `pytest --cov=deadcode --cov-fail-under=95.0` (`pyproject.toml`
  `[tool.pytest.ini_options]`); `base_test_case.py` omitted from coverage.
- `Part` (`deadcode/data_types.py:38`) is the shared currency between Q2 and Q4; both
  functions are the two most complex pieces (~30 and ~11), and `visit` (~23) is the third.
- Complexity is currently NOT enforced by default `ruff check` because `C901` sits in the
  global `ignore`; only the explicit `--select C901` recipe (`check-complexity`) surfaces it,
  using ruff's default threshold of 10 (no override present).
- All four targets are reachable through the `main()` CLI path via `BaseTestCase`, in addition
  to (where present) dedicated unit tests.

## Open Areas
- The task title's specific number "8" for cyclomatic complexity is not represented anywhere
  in `pyproject.toml` or the `Justfile`; the only tooling threshold is ruff's default
  `max-complexity = 10`. Where/whether "8" is an intended target is not encoded in the repo.
- Exact, tool-computed C901 scores per function were not run here; the counts above are manual
  decision-point estimates. Running `ruff check --select C901` (the `check-complexity` recipe)
  would give the authoritative numbers.

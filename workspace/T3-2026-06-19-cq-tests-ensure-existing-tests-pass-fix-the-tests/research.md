# Research Findings

Scope: `deadcode/actions/`, `deadcode/visitor/`, `deadcode/utils/`, and the tests
under `tests/cli_args/test_dry.py`, `tests/cli_args/test_fix.py`,
`tests/fix/test_unused_imports_in_a_single_file.py`. Findings describe observed
behavior only.

## Q1: Test configuration, runner, fixtures, helpers

### Findings
- pytest config: `[tool.pytest.ini_options]` `addopts = "--cov=. --no-cov-on-fail --cov-fail-under=88.0"` (`pyproject.toml:210-211`). No markers, no `testpaths`. Running raw `python -m pytest` fails because `pytest-cov` is needed for those addopts; tests must run under `uv run` (deps from `[test]` extra).
- Test runner: `just test *args` → `uv run pytest -n "$(nproc --ignore=1)" {{args}}` (`Justfile`), i.e. pytest-xdist with cores-minus-one. `just sync` installs editable `.[test]` first.
- Skipped tests: two `@skip`-decorated in `tests/cli_args/test_fix.py:352` (`test_empty_if_statement_else_block`) and `:376` (`test_if_is_not_fixed_correctly_when_branch_is_unreachable`). These account for the "2 skipped" in the run.
- Base class: `BaseTestCase(TestCase)` (`deadcode/utils/base_test_case.py:10`). `maxDiff = None`; class attr `files: Dict[str,str]`.
- `setUp` (`base_test_case.py:37-54`) mocks: `find_python_filenames` (returns `self.files` keys), `open` patched in three modules (`find_unused_code_visitor`, `fix_unused_code_visitor`, `fix_or_show_unused_code`), and `os.remove` in `fix_or_show_unused_code`. Writes are captured into `self.updated_files` via `cache_file_content` side-effect (`base_test_case.py:27-34`). No real filesystem I/O.
- `_read_file_side_effect` (`base_test_case.py:23-35`) runs file content through `fix_indent` before serving `read`/`readlines`.
- Assertion helpers: `assertFiles` (`base_test_case.py:56-82`) compares `fix_indent(expected)` vs `fix_indent(produced)` per file; `assertUpdatedFiles` (`:84-93`) compares only files actually written.
- `fix_indent` (`deadcode/utils/fix_indent.py:5-43`): strips the first line's/min indentation (cleandoc-style) and removes leading blank lines (`:41-42`) but keeps trailing/interior blank lines. Note the in-file `TODO` (`:15`): "this method also removed empty lines, which makes exact assert checking hard." This is directly relevant to the import test's blank-line mismatch.

## Q2: main() → report + diff flow; effect of --dry / --fix

### Findings
- Entry `main()` in `deadcode/cli.py` calls in order: `parse_arguments` (`cli.py:15`), `find_python_filenames` (`:17`), `find_unused_names` (`:20`), then `fix_or_show_unused_code` only if `(args.fix or args.dry) and unused_names` (`:23-24`), then `get_unused_names_error_message` (`:26`). Returns `error_message + ('\n\n' + file_diff if file_diff else '')` (`:27`).
- `find_unused_names` (`deadcode/actions/find_unused_names.py:9-23`) runs two AST passes: `FindUnusedCodeVisitor` (detection) then `FixUnusedCodeVisitor` (computes `additional_code_parts_to_remove`). Returns `(unused_code_items, additional_code_parts_to_remove)`.
- `--fix` parse: `action='store_true'`, default `False` (`parse_arguments.py:31-35`). `--dry`: `nargs='*'`, `action='append'`, default sentinel `[['__all_files__']]` (`:37-43`). Normalization removes the sentinel unless `--dry` was given bare (`:204-205`), and forces `args.fix=False` when `args.dry` is truthy (`:208-209`) — `--dry` wins over `--fix`.
- `fix_or_show_unused_code` (`deadcode/actions/fix_or_show_unused_code.py:15-67`): groups items by filename (`:26-28`), flattens `code_parts` + `additional_code_parts_to_remove` (`:33-35`), `merge_overlaping_file_parts` (`:37`), reads lines (`:39-40`), `remove_file_parts_from_content` (`:42`). Then: if file becomes empty → `os.remove` (`:63`); elif `args.dry` matches filename → build `difflib.unified_diff`, append `'\n'`, color unless `--no-color` (`:45-56`); elif `args.fix` → write file (`:58-61`).
- So `--dry` produces the colored unified-diff string appended to the report and never writes; `--fix` writes files and adds a "Removed N unused code item(s)!" summary (`get_unused_names_error_message.py:29-33`).

## Q3: Removing file parts; line/column ranges

### Findings
- `Part` named tuple = `(line_start, line_end, col_start, col_end, insert_code, insert_code_if_character_is_not_removed)` (`deadcode/data_types.py:37-49`).
- Initial coarse `Part` per item built in `FindUnusedCodeVisitor._define`: `Part(first_lineno, last_lineno, last_node.col_offset, last_node.end_col_offset or 0)` (`find_unused_code_visitor.py:313`), with line numbers from `lines.get_first_line_number`/`get_last_line_number`.
- Refined sub-ranges from `FixUnusedCodeVisitor`: mutate AST node, `ast.unparse` it (`fix_unused_code_visitor.py:161-163`), diff original-vs-unparsed with `difflib.SequenceMatcher`, emit a `Part` for every `"delete"` opcode via `get_chars_to_remove` (`:189-225`) and `convert_1d_part_to_2d` (`:165-187`). `convert_1d_part_to_2d` maps flat char offsets to absolute `(line,col)` using per-line lengths of the original node text and `first_line=node.lineno`, `first_col=node.col_offset`.
- `merge_overlaping_file_parts` (`merge_overlaping_file_parts.py:99-127`): sorts by `(line_start, col_start, -line_end, -col_end)`, drops parts contained in larger ones (`does_include`), merges overlaps (`merge_parts`, `:44-96`). Docs note a copy-paste bug at `merge_overlaping_file_parts.py:11` (`line_end_b == line_end_b`) per `docs/fix-and-output.md:37`.
- `remove_file_parts_from_content` (`remove_file_parts_from_content.py:127-396`): line-by-line. Skips interior lines of a multi-line part (`:162-164`); first line either inline-spliced (`from_line==to_line`, calls `remove_unused_fragments_from_a_line`) or truncated to `line[:from_col]` (`:230`); last line spliced again (`:245`). State flags `has_block_started`, `was_block_removed`, `empty_lines_in_a_row_list`, `empty_lines_before_removed_block_list` govern blank-line suppression after removals (`:332-384`). `pass` is injected when a block header ending in `:` loses its body (`:354-361`, `:388-390`).
- `remove_unused_fragments_from_a_line` (`:60-124`) splices same-line parts via `line[:from_col] + line[to_col:]` and trims line beginnings/ends for parts straddling line boundaries.

## Q4: `with ... as <name>` handling

### Findings
- `FixUnusedCodeVisitor.visit_With` (`fix_unused_code_visitor.py:281-289`): for each `withitem`, if `item.optional_vars` exists and its `.id` is not in `find_unused_code_visitor.used_names`, sets `item.optional_vars = None` (`:287`), then calls `add_code_adjustments_for_cleaned_up_code_items(node)` (`:289`).
- The removable span is computed by diffing the **original** `with` source against `ast.unparse(node)`. `ast.unparse` drops the `as <name>` binding, and `SequenceMatcher` reports the deleted characters.
- Observed runtime behavior (captured test stdout):
  - Module-level `with open("tmp.txt", "r") as unused_var:` → SequenceMatcher opcode `delete a[25:39]=" as unused_var"`; produced line `with open("tmp.txt", "r"):` (clean, `as` fully removed). Confirmed in `test_dry` captured stdout, step 4 "Updated line: with open(\"tmp.txt\", \"r\"):".
  - Nested `with open("example.txt") as unused_file:` (inside `class>method`, 8-space indent) → opcodes `delete a[24:39]=" as unused_file"` **and** `delete a[41:49]` = 8 spaces of the next line's indentation. Cause: `ast.unparse` re-indents the body to 4 spaces, so SequenceMatcher treats the original deeper indentation as deleted, corrupting the `print(...)` body line. Captured `test_fix` stdout shows the body becoming `t("File was openned")` (chars lost).
- Net: the same code path yields a clean rewrite when body indentation matches `ast.unparse` output (module level), and a corrupted body line when it does not (nested).

## Q5: Unused/aliased imports, parenthesized multi-name `from`

### Findings
- Detection: `_add_aliases` (`find_unused_code_visitor.py:212-237`) iterates `node.names` (`ast.alias` list, one per name regardless of parentheses). Registers `_define(self.defined_imports, alias or name, ...)`; the tracked name is the alias when present. When `asname` is set, the original name is immediately marked used (`:236-237`), so only the alias can be flagged unused. `visit_Import`/`visit_ImportFrom` at `:461-471` (skip `__future__`).
- Removal: `FixUnusedCodeVisitor.visit_Import` (`fix_unused_code_visitor.py:339-359`, `visit_ImportFrom` delegates). Effective names `e.asname or e.name.partition('.')[0]` reversed (`:347`); `names_to_remove` = those not in `used_names` (`:348`). If all removed → `remove_node(node)` removes whole statement (`:351`, `remove_node` `:276-279`). Otherwise `remove_from_list(node.names, ...)` mutates names in place (`:357`, helper `deadcode/utils/remove_from_list.py:4`), then `add_code_adjustments_for_cleaned_up_code_items(node)` (`:359`).
- For parenthesized multi-name `from m import ( a, b, c )`: original spans multiple lines; `ast.unparse` produces single line `from m import (b, c)` (or `from m import b`). `SequenceMatcher` deletes cover the dropped names and surrounding parens/whitespace; `convert_1d_part_to_2d` maps these multi-line char offsets back to `(line,col)` `Part`s. Test comment records detected parts as `[Part(1,3,17,4), Part(3,5,20,2)]` (`tests/fix/test_unused_imports_in_a_single_file.py:224`).

## Q6: Colored unified diff generation

### Findings
- Diff built in `fix_or_show_unused_code.py:47` via `difflib.unified_diff(original_lines, updated_lines, fromfile, tofile)`; joined and a literal `'\n'` appended (`:48`, comment `:50-51` explains it guards files lacking a trailing newline).
- `add_colors_to_diff` (`deadcode/utils/add_colors_to_diff.py:1-10`): iterates `diff_str.splitlines(True)` (keeps line endings). Lines starting `-` → wrapped `\033[31m...\033[0m` (red); lines starting `+` → `\033[32m...\033[0m` (green). Two independent `if`s (not `elif`). `@@` hunk headers and ` ` context lines pass through unchanged. Applies to file headers `---`/`+++` too. Called only when not `args.no_color` (`fix_or_show_unused_code.py:53-56`).
- Blank lines: no special handling — only the leading char matters. A removed blank line is `-\n` → colored red `\x1b[31m-\n\x1b[0m` (see `tests/utils/test_add_colors_to_diff.py:26-34`). A blank context line is ` \n` and is left unchanged.

## Q7: The three failing tests — asserted vs produced output

Run: `uv run pytest <three files> -o addopts=""` → **3 failed, 27 passed, 2 skipped**.

### 7a. `tests/cli_args/test_dry.py::TestDryCliOption::test_coloring_of_a_diff` (`test_dry.py:240-304`)
- Test asserts the diff `+` line as `with open("tmp.txt", "r") as :` (leftover bare `as`, `test_dry.py:273`).
- Code produces `with open("tmp.txt", "r"):` (clean — `as` fully removed). The test expects the *older buggy* `as :` form; code now emits the cleaner form. Mismatch is exactly ` as ` (4 chars).
- The `assertFiles` part of this test passes (files unchanged under `--dry`).

### 7b. `tests/cli_args/test_fix.py::TestFixCliOption::test_empty_lines_are_removed_properly_indented` (`test_fix.py:126-191`)
- Test expects clean nested rewrite: `with open("example.txt"):` then `            print("File was openned")` preserved, plus 2 trailing blank lines (`test_fix.py:183-184`). Comment `:168` "GOAL: make this method work with multiline code diffs."
- Code produces a **corrupted** body line `t("File was openned")` (lost `prin` + wrong indentation) and drops the trailing blank lines — the nested `with as` over-deletion described in Q4.
- Here the test asserts the *intended/correct* result; code is buggy. (Opposite direction from 7a.)

### 7c. `tests/fix/test_unused_imports_in_a_single_file.py::TestAssignmentExpressionRemoval::test_aliases_are_removed` (`:211-253`)
- Expected file content (`:247-252`) is `from spam import bar as bar_alias\n\nprint(bar_alias)\n` (blank line kept between import and print).
- Code produces `from spam import bar as bar_alias\nprint(bar_alias)\n` (blank line removed). Mismatch is one blank line. The test's inline comment `:242-243` ("This comparison ignores empty lines... I want number of empty lines to be accurate") plus `fix_indent`'s `TODO` (`fix_indent.py:15`) document this empty-line inaccuracy as known.

### Documented intent
- No `docs/`, README, or `notes/` file specifies an exact expected rewrite for `with ... as` removal or for post-import blank-line counts. `notes/` is an empty directory.
- `docs/fix-and-output.md` describes the pipeline and explicitly labels bugs as "Observed bug" (`:37`) rather than prescribing fixed output. README documents only flags and DC codes (`README.md:55-89`), not exact diff formatting.
- Intent for these three cases is expressed **only inside the tests themselves** (assertions + `TODO`/`GOAL` comments), and the three are mutually inconsistent: 7a asserts the buggy `as :` form while 7b/7c assert clean output.

## Cross-Cutting Observations
- `with ... as <name>`, multi-name imports, and multi-target assigns all share one mechanism: mutate AST → `ast.unparse` → `SequenceMatcher` diff → `Part`s (`fix_unused_code_visitor.py:227-236`). Its fragility appears when `ast.unparse` reformats (re-indentation, paren collapse) differently from the original source.
- Blank-line fidelity is governed both by `remove_file_parts_from_content`'s empty-line bookkeeping and by `fix_indent` normalization in the test harness; `fix_indent` removes leading blank lines and is noted to affect interior blanks (`fix_indent.py:15`).
- Tests rely entirely on mocked `open`/`os.remove`/`find_python_filenames` (no disk), with content normalized via `fix_indent` on both read and assert.

## Open Areas
- Exact char-level mechanism of the 7c blank-line loss (whether from `remove_file_parts_from_content` block-removal suppression vs `fix_indent` normalization) was inferred from the assertion diff, not stepped through line by line.
- Whether the code recently changed (making 7a's `as :` expectation stale) vs the tests being aspirational was not verified via git history (out of documentarian scope).

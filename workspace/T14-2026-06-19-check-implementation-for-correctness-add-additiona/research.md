# Research Findings

Scope: the `deadcode/` package — AST visitor, fix pipeline, ignore/noqa layer,
CLI/config parsing, and the `tests/` suite. References use `file:line`.

## Q1: How the visitor traverses the AST and which name categories it tracks

### Findings
- Entry point `visit_abstract_syntax_trees` loops over `self.filenames`, resets
  `self.scope_parts = [module_name]` per file, parses noqa, then calls
  `self.visit(module_node)` (`find_unused_code_visitor.py:98-152`). Empty
  non-dunder files become a `CodeItem(type_='unused_file')`
  (`find_unused_code_visitor.py:145-152`).
- `visit(node)` is a custom dispatcher replacing `generic_visit`
  (`find_unused_code_visitor.py:579-609`): computes `inherits_from`, applies
  ignore-definition/body flags, dispatches `visit_<Class>`, pushes/pops scope,
  visits type comments by re-parsing them (`:556-559`), recurses into children
  via `_visit_children` (`:561-572`), then dispatches
  `visit_<Class>_after_visiting_child_nodes`.
- Nine `LoggingList` collections store defined names, each tagged with a `type_`
  and a DC error code (`find_unused_code_visitor.py:56-64`; codes in
  `ignore.py:23-36`): `defined_attrs`=DC05, `defined_classes`=DC03,
  `defined_funcs`=DC02, `defined_imports`=DC07, `defined_methods`=DC04,
  `defined_props`=DC08, `defined_vars`=DC01, `unused_file`=DC11,
  `unreachable_code`=DC09. `used_names` is a `LoggingSet` of plain strings
  (`find_unused_code_visitor.py:66`; `utils.py:76-85`).
- All definitions funnel through `_define` (`find_unused_code_visitor.py:273-334`),
  which builds a `CodeItem` (name, type_, filename, scope, `code_parts=[Part]`,
  name line/col, inherits_from), registers it in `self.scopes` (NestedScope),
  evaluates ignore rules, and either marks the name used or appends to the list.
- Category dispatch:
  - **Functions/methods/properties**: `visit_FunctionDef`
    (`:446-465`); `visit_AsyncFunctionDef` delegates to it (`:348-349`).
    `@property` → `defined_props`; `@staticmethod`/`@classmethod` or
    `first_arg == 'self'` → `defined_methods`; else `defined_funcs`.
  - **Classes**: `visit_ClassDef` (`:438-444`).
  - **Imports**: `visit_Import`/`visit_ImportFrom` → `_add_aliases`
    (`:211-236`); only top-level module name stored (`name.partition('.')[0]`,
    `:222`); `__future__` skipped (`:482-483`).
  - **Variables/names**: `visit_Name` (`:497-501`) — Load/Del → `add_used_name`;
    Param/Store → `_define_variable` (`:336-342`).
  - **Attributes**: `visit_Attribute` (`:351-355`) — Store → `defined_attrs`,
    Load → `add_used_name`.
- Scope is `'.'.join(self.scope_parts)` (`:85-86`), pushed for Class/Function
  defs only (`:547-553`). `visit_arg` is commented out (`:344-346`) — function
  args are not tracked as defined.

## Q2: Used vs. unused classification logic and edge cases

### Findings
- Core test: `unused_items = [i for i in defined_items if i.name not in
  used_names]` (`ignore.py:39-42`). Membership is by **bare name string**, not
  scoped/typed/file-qualified. `CodeItem.__eq__`/`__hash__` are name-only
  (`code_item.py:130-139`), so a name used anywhere marks all same-named
  definitions used everywhere. `number_of_uses` is incremented
  (`nested_scopes.py:83`) but never consulted by the final check.
- **`__all__`**: `visit_Assign` + `_assigns_special_variable__all__`
  (`find_unused_code_visitor.py:503-508`; `ignore.py:66-70`) adds each string
  literal element to `used_names`. Only literal list/tuple of string constants
  handled; dynamic `__all__` not.
- **String references**: `getattr`/`hasattr(obj, "name")` literal arg
  (`:373-379`); `"%(name)s" % locals()` via `visit_BinOp` regex (`:357-369`);
  `"{name}".format(**locals())` via `_handle_new_format_string` (`:381-409`).
  Both format paths require a literal `locals()` call (`_is_locals_call`,
  `:412-420`).
- **Dunders / privates**: `_ignore_method` and `_ignore_variable` ignore
  `__x__` (`_is_special_name`, `ignore.py:45-46,91-93,96-105`); variables
  starting with single `_` are also ignored (pylint convention,
  `ignore.py:97-99`). Dunder classes/functions are NOT auto-ignored.
- **Scope isolation — documented limitation**: `used_names` is global/flat.
  `nested_scopes.py:65` comment: `mark_as_used` "does not work when methods are
  invoked" (instance/class context ignored). `nested_scopes.py:41-45` TODO:
  flat module-stem scope causes cross-directory same-name collisions.
- **Import alias workaround**: aliased imports store only the alias but
  immediately mark the original name used (`:234-236`, comment acknowledges).
  `import os.path` tracked as `os`, not `os.path` (`:220` TODO).
- **Test-file heuristics**: `_is_test_file` (`ignore.py:58-63`) auto-ignores
  `Test*` classes, `test_*`/`setup_*`/`teardown_*` funcs and methods
  (`ignore.py:73-93`).
- **No name-mangling handling** (`__attr` → `_Class__attr`); literal string
  lookup only.
- **Other documented gaps (comments)**: `:89-93` usage-on-CodeItem TODO;
  `:476-479` empty `visit_Import_after_visiting_child_nodes` stub; `:284-289`
  stale "not implemented yet" log for ignore_definitions* (they ARE applied via
  `_apply_ignore_definitions`); `code_item.py:1-28` filename TODO + commented
  `VariableInfo` blueprint.

## Q3: Fix pipeline — parts, merge, reassembly

### Findings
- **`Part`** NamedTuple: `line_start, line_end` (1-indexed inclusive),
  `col_start, col_end` (0-indexed), `insert_code`,
  `insert_code_if_character_is_not_removed` (`data_types.py:38-51`). Each
  `CodeItem.code_parts` is a `list[Part]` (`code_item.py:44,62-80`).
- **Part computation**: `_define` builds one `Part(first_lineno, last_lineno,
  col_offset, end_col_offset or 0)` (`find_unused_code_visitor.py:300-319`).
  Lines from `lines.get_first_line_number` (first decorator if any,
  `lines.py:69-82`) and `get_last_line_number` (recursive max over last children,
  `lines.py:41-66`).
- **Additional parts** from `FixUnusedCodeVisitor` (second AST pass) into
  `additional_code_parts_to_remove: dict[Filename, list[Part]]`: full-node
  removal `remove_node` (`fix_unused_code_visitor.py:258-267`); partial removal
  diffs original source vs `ast.unparse` output with `SequenceMatcher`, mapping
  `'delete'` opcodes via `convert_1d_part_to_2d` (`:142-212`).
- **Collection**: `_compute_updated_content` flattens
  `[item.code_parts ...]` and extends with the file's additional parts
  (`fix_or_show_unused_code.py:15-24`).
- **Merge** `merge_overlaping_file_parts` (`merge_overlaping_file_parts.py:89-117`):
  sort by `(line_start, col_start, -line_end, -col_end)` (`:95`); O(n²) sweep —
  `does_include` (`:4`) drops contained parts, `does_overlap` (`:27`) triggers
  `merge_parts` (`:38-86`) which keeps earliest start, latest end, and the
  earlier part's `insert_code`. (`does_include` has a self-comparison at `:10`.)
- **Reassembly** `remove_file_parts_from_content` (`remove_file_parts_from_content.py:353-410`)
  reads `f.readlines()` (`fix_or_show_unused_code.py:27`) and iterates lines via a
  `_RemovalState`, four branches: interior multi-line → skip (`:385`); first line
  → `_handle_first_line` (`:390`, slices `line[:from_col]`/`line[:from_col]+line[to_col:]`,
  `:143-214`); last line → `_handle_last_line` (`:394`, `line[to_col:]`); kept
  line → `_handle_normal_line` (`:398`, manages blank lines, injects `pass\n`
  after an emptied block whose header ends in `:`, `:301-350`). Final trailing
  `pass` appended if needed (`:404`).
- **Emit**: `_emit_for_file` writes (`--fix`), prints `unified_diff` (`--dry`),
  or `os.remove`s fully-emptied files (`fix_or_show_unused_code.py:32-51`).

## Q4: Ignore and noqa mechanisms

### Findings
- **Config options** are `Args` fields (`data_types.py:15-36`) parsed in
  `parse_arguments.py`. Suppression-relevant: `ignore_names` (`:49-59`),
  `ignore_names_in_files` (`:151-158`), `ignore_definitions` (`:84-93`),
  `ignore_definitions_if_inherits_from` (`:94-104`), `ignore_bodies_if_inherits_from`
  (`:76-83`), plus several parsed-but-unused options:
  `ignore_bodies_of`, `ignore_bodies_if_decorated_with`,
  `ignore_definitions_if_decorated_with`, `ignore_if_decorated_with`,
  `ignore_if_inherits_from`, `ignore_names_if_decorated_with`,
  `ignore_names_if_inherits_from` (defined but not read by the visitor).
- **Glob matching**: `_match` uses `fnmatchcase`/`fnmatch` (`ignore.py:49-51`);
  `_match_many` (`:54-55`). `ignore_names` matched vs name (`:294`),
  `ignore_names_in_files` vs file path (`:295`), `ignore_definitions` vs node
  name (`:524`), `*_if_inherits_from` vs base-class names (`:525,534`).
- **Hardcoded heuristics** via `_ignore_*` predicates passed as `ignore=` to
  `_define`: variables (`ignore.py:96-105`), methods (`:90-93`), functions
  (`:86-87`), classes (`:73-74`), imports — `__init__.py` and `*` star
  (`:77-83`). Test-file detection: `*/test/*`, `*/tests/*`, `*/test*.py`,
  `*[-_]test.py` (`:58-63`).
- **Decorators**: `@property`→props, `@staticmethod`/`@classmethod`→methods;
  any decorator in `self.ignore_decorators` skips the def entirely
  (`:440-442,458-459`) — but `ignore_decorators` is `[]` with no CLI wiring
  (`:50`). `get_decorator_name` normalizes names (`utils.py:53-61`).
- **`should_ignore_new_definitions` flag**: set by `_apply_ignore_definitions`
  (name or inherits match, `:518-530`) and `_apply_ignore_bodies` (inherits
  match, `:532-538`); cleared after children visited (`:606-607`); when set,
  `ignored()` returns True (`:296`). `inherits_from` built transitively by
  `get_inherits_from` (`:422-436`).
- **Noqa**: `parse_noqa(code)` (`noqa.py:54-62`) builds `dict[code -> set[int]]`
  via `NOQA_REGEXP` (`noqa.py:4-14`, IGNORECASE) — accepts bare `# noqa`
  (→ key `'all'`, `:51`), `# noqa: DC02`, comma lists, 3-digit legacy. `NOQA_CODE_MAP`
  (`:16-46`) maps native DC01–DC09/DC11–DC13, legacy 3-digit, and flake8
  `F401→DC07`, `F841→DC01` (DC10 absent). `ignore_line` (`:65-67`) checks the
  code set plus `'all'`.
- **Pipeline stage**: all suppression happens during the AST visit inside
  `_define` (`:291-334`) — suppressed names get `add_used_name` (`:332`) and are
  never collected. `parse_noqa` runs before `self.visit` (`:109`). Reporting
  (`get_unused_code_items` `:154-171`, `_get_unused_items` `ignore.py:39-42`)
  and fix do no further suppression.

## Q5: CLI and configuration parsing

### Findings
- **pyproject.toml**: `parse_pyproject_toml` (`parse_arguments.py:210-224`)
  checks `pyproject.toml` in CWD only (no upward traversal), `tomllib.load`,
  reads `[tool.deadcode]`, normalizes keys (`--`/`-`→`_`), returns `{}` if
  absent.
- **CLI options** (`parse_arguments.py:25-186`): positional `paths` (nargs=+);
  bool flags `--fix`, `--no-color`, `--quiet`, `--count`, `-v/--verbose`
  (default False); list options (`nargs='*' action='append'`, default `[]`):
  `--dry` (sentinel default `[['__all_files__']]`), `--exclude`,
  `--ignore-names`, and all the `--ignore-*` variants (`:60-158`).
- **Precedence/merge** (`:195-197`): CLI parsed first, pyproject values
  `.extend()`-ed onto the flattened CLI lists — concatenation, NOT override; CLI
  values come first. Only list args merged.
- **Normalization**: `flatten_lists_of_comma_separated_values` flattens
  append-lists and splits comma-separated tokens (`flatten_lists.py:6-12`),
  applied to all list args except `paths` (`:190-192`). `--dry` sentinel logic
  (`:200-205`): removes `'__all_files__'` unless `--dry` given without args;
  non-empty `dry` forces `fix=False`.
- **Args dataclass** (`data_types.py:14-35`): list fields `Iterable[Pathname]`
  (`Pathname=str`), bool fields default False.
- **Detection-affecting**: `paths`, `exclude` (`find_python_filenames.py:10-33`),
  `ignore_names` (`:294`), `ignore_names_in_files` (`:295`),
  `ignore_definitions`/`_if_inherits_from` (`:524-525`),
  `ignore_bodies_if_inherits_from` (`:534`). The other `ignore_*` options are
  parsed but not consumed.
- **Fix/output-affecting**: `--fix` writes (`fix_or_show_unused_code.py:46-49`),
  `--dry` diffs (`:35-45`), `--quiet`/`--count` change message (`cli.py:27`),
  `--no-color` skips coloring (`:43-45`), `--verbose` checked in
  `find_python_filenames.py:17,31` (visitor verbose hardcoded False at
  `find_unused_code_visitor.py:52-53`).

## Q6: Test-suite organization and conventions

### Findings
- **`BaseTestCase`** (`deadcode/utils/base_test_case.py`): class attr `files`
  (virtual filename→source), `maxDiff=None` (`:11-13`); `patch()` helper auto-
  cleanup (`:15-18`); `setUp` patches `find_python_filenames`, three `open`
  seams, `os.remove`, and `parse_pyproject_toml`→`{}` (`:37-57`).
- **Mock filesystem**: `_read_file_side_effect` serves `self.files[...]` via
  `fix_indent`, captures writes into `self.updated_files` (`:23-35`);
  `find_python_filenames` returns `list(self.files.keys())` (`:40-41`). Real-disk
  tests use `tempfile.TemporaryDirectory` (`actions/test_find_python_filenames.py`,
  `cli_args/test_exclude.py`) or `os.chdir(REPO_ROOT)` (`test_deadcode.py:13-71`).
- **Assertion helpers**: `assertFiles(files, removed=None)` compares fixed
  content via `fix_indent` and checks `os.remove` calls (`:59-85`);
  `assertUpdatedFiles` defined (`:87-96`) but used by zero tests.
- **Conventions**: detection tests `assertEqual(unused_names,
  'file:line:col: DCxx ...')` (`test_deadcode.py:22`, `test_imports.py:67`); fix
  tests add `assertFiles({...})`; `--dry` tests compare unified-diff strings
  (`cli_args/test_dry.py`); `--count` returns numeric string
  (`test_line_number_detection.py:19`); `--quiet` returns `''`
  (`test_output.py:73`). Mixed `assert` vs `self.assertEqual`; one
  `pytest.raises` (`visitor/test_fix_unused_code_visitor.py:15`).
- **Covered constructs**: globals/tuple-assign/lambda vars, functions/closures,
  classes, methods, imports (alias, multi-name, parenthesized, relative, dotted
  attribute), async def + @property (smoke-only via `_run()`), decorator
  whitelisting, `__all__`, `getattr`, `%`/`.format` locals, ternary, type
  comments, unreachable-after-return, attribute store, MatchClass, with-as var,
  noqa per-code + all, empty-file removal, multi-parent/inner-class inheritance,
  `--ignore-definitions[-if-inherits-from]`, `--ignore-names` globs, syntax
  errors → None. Fix mechanics: var/func/class/method removal, `pass` insertion,
  blank-line preservation, `--dry`, multi-file.
- **Gaps (`@skip`/empty/stub)**: DC05, DC06, DC08, DC09, DC13 noqa tests skipped
  (`noqa/test_noqa_comments.py:142-339`); tuple-unpacking fix + typed-var fix
  skipped (`fix/test_assign.py:34-92`); type-tracking-across-calls skipped
  (`nested_scope/test_nested_scope.py:133-188`,
  `test_accurate_usage_detection.py:8-49`); entire `TestVariableScopeTracking`
  skipped (`fix/test_scope.py:11-244`); multi-level inheritance skipped
  (`cli_args/test_ignore_definitions_if_inherits_from.py:62-125`);
  cross-file/same-name disambiguation skipped (`fix/test_class_def.py:62-117`);
  `if False`/redundant-else removal skipped (`cli_args/test_fix.py:349-394`);
  stub `pass` bodies (`test_imports.py:94-101`); empty
  `VariableParsingTests` (`test_variable_parsing_from_ast_dump.py:11-12`); empty
  `cli_args/test_{count,verbose,quiet,no_color}.py`; no async-detection return
  assertion; no decorator-removal fix; no comprehension-scope test;
  `assertUpdatedFiles` unused; merge-same-line test has TODO/commented assertion
  (`actions/test_merge_overlaping_file_parts.py:54-67`).

## Cross-Cutting Observations
- The single source of truth for "used" is the flat `used_names: set[str]`;
  every suppression path (config, noqa, heuristics, `__all__`, alias workaround)
  works by injecting names into that set during the AST pass, so all filtering is
  complete before reporting/fix (`find_unused_code_visitor.py:291-334`).
- Name-only `CodeItem` equality (`code_item.py:130-139`) plus flat scope
  (`nested_scopes.py:41-45,65`) is the root of documented scope/collision
  limitations and several skipped scope tests.
- Detection runs in one AST pass; fixing runs a separate second pass
  (`FixUnusedCodeVisitor`) that computes additional removal `Part`s via
  `ast.unparse` + `SequenceMatcher` diffing.
- Multiple `Args` ignore-options are parsed but unconsumed (Q4/Q5), and the
  `ignore_decorators` list has no CLI wiring (`:50`).

## Open Areas
- Whether the parsed-but-unused `ignore_*` options are referenced anywhere
  beyond the visitor was not exhaustively traced outside `find_unused_code_visitor.py`
  and `parse_arguments.py`.
- Exact runtime behavior of the multi-part same-line merge ordering is flagged by
  a TODO in tests (`actions/test_merge_overlaping_file_parts.py:54-67`) but not
  independently re-derived here.

# Research Findings

Scope: the `deadcode/` Python package — a CLI tool that detects (and optionally
removes) unused Python code via AST analysis. All references are `file:line`.

## Q1: Top-level execution flow (entry point → output / file modification)

### Findings
- Console script registered at `pyproject.toml:38`: `deadcode = "deadcode.cli:main"`.
- `main(command_line_args=None) -> Optional[str]` at `cli.py:12-31` runs five sequential steps:
  1. `parse_arguments(command_line_args)` → `Args` (`cli.py:15`, `parse_arguments.py:15`).
  2. `find_python_filenames(args=args)` → `List[str]` (`cli.py:17`, `find_python_filenames.py:11`).
  3. `find_unused_names(filenames, args)` → `Tuple[Iterable[CodeItem], dict[Filename, List[Part]]]` (`cli.py:20`, `find_unused_names.py:9`).
  4. Conditional `fix_or_show_unused_code(...)` → `str` (diff text or `''`), only when `(args.fix or args.dry) and unused_names` (`cli.py:23-24`).
  5. `get_unused_names_error_message(unused_names, args)` → `Optional[str]` (`cli.py:26`).
- Return / exit logic (`cli.py:26-31`): if `error_message is not None`, `main` returns the message with the diff appended (`+ '\n\n' + file_diff` when present). Otherwise prints `'\033[1mWell done!\033[0m ✨ 🚀 ✨'` (unless `--count`/`--quiet`) and returns `None`.
- There is **no `sys.exit()`** anywhere in `cli.py`; the `__main__` guard at `cli.py:34-35` just calls `main()`. Exit-code/printing is handled by the console-script wrapper, not by `main` itself.
- `find_unused_names` orchestrates two visitor passes: `FindUnusedCodeVisitor` (collects defined/used names), then `FixUnusedCodeVisitor` (second AST pass producing `additional_code_parts_to_remove`) (`find_unused_names.py:9-24`).

## Q2: Argument & pyproject.toml parsing, merging, representation

### Findings
- Parser built in `parse_arguments.py:28`; falls back to `sys.argv[1:]` when `None` (`parse_arguments.py:25`).
- Positional `paths` (`nargs='+'`); two `store_true` flags beyond `--fix`: `--no-color`, `--quiet`, `--count`, `-v/--verbose`. All other options are list-valued (`nargs='*', action='append'`): `--dry`, `--exclude`, `--ignore-names`, `--ignore-names-in-files`, `--ignore-bodies-of`, `--ignore-bodies-if-decorated-with`, `--ignore-bodies-if-inherits-from`, `--ignore-definitions`, `--ignore-definitions-if-inherits-from`, `--ignore-definitions-if-decorated-with`, `--ignore-if-decorated-with`, `--ignore-if-inherits-from`, `--ignore-names-if-inherits-from`, `--ignore-names-if-decorated-with`.
- `--dry` default is the sentinel `[['__all_files__']]`; all list flags otherwise default `[]`.
- Flattening: every list field except `paths` passes through `flatten_lists_of_comma_separated_values` (`parse_arguments.py:194-196`, defined `utils/flatten_lists.py:6-12`) — flattens nested append-lists AND splits comma-separated tokens into one flat `List[str]`.
- pyproject.toml: `parse_pyproject_toml()` (`parse_arguments.py:214-229`) reads `pyproject.toml` from CWD via `tomllib`/`tomli`, extracts `[tool.deadcode]`, normalizes keys (strip `--`, `-`→`_`). Merge loop (`parse_arguments.py:199-201`) `.extend()`s each value onto the matching already-flattened CLI list — only existing list keys merge; bool flags from config are not merged here.
- `--dry` post-processing (`parse_arguments.py:204-209`): removes `'__all_files__'` sentinel if explicit dry filenames given; if `dry` non-empty, forces `fix=False`.
- Result built `Args(**parsed_args)` (`parse_arguments.py:211`); flows as `args=` into every downstream stage.
- `Args` is a `@dataclass` (`data_types.py:13-34`) with 20 fields: `fix/verbose/no_color/quiet/count: bool = False`, plus `dry/paths/exclude/ignore_*: Iterable[Pathname] = ()`. `Pathname = str` (`data_types.py:10`).

## Q3: AST-traversal layer in `visitor/`

### Findings
- Parsing: `parse_abstract_syntax_tree` calls `ast.parse(content, filename, type_comments=True)`; returns empty `ast.Module()` on exception (`parse_abstract_syntax_tree.py:6-13`).
- Entry: `FindUnusedCodeVisitor.visit_abstract_syntax_trees` loops files, sets root scope `scope_parts=[module_name]`, runs `noqa.parse_noqa`, parses, stores `file_content_lines`, calls `self.visit(node)` (`find_unused_code_visitor.py:98-153`). Empty non-dunder files → `CodeItem(type_='unused_file')` (`find_unused_code_visitor.py:146-153`).
- Custom `visit()` dispatcher (`find_unused_code_visitor.py:506-587`): attaches `node.inherits_from` via `get_inherits_from` (recursive base resolution); applies `ignore_definitions[_if_inherits_from]` gate (`519-528`); calls `visit_<Class>` pre-children; pushes scope for `ClassDef`/`FunctionDef`/`AsyncFunctionDef` (`540-541`); applies `ignore_bodies_if_inherits_from` gate after scope push (`547-550`); parses `type_comment`; recurses children via `ast.iter_fields` with `_handle_ast_list` for unreachable-code detection; calls `visit_*_after_visiting_child_nodes`; pops scope + resets `should_ignore_new_definitions` (`582-587`).
- DEFINED collectors → all route through `_define()` (`find_unused_code_visitor.py:274-328`): `visit_FunctionDef/AsyncFunctionDef` classify property/method/function by decorators+`self` (`342-453`), `visit_ClassDef` (`426-432`), `visit_Import`/`visit_ImportFrom`→`_add_aliases` (`461-471`, `212-237`; skips `__future__`, stores top-level module name, marks `asname` originals used), `visit_Name` Store/Param→`_define_variable` (`485-489`), `visit_Attribute` Store (`345-349`).
- USED collectors → `add_used_name` (`find_unused_code_visitor.py:88-96`): `visit_Name` Load/Del (`487`), `visit_Attribute` Load (`349`), `visit_Call` handles `getattr/hasattr` string args + `str.format(**locals())` (`360-378`), `visit_BinOp` handles `"%(x)s" % locals()` (`351-358`), `visit_Assign` extracts `__all__` members (`491-496`), `visit_MatchClass` kwd_attr (`502-504`).
- `_define()` builds `CodeItem` with `Part(first_lineno, last_lineno, col_offset, end_col_offset)` (linenos via `lines.get_first/last_line_number`, which walk decorators/child chains, `lines.py:41-82`), registers in `self.scopes.add()`, then evaluates inner `ignored()` (`293-300`). If ignored → `add_used_name(name)` (treated as used); else appended to the `defined_*` list.
- Scope: `scope_parts: List[str]` (`73`), root=module name; `scope` property joins with `.` (`85-86`). Backed by `NestedScope` (`nested_scopes.py:6`): `add` walks/creates nested dicts, `get` searches innermost→outermost, `mark_as_used` increments `number_of_uses`.
- noqa: `parse_noqa` scans lines with flake8-style `NOQA_REGEXP` (`noqa.py:5-15,55-63`); codes normalized via `NOQA_CODE_MAP` (e.g. `F401→DC07`, `F841→DC01`, `DC001→DC01`; `noqa.py:17-47`); bare `# noqa` → key `'all'`. `ignore_line(noqa_lines, lineno, code)` checks code-set or `'all'` (`noqa.py:66-68`); invoked in `_define` as `noqa.ignore_line(..., first_lineno, ERROR_CODES[type_])` (`find_unused_code_visitor.py:299`, `ERROR_CODES` map `ignore.py:23-36`).

## Q4: Deciding "unused" + ignore/exclude mechanisms

### Findings
- Core decision: `_get_unused_items(defined_items, used_names)` returns items whose `.name not in used_names`, sorted case-insensitively (`ignore.py:39-42`). `used_names` is a flat global `Set[str]` across all files — name-string comparison, not scope-aware at decision time.
- 8 `unused_*` properties (`find_unused_code_visitor.py:174-200`) each call `_get_unused_items`; `get_unused_code_items()` chains them + `unused_file`, sorts by `(filename, name_line)` (`155-172`).
- `ignore-names`: `_match(name, args.ignore_names)` in `ignored()` (`297`) using `fnmatchcase`; match → `add_used_name`.
- `ignore-names-in-files`: `_match(self.filename, args.ignore_names_in_files)` (`298`) — whole file's defs treated as used.
- `ignore-definitions` / `ignore-definitions-if-inherits-from`: gate in `visit()` (`519-528`) sets `should_ignore_new_definitions=True`, suppressing the node + nested defs (their names added to used). `inherits_from` includes transitively resolved ancestors.
- `ignore-bodies-if-inherits-from`: gate after scope push (`547-550`) suppresses defs within the class body only.
- Built-in type predicates (`ignore.py`): `_ignore_variable` (`96-105`: `{'object','self'}`, leading `_` non-dunder, dunders), `_ignore_function` (`86-87`: pytest lifecycle / `test_*` in test files), `_ignore_method` (`91-93`: dunder methods, pytest names in test files), `_ignore_class` (`73-74`: `'Test'` substring in test files), `_ignore_import` (`77-83`: `__init__.py`, star imports). `_is_test_file` globs `*/test/*`,`*/tests/*`,`*/test*.py`,`*[-_]test.py` (`58-63`). `IGNORED_VARIABLE_NAMES={'object','self'}` (`ignore.py:9`).
- **Decorator-based fields are largely inert**: `ignore_definitions_if_decorated_with`, `ignore_bodies_if_decorated_with`, `ignore_if_decorated_with`, `ignore_names_if_decorated_with`, `ignore_names_if_inherits_from`, `ignore_if_inherits_from` exist in `Args` but are NOT referenced in `find_unused_code_visitor.py`/`ignore.py`. The only decorator gate is `self.ignore_decorators` (`find_unused_code_visitor.py:50`), checked in `visit_ClassDef`/`visit_FunctionDef`, but it is always `[]` and never assigned. (See Open Areas.)

## Q5: Fix/output stage

### Findings
- `fix_or_show_unused_code(unused_items, additional_code_parts_to_remove, args) -> str` (`fix_or_show_unused_code.py:15`): groups items by filename (`26-28`); per file flattens `item.code_parts` (each a `List[Part]`) + `additional_code_parts_to_remove[filename]` (`32-37`); `merge_overlaping_file_parts(file_parts)`; reads file `readlines()`; `remove_file_parts_from_content(...)` → updated lines (`39-43`). Then: if result blank → `os.remove(filename)` (`63`); elif `args.dry` (+ pattern/`__all_files__` match) → `unified_diff(...)` joined, colored via `add_colors_to_diff` unless `args.no_color` (`45-56`); elif `args.fix` → `f.write(updated_file_content)` (`58-61`). Returns `''.join(result)` or `''`.
- `merge_overlaping_file_parts(parts) -> List[Part]` (`merge_overlaping_file_parts.py:99`): sorts by `(line_start, col_start, -line_end, -col_end)` (`105`); for each part checks `does_include` (skip, `5`), else `does_overlap` (`30`) → `merge_parts` (`44`, spans outer boundaries, first-start wins `insert_code`); replaces accumulator entry or appends. Note: `does_include` line 11 has copy-paste `line_end_b == line_end_b`.
- `remove_file_parts_from_content(content_lines, parts) -> List[str]` (`remove_file_parts_from_content.py:127`): line-by-line cursor over sorted parts; handles inside-block skip, single-line column slicing via `remove_unused_fragments_from_a_line` (`184`), multi-line truncation, `insert_code` appending, empty-line bookkeeping, and `pass`-insertion to keep emptied `class`/`def`/`if` blocks valid (`354-361`, EOF case `388-390`).
- `get_unused_names_error_message(unused_names, args) -> Optional[str]` (`get_unused_names_error_message.py:7`): `None` if empty (`10-11`); `''` if `--quiet` (`13-14`); count string if `--count` (`17`); else per-item lines using `item.filename_with_position` + red error code + `item.message` or `"<Type> \`name\` is never used"` (`21-24`); strips ANSI if `--no-color` (`26`); appends `"Removed N unused code item(s)!"` if `--fix` (`30`).
- Helpers in `utils/`: `add_colors_to_diff` wraps `-`/`+` diff lines in red/green ANSI (`add_colors_to_diff.py:1`); `fix_indent` strips common leading whitespace (`fix_indent.py:5`, used for normalization/tests, not the diff path).

## Q6: Shared data structures & constants

### Findings
- `data_types.py`: aliases `AbstractSyntaxTree = ast.Module` (`7`), `FileContent = str` (`8`), `Filename = str` (`9`), `Pathname = str` (`10`). `Args` dataclass (`13-34`). `Part` is a `NamedTuple` (`37-49`): `line_start, line_end, col_start, col_end: int`, `insert_code: str|None=None`, `insert_code_if_character_is_not_removed: tuple[int,int]|None=None` — the atomic removal/replace region consumed by merge/remove.
- `visitor/code_item.py`: `CodeItem` is a plain `__slots__` class (TODO at `:39` notes "should be dataclass"). Fields: `name, type_ (UnusedCodeType), filename (Path), code_parts (List[Part]=[]), scope, inherits_from, name_line, name_column, message='', error_code, number_of_uses=0`. `error_code` derived via `ERROR_TYPE_TO_ERROR_CODE[type_]` at `__init__` (`code_item.py:83`). Properties: `scoped_name` (`90`, `f'{scope}.{name}'`), `filename_with_position` (`94`, `filename:line:col:`). `__eq__`/`__hash__` use `name` only (`131,139`) — comparable to a `str`, hashable by name.
- `constants.py`: `UnusedCodeType` Literal of 12 values (`4-17`); `UnusedCodeErrorCode` Literal `DC01..DC09, DC11, DC12, DC13` (DC10 skipped) (`20-33`); `ERROR_TYPE_TO_ERROR_CODE` dict (`36-49`) e.g. variable→DC01, function→DC02, class→DC03, method→DC04, attribute→DC05, name→DC06, import→DC07, property→DC08, unreachable_code→DC09, unused_file→DC11, commented_out_code→DC12, ignore_expression→DC13.
- No `UnusedCodeMessage` type exists — "message" is just `CodeItem.message: str`.
- Inter-stage flow: `Args` → `find_unused_names` returns `CodeItem`s (each carrying `List[Part]`) + raw-coordinate dict → fix stage extracts/merges `Part`s → `remove_file_parts_from_content` applies `insert_code`/deletions.

## Q7: Testing & tooling layout

### Findings
- `tests/` groups: `cli_args/` (one file per flag), `fix/` (removal output by AST node type), `noqa/` (DC01–DC13 suppression, `test_noqa_comments.py`), `nested_scope/`, `code_item/` (plain `unittest.TestCase`), `utils/` (plain TestCase), `actions/` (direct action-function unit tests), `files/` (on-disk fixtures used by `test_deadcode.py`). Top-level: `test_deadcode.py`, `test_output.py`, `test_accurate_usage_detection.py`, `test_imports.py`, `test_line_number_detection.py`, `test_variable_parsing_from_ast_dump.py`.
- `BaseTestCase` (`deadcode/utils/base_test_case.py:10`) extends `unittest.TestCase`; class attr `files: Dict[str,str]={}` (`:11`). `setUp` (`37-54`) resets `updated_files`, patches `find_python_filenames` → `_get_filenames`, patches `open` in the two visitor modules + `fix_or_show_unused_code`, patches `os.remove`, builds fresh `Args()`. `_read_file_side_effect` (`23-35`) returns a MagicMock whose `read`/`readlines` serve `fix_indent(self.files[...])` and whose `write` captures into `updated_files`. Assertions: `assertFiles(files, removed=None)` (`56-82`) and `assertUpdatedFiles` (`84-93`). Tests declare virtual files via `self.files = {...}`, call `main([...])`, assert return string + `assertFiles`.
- Some tests bypass `BaseTestCase`: `tests/code_item/test_code_item.py:7`, `tests/test_deadcode.py:7` (real filesystem), `tests/utils/*` use plain `TestCase`.
- Commands — `Makefile`: `make test` (`pytest -vv`), `make lint` (`ruff check`), `make format`, `make mypy`, `make deadcode`, `make audit` (`pip-audit`), `make check` (test+lint+mypy+audit+deadcode), `make publish` (hatch build/publish), `make .venv`/`sync`/`compile`.
- `Justfile`: single `lifecycle` recipe — `uv pip sync` + `uv pip install -e .[test]` + loop running `uv run lifecycle --max-tasks 1 --prior-tasks "$count"` until non-zero.
- `pyproject.toml`: entry `deadcode = "deadcode.cli:main"` (`38`); runtime dep `tomli>=2.0.1` (`21-23`); test extras incl. hatch/ruff/mypy/pip-audit/pytest/pytest-cov/vupi (`26-35`); build backend hatchling (`44-46`); pytest `addopts = "--cov=. --no-cov-on-fail --cov-fail-under=88.0"` (`209-210`); ruff `line-length=120`, `select=["ALL"]` with ignores, per-file test ignores (`61,153-159`); mypy `strict=true, python_version="3.11"` (`162-170`); `[tool.deadcode]` self-config ignoring `visit_*` etc., `ignore_names_in_files=["deadcode/utils/base_test_case.py"]`, `exclude=["tests"]` (`178-201`).

## Cross-Cutting Observations
- One `Args` dataclass threads through every stage; `Part` (NamedTuple) and `CodeItem` carry state from detection into the fix/output stage.
- Two full AST passes: detection (`FindUnusedCodeVisitor`) then fix (`FixUnusedCodeVisitor`), the latter re-parsing and using `ast.unparse` + `SequenceMatcher` for partial removals (`fix_unused_code_visitor.py:209,165-279`).
- "Ignored" definitions are uniformly modeled by adding the name to `used_names` rather than a separate exclusion set.
- ANSI coloring is manual (`\033[...]`) and stripped on `--no-color`; error codes are `DCxx`, flake8 codes mapped via `NOQA_CODE_MAP`.
- The project dog-foods itself (`make deadcode`, `[tool.deadcode]`, deadcode in test extras).

## Open Areas
- **Decorator/inheritance ignore options partly unimplemented**: `ignore_*_if_decorated_with`, `ignore_if_inherits_from`, `ignore_names_if_inherits_from` are parsed into `Args` but not consulted by the visitor/ignore code (Q4). `self.ignore_decorators` is the only decorator gate and is never populated. This is an observed gap, stated as fact, not a recommendation.
- Exit-code semantics are implicit (no `sys.exit` in `cli.py`); behavior depends on the console-script wrapper printing the returned string (Q1).
- `does_include` contains a likely copy-paste (`line_end_b == line_end_b`, `merge_overlaping_file_parts.py:11`) — noted as observed, not assessed for impact.

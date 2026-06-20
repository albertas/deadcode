# Research Findings

## Q1: Scenario test structure, `main()` invocation, output assertions, and `BaseTestCase`

### Findings
- Scenario tests subclass `BaseTestCase` (`deadcode/utils/base_test_case.py:11`). Fixture files are an **in-memory `dict[str, str]`** assigned to `self.files` — no temp files, no real I/O. Keys are bare paths (`'main.py'`), values are indented triple-quoted source (`tests/frameworks/test_fastapi.py:7-41`).
- `fix_indent()` (`deadcode/utils/fix_indent.py:25-50`) strips the common leading margin so tests can write naturally; applied when serving content (`base_test_case.py:31`) and on both sides of every assertion.
- `setUp` (`base_test_case.py:37-57`) patches five call sites: `cli.find_python_filenames` (returns `list(self.files.keys())`), `open` in `find_unused_code_visitor`, `fix_unused_code_visitor`, and `fix_or_show_unused_code`, plus `os.remove` (captured in `self.os_remove.mock_calls`). It also patches `parse_arguments.parse_pyproject_toml` to return `{}` so no real toml is read. `_read_file_side_effect` (`base_test_case.py:23-35`) returns a MagicMock context manager; writes are captured into `self.updated_files`.
- Tests call the real `main()` from `deadcode/cli.py:10-29` with a plain `list[str]` of CLI args, e.g. `main(['main.py', '--no-color', '--ignore-definitions-if-decorated-with=@app.*'])` (`tests/frameworks/test_fastapi.py:44-51`). `main()` returns `str | None` (formatted message, or `None` when nothing found).
- **Output format** is built by `get_unused_names_error_message` (`deadcode/actions/get_unused_names_error_message.py:19-35`): `{filename}:{line}:{col}: {DC_CODE} {Description}`. The `path:line:col` prefix is `CodeItem.filename_with_position` (`deadcode/visitor/code_item.py:92-99`). With `--no-color`, ANSI escapes are stripped. Findings joined by `\n`; on `--fix`, a blank line + `Removed N unused code item!` summary is appended (`get_unused_names_error_message.py:29-33`).
- Assertions use plain `self.assertEqual(output, 'main.py:31:0: DC02 Function `_unused_helper` is never used')` (`tests/frameworks/test_fastapi.py:53`). Multi-finding example: `test_fastapi.py:73-77`.
- `BaseTestCase` helpers: `assertFiles(files, removed=None)` (`base_test_case.py:59-85`) checks deletions + unchanged + written content after `--fix`; `assertUpdatedFiles` (`base_test_case.py:87-96`) is a stricter written-only variant; `patch()` (`base_test_case.py:15-18`) wraps `mock.patch` with auto-cleanup; `self.args = Args()` default created in setUp.
- **DC codes** defined in `deadcode/constants.py:20-49` (`ERROR_TYPE_TO_ERROR_CODE` at 36-49), consumed in `CodeItem.__init__` (`code_item.py:82`). Codes: DC01 variable, DC02 function, DC03 class, DC04 method, DC05 attribute, DC06 name, DC07 import, DC08 property, DC09 unreachable_code, DC11 unused_file, DC12 commented_out_code, DC13 ignore_expression. (DC10 absent.)
- `tests/frameworks/test_fastapi.py` is the **only** current framework scenario test file.

## Q2: Parsing, storage, and application of ignore options (and which are wired)

### Findings
- All flags declared in `deadcode/actions/parse_arguments.py` via `add_argument` with `nargs='*'`, `action='append'`, `default=[]`. Lines: `--ignore-names` 49-59, `--ignore-bodies-of` 61-67, `--ignore-bodies-if-decorated-with` 68-75, `--ignore-bodies-if-inherits-from` 76-83, `--ignore-definitions` 85-93, `--ignore-definitions-if-inherits-from` 94-104, `--ignore-definitions-if-decorated-with` 105-115, `--ignore-if-decorated-with` 117-124, `--ignore-if-inherits-from` 125-132, `--ignore-names-if-inherits-from` 134-141, `--ignore-names-if-decorated-with` 142-149, `--ignore-names-in-files` 151-158.
- Stored in `Args` dataclass (`deadcode/data_types.py:21-32`), passed into `FindUnusedCodeVisitor` (`find_unused_names.py:14-16`), held as `self.args` (`find_unused_code_visitor.py:48`).
- **Application sites:**
  - `_define()`'s `ignored()` closure (`find_unused_code_visitor.py:284-291`) consumes `ignore_names` (287) and `ignore_names_in_files` (288). When True, name is added to `used_names` instead of a `defined_*` list (322-327).
  - `_apply_ignore_definitions()` (`find_unused_code_visitor.py:520-539`, called at 603) consumes `ignore_definitions` (532), `ignore_definitions_if_inherits_from` (533), `ignore_definitions_if_decorated_with` (534). Sets `should_ignore_new_definitions=True`.
  - `_apply_ignore_bodies()` (`find_unused_code_visitor.py:541-547`, called at 609-611) consumes only `ignore_bodies_if_inherits_from` (543).
  - Timing in `visit()`: `_apply_ignore_definitions` runs before pre-visit (suppresses the container's own name); `_apply_ignore_bodies` runs after the container is defined but before body children (suppresses only body members).

| Option | Verdict | Evidence |
|---|---|---|
| `ignore_names` | APPLIED | `find_unused_code_visitor.py:287` |
| `ignore_names_in_files` | APPLIED | `find_unused_code_visitor.py:288` |
| `ignore_definitions` | APPLIED | `find_unused_code_visitor.py:532` |
| `ignore_definitions_if_inherits_from` | APPLIED | `find_unused_code_visitor.py:533` |
| `ignore_definitions_if_decorated_with` | APPLIED | `find_unused_code_visitor.py:534` |
| `ignore_bodies_if_inherits_from` | APPLIED | `find_unused_code_visitor.py:543` |
| `ignore_bodies_of` | DECLARED-BUT-UNUSED | only `data_types.py:24` |
| `ignore_bodies_if_decorated_with` | DECLARED-BUT-UNUSED | only `data_types.py:25` |
| `ignore_if_decorated_with` | DECLARED-BUT-UNUSED | only `data_types.py:27` |
| `ignore_if_inherits_from` | DECLARED-BUT-UNUSED | only `data_types.py:28` |
| `ignore_names_if_decorated_with` | DECLARED-BUT-UNUSED | only `data_types.py:30` |
| `ignore_names_if_inherits_from` | DECLARED-BUT-UNUSED | only `data_types.py:31` |

- Note: `self.ignore_decorators` (`find_unused_code_visitor.py:50`) is checked in `visit_ClassDef` (433) and `visit_FunctionDef` (451) but **never populated from `Args`** — always empty, so inert.

## Q3: Base-class (inherits-from) tracking and matching

### Findings
- `get_inherits_from()` (`find_unused_code_visitor.py:415-429`) called from `visit()` (597-599); attaches `node.inherits_from` dynamically.
- Base names extracted at `find_unused_code_visitor.py:421`: `bases = [base.id for base in bases_attr if getattr(base, 'id', None)]` — **only `ast.Name` bases**. **Dotted bases like `models.Model` (`ast.Attribute`) are silently dropped** (no `.id`).
- Transitive (multi-level) resolution at lines 424-427: for each base, looks up `self.scopes.get(name=base, scope=...)` (`nested_scopes.py:37`) and extends with that item's `inherits_from`. **Works one hop, only for classes already defined+visited in the same file/scope.** Imported base classes are not resolved (imports are stored as import `CodeItem`s, not classes with `inherits_from`).
- Stored on `CodeItem` (`code_item.py:47` slot, `code_item.py:74` assignment) via `_define` reading `getattr(first_node, 'inherits_from', None)` (`find_unused_code_visitor.py:300`, passed at 317).
- Matched via `_match_many` (`ignore.py:54-55`, fnmatch per name) against `ignore_definitions_if_inherits_from` (533) and `ignore_bodies_if_inherits_from` (543).
- `ignore_if_inherits_from` and `ignore_names_if_inherits_from` are declared but never read.

## Q4: Decorator tracking and matching

### Findings
- `get_decorator_name()` (`deadcode/visitor/utils.py:53-61`) builds the decorator string. Handles: `ast.Call` (unwraps `.func`), `ast.Attribute` chains (walks `.attr`/`.value`), and plain `ast.Name` (`.id`). Returns `'@' + '.'.join(reversed(parts))`, so `@app.route(...)` → `"@app.route"`, `@simple` → `"@simple"`.
- Decorator list computed per node in `visit()` at `find_unused_code_visitor.py:601`: `[get_decorator_name(d) for d in getattr(node, 'decorator_list', [])] or None`.
- **Decorators are NOT stored on `CodeItem`** (no slot in `code_item.py:43-55`); used transiently within the `visit()` call.
- Matched in `_apply_ignore_definitions` at `find_unused_code_visitor.py:534` via `_match_many(decorators, self.args.ignore_definitions_if_decorated_with)`.
- `visit_FunctionDef` (440) also derives decorator names to classify `@property`/`@staticmethod`/`@classmethod` for type routing.
- Only `ignore_definitions_if_decorated_with` is wired. `ignore_bodies_if_decorated_with`, `ignore_if_decorated_with`, `ignore_names_if_decorated_with` declared but never read. `self.ignore_decorators` is inert (see Q2).

## Q5: Classification of unused vars/functions/methods and built-in suppression rules

### Findings
- **Definitions** collected by `_define()` (`find_unused_code_visitor.py:273-327`) into typed `LoggingList`s (`defined_vars`, `defined_funcs`, `defined_classes`, `defined_methods`, `defined_attrs`, `defined_props`, `defined_imports`, `unreachable_code`, `unused_file`).
- Variables: `visit_Name` (`find_unused_code_visitor.py:490-494`) — `ast.Store`/`ast.Param` → `_define_variable` (DC01); `ast.Load`/`ast.Del` → `add_used_name`.
- Function vs method vs property routing in `visit_FunctionDef` (`find_unused_code_visitor.py:439-458`): first arg `self` or `@staticmethod`/`@classmethod` → `defined_methods` (DC04); `@property` → `defined_props` (DC08); else `defined_funcs` (DC02). Classes → DC03, attributes (`self.x =`) → DC05, imports → DC07.
- **Usages** in `self.used_names` (`LoggingSet`, `find_unused_code_visitor.py:66`) via `add_used_name` (88-96).
- **"Never referenced"** = plain set-membership in `_get_unused_items` (`ignore.py:39-42`): `item.name not in used_names`. Aggregated by `get_unused_code_items` (`find_unused_code_visitor.py:154-171`).
- **Built-in suppression rules** (mostly in `deadcode/visitor/ignore.py`):
  - Variables `_ignore_variable` (`ignore.py:97-106`): names in `IGNORED_VARIABLE_NAMES = {'object','self'}` (`ignore.py:9`); single-underscore prefix `_x` (not `__`); dunders via `_is_special_name` (`ignore.py:45-46`).
  - Methods `_ignore_method` (`ignore.py:91-94`): all dunders; `test_*` / `PYTEST_METHOD_NAMES` (`setup_class`, `teardown_class`, `setup_method`, `teardown_method`, `ignore.py:17-21`) only in test files.
  - Functions `_ignore_function` (`ignore.py:87-88`): `test_*` / `PYTEST_FUNCTION_NAMES` (`setup_module`, etc., `ignore.py:10-15`) only in test files.
  - Classes `_ignore_class` (`ignore.py:74-75`): name contains `'Test'` only in test files.
  - Test-file detection `_is_test_file` (`ignore.py:58-63`): globs `*/test/*`, `*/tests/*`, `*/test*.py`, `*[-_]test.py` (case-insensitive).
  - Imports `_ignore_import` (`ignore.py:78-84`): any import in `__init__.py`, or star import (`*`).
  - `__all__` exports: `_mark_all_exports_used` (`find_unused_code_visitor.py:496-510`, `ignore.py:66-71`) marks every string element of `__all__ = [...]` as used.
  - `noqa` inline (`deadcode/visitor/noqa.py`): `parse_noqa` (54-63), code map incl. flake8 aliases `F401→DC07`, `F841→DC01` (16-46), `ignore_line` (66-68) called in `ignored()` closure (`find_unused_code_visitor.py:284-291`).

## Q6: pyproject.toml `[tool.deadcode]` expression, merge with CLI, and framework docs

### Findings
- Actual `[tool.deadcode]` at `pyproject.toml:179-206`: sets `ignore_names` (21 entries incl. glob `"visit_*"`), `ignore_names_in_files` (`["deadcode/utils/base_test_case.py"]`), and `exclude = ["tests"]`. Keys use underscores; both `-` and `_` forms accepted via normalization.
- `parse_pyproject_toml()` (`parse_arguments.py:210-225`): reads `pyproject.toml` from **cwd** (returns `{}` if absent), uses stdlib `tomllib` (import at `parse_arguments.py:6`), drills `tool.deadcode` (223), normalizes keys `k.replace('--','').replace('-','_')` (224).
- **Merge** (`parse_arguments.py:194-201`): argparse parses CLI → flatten each list field (except `paths`) via `flatten_lists_of_comma_separated_values` (`flatten_lists.py:6-12`, splits on commas) → for each toml key already in `parsed_args`, `.extend(item)`. So **list options are extend/union (CLI items first, toml appended); not replace.** Booleans (`--fix`, `--no-color`, etc.) are non-list so toml cannot set them. `paths` excluded. `Args(**parsed_args)` at `parse_arguments.py:207`.
- **Framework docs:**
  - `README.md:41-52` shows CLI vs pyproject side-by-side (`exclude`, `ignore-names=BaseTestCase,*Mixin`, `ignore-names-in-files=migrations`).
  - `README.md:54-60` FastAPI + Pydantic block: `ignore-definitions-if-decorated-with = ["@app.*","@router.*"]`, `ignore-definitions-if-inherits-from = ["BaseModel"]`, with note on conventional instance names and list-not-comma-split semantics. FastAPI and Pydantic are the only frameworks named in README toml.
  - `docs/unused-detection-and-ignoring.md:90-93` Django scenario (`--ignore-definitions-if-inherits-from models.Model`); `:94-97` FastAPI scenario (`--ignore-definitions-if-decorated-with=@app.*`) — expressed as CLI flags, not toml.
  - `docs/cli-and-configuration.md:65-89` shows toml in a bash comment; `:51-53` describes merge.
  - **No `docs/` or README content mentions SQLAlchemy, Alembic, or Flask** in any configuration context.

## Cross-Cutting Observations
- **Wiring gap is the dominant theme**: of 12 ignore-* `Args` fields, only 6 are consumed by the visitor (Q2 table). The unwired family covers all `*_if_*` variants of `ignore_bodies`, `ignore_names`, and the bare `ignore_if_*` pair. `self.ignore_decorators` is similarly declared-but-never-populated.
- **Decorator/inheritance matching is shallow**: dotted base classes are dropped (`find_unused_code_visitor.py:421`); transitive inheritance resolves one hop, same-file only (424-427); decorators are computed transiently and matched via fnmatch but never persisted on `CodeItem`.
- **Matching uses fnmatch glob** throughout (`_match`/`_match_many`, `ignore.py:48-55`), so patterns like `@app.*`, `*Mixin`, `visit_*` work in both CLI and toml.
- **Scenario tests are fully filesystem-mocked** and assert exact `path:line:col: DCxx ...` strings, making them the canonical way to validate new framework-suppression behavior.

## Open Areas
- The questions reference "SQLAlchemy and Alembic" (task title) but **no SQLAlchemy/Alembic-specific config, docs, or tests currently exist** in the repo — only FastAPI/Pydantic/Django examples. This is an absence, stated factually.
- Whether the unwired `*_if_decorated_with` / `*_if_inherits_from` body/name options were intended to behave like their `ignore_definitions_*` counterparts cannot be determined from code alone (no implementation exists to inspect).

# Research Findings

Repo: `deadcode` static unused-code analyzer. All references are `file:line`.

## Q1: Test case structure & execution

### Findings
- **Two input mechanisms.** (1) Real on-disk fixture modules under `tests/files/`; (2) inline `files` dict virtual-filesystem via `BaseTestCase`.
- **Fixture modules** (`tests/files/`): `variables.py` (3 unused globals + 1 used), `functions.py` (unused funcs + nested closure), `classes.py` (`UnusedClass`, `AnotherUnusedClass`, used `ThisClassIsUsed`), `subdir/one_more_file.py`, `subdir/another_subdir/__init__.py`. Consumed **only** by `DeadCodeIntegrationTests` (`tests/test_deadcode.py:13`), which `os.chdir(REPO_ROOT)` (`:16`) and calls `main(['tests/files/variables.py', '--no-color'])` against the real filesystem — no mocking. `subdir/` fixtures appear unused by active tests.
- **Inline `files` dict** (`deadcode/utils/base_test_case.py`): class attr `files: dict[str,str] = {}` (`:11`). `setUp` (`:37-57`) patches: `cli.find_python_filenames`→`_get_filenames` (returns `list(self.files.keys())`, `:21`); `open` in `find_unused_code_visitor`, `fix_unused_code_visitor`, `fix_or_show_unused_code` →`_read_file_side_effect` (`:43-50`); `os.remove`→MagicMock `self.os_remove` (`:52`); `parse_pyproject_toml`→`{}` (`:54-55`).
- `_read_file_side_effect` (`:23-35`) builds a MagicMock per `open()`, normalizes content with `fix_indent` (`deadcode/utils/fix_indent.py:25`, strips common indent), wires `.read()`, `.readlines()`, and captures writes into `self.updated_files`.
- **Assertions.** Detection tests compare `main(...)` return string directly: `assertEqual(unused_names, 'file:line:col: DCxx ... is never used')`, multiple findings joined by `\n` (`tests/test_deadcode.py:22-29`). File-state helpers: `assertFiles(files, removed=None)` (`base_test_case.py:59-85`) checks full post-run state (updated+unchanged+removed); `assertUpdatedFiles` (`:87-96`) checks only written files.
- **`tests/cli_args/`** — one file per option, all extend `BaseTestCase`. Present & populated: `test_ignore_names.py`, `test_ignore_definitions.py`, `test_ignore_definitions_if_inherits_from.py`, `test_ignore_bodies_if_inherits_from.py`, `test_fix.py`, `test_dry.py`, `test_exclude.py` (uses real `tempfile.TemporaryDirectory`, calls `find_python_filenames` directly), `test_parsing.py` (calls `parse_arguments()`, asserts `Args` fields). Empty/stub files: `test_no_color.py`, `test_quiet.py`, `test_count.py`, `test_verbose.py`, `test_ignore_names_in_files.py`.

## Q2: How the visitor decides a name is "used"

### Findings
- **Single AST pass** in `FindUnusedCodeVisitor` populates typed definition lists + one flat `used_names` set; matching is plain string membership.
- **Definition lists** init `find_unused_code_visitor.py:56-64`; `used_names` set `:66`. Lists: `defined_vars`, `defined_funcs`, `defined_classes`, `defined_methods`, `defined_attrs`, `defined_imports`, `defined_props`.
- **`CodeItem`** (`deadcode/visitor/code_item.py:38-139`) carries `name, type_, filename, scope, inherits_from, code_parts, name_line, name_column, number_of_uses`. `__eq__`/`__hash__` use only `self.name` (`:130-139`).
- **Dispatch** `visit()` (`:588-618`): no `generic_visit`; computes `get_inherits_from`, runs `_apply_ignore_definitions`, dispatches to `visit_<Node>`, pushes/pops scope, recurses children, resets `should_ignore_new_definitions`.
- **Type discrimination at definition time:**
  - `visit_FunctionDef` (`:446-465`): `@property`→`defined_props`; `@staticmethod`/`@classmethod`/first arg `self`→`defined_methods`; else `defined_funcs`. `visit_AsyncFunctionDef` (`:348-349`) delegates.
  - `visit_ClassDef` (`:438-444`)→`defined_classes`.
  - `visit_Name` (`:497-501`): `Load`/`Del` (and id not in `IGNORED_VARIABLE_NAMES`)→`add_used_name`; `Store`/`Param`→`_define_variable`.
  - `visit_Attribute` (`:351-355`): `Store`→`defined_attrs`; `Load`→`add_used_name(node.attr)` (object not tracked, only attr name).
  - imports via `_add_aliases` (`:211-236`)→`defined_imports`; aliased import marks original name used (`:236`).
- **Usage tracking:** `add_used_name` (`:88-96`) adds string to `used_names` + `scopes.mark_as_used` (increments `number_of_uses`). Also called from `visit_Call` for `getattr`/`hasattr` string args (`:379`) and format strings (`:409`); `visit_BinOp` `%(name)s` (`:369`); `visit_MatchClass` (`:525`); `__all__` exports (`_mark_all_exports_used` `:503-508`).
- **Central registration** `_define` (`:273-334`): evaluates `ignored()` closure (`:291-298`); builds `CodeItem`; registers in `NestedScope`; if ignored→`add_used_name(name)` (suppresses, `:332`), else appends to collection (`:334`).
- **Matching** `_get_unused_items` (`deadcode/visitor/ignore.py:39-42`): `[item for item in defined_items if item.name not in used_names]`. **Flat string test, not scope-aware** — a name used anywhere counts as used everywhere. `unused_*` properties (`:175-198`) feed `get_unused_code_items()` (`:154-171`), sorted by `(filename, name_line)`.
- `scope_parts` (`:105`, push `:554-562`, pop `:618`) builds `CodeItem.scope` but plays **no role** in used/unused matching.

## Q3: Decorator parsing & handling

### Findings
- **`get_decorator_name`** (`deadcode/visitor/utils.py:53-61`): if `ast.Call`, unwrap to `.func` (discards call args); walk `ast.Attribute` chain collecting `.attr`; append final `ast.Name.id`; return `'@' + '.'.join(reversed(parts))`. Results: `@deco`→`'@deco'`; `@a.b.c`→`'@a.b.c'`; `@deco(1)`→`'@deco'`; `@app.get("/path")`→`'@app.get'` (confirmed `tests/visitor/test_utils.py:36-43`).
- **`visit_ClassDef`** (`find_unused_code_visitor.py:438-444`): iterates `node.decorator_list`; if `_match(get_decorator_name(d), self.ignore_decorators)` → `break` (skip, never defined); else `for/else`→`_define(defined_classes,...)`.
- **`visit_FunctionDef`** (`:446-465`): builds `decorator_names` list (`:447`); uses it to (1) classify type (`:449-456`) and (2) gate via `any(_match(name, self.ignore_decorators) ...)` (`:458`). Decorator names are **not** stored on `CodeItem` (no field in `code_item.py:43-55`); used only for the in-pass ignore gate.
- **`self.ignore_decorators`** init `[]` (`:50`) and **never populated from `self.args`** in production; only set directly in tests (`tests/visitor/test_find_unused_code_visitor.py:92,98`).
- `lines.py:19` lists `decorator_list` in `ignored_fields`, so decorators are skipped when computing definition line spans.

## Q4: CLI / pyproject options for suppressing false positives

### Findings
- **Declared** in `deadcode/actions/parse_arguments.py` (all `nargs='*', action='append', default=[]`): `--exclude` (`:41-48`), `--ignore-names` (`:49-59`), `--ignore-bodies-of` (`:60-67`), `--ignore-bodies-if-decorated-with` (`:68-75`), `--ignore-bodies-if-inherits-from` (`:76-83`), `--ignore-definitions` (`:84-93`), `--ignore-definitions-if-inherits-from` (`:94-104`), `--ignore-definitions-if-decorated-with` (`:105-115`), `--ignore-if-decorated-with` (`:117-124`), `--ignore-if-inherits-from` (`:125-132`), `--ignore-names-if-inherits-from` (`:134-141`), `--ignore-names-if-decorated-with` (`:142-149`), `--ignore-names-in-files` (`:151-158`).
- **No `--ignore-decorators` CLI flag exists.** The internal `self.ignore_decorators` (Q3) is the only related identifier and is never wired to args.
- **Flatten + merge:** post-parse, list args flattened by `flatten_lists_of_comma_separated_values` (`:190-192`, `deadcode/utils/flatten_lists.py:6-12` — flattens sublists then splits on commas). `parse_pyproject_toml` (`:210-225`) reads `[tool.deadcode]`, normalizes keys (strip `--`, `-`→`_`, `:224`), extends onto CLI lists (`:195-197`; TOML values **not** comma-split). Returns `Args(**parsed_args)` (`:207`).
- **`Args` dataclass** (`deadcode/data_types.py:14-36`): all suppression fields typed `Iterable[Pathname]` (`Pathname=str`, `:11`), defaults `()`.
- **Matching primitives** (`deadcode/visitor/ignore.py:49-55`): `_match` uses `fnmatchcase` (case=True) / `fnmatch`; `_match_many` short-circuits over a name collection. Glob wildcards supported.
- **Only 4 options are actually consumed in the visitor** (`self.args.` grep):
  - `ignore_names` — `ignored()` closure `_match(name, args.ignore_names)` (`:294`).
  - `ignore_names_in_files` — `_match(self.filename, args.ignore_names_in_files)` (`:295`).
  - `ignore_definitions` — `_apply_ignore_definitions` `_match(node_name, ...)` (`:533`), sets `should_ignore_new_definitions`.
  - `ignore_definitions_if_inherits_from` — `_match_many(inherits_from, ...)` (`:534`); `inherits_from` from `get_inherits_from` (`:422-436`).
  - `ignore_bodies_if_inherits_from` — `_apply_ignore_bodies` (`:543`) suppresses nested defs only.
- **Declared-but-inert** (parsed into `Args`, never read by visitor): `ignore_bodies_of`, `ignore_bodies_if_decorated_with`, `ignore_definitions_if_decorated_with`, `ignore_if_decorated_with`, `ignore_if_inherits_from`, `ignore_names_if_decorated_with`, `ignore_names_if_inherits_from`. TODO note at `find_unused_code_visitor.py:284-289`.

## Q5: Implicit exemptions / exempt definitions

### Findings (all in `deadcode/visitor/ignore.py` unless noted)
- **Hardcoded name sets:** `IGNORED_VARIABLE_NAMES = {'object','self'}` (`:9`); `PYTEST_FUNCTION_NAMES` (`:10-15`); `PYTEST_METHOD_NAMES` (`:17-21`). `cls` is **not** exempt by name.
- **Dunders:** `_is_special_name(name)` = startswith+endswith `__` (`:45-46`), applied only in `_ignore_method` (`:92`) — dunder **methods** (`__init__`, `__str__`, …) always exempt. Dunder funcs/vars not via this path.
- **`@property`:** classified to `defined_props` and bypasses `_ignore_method`/`_ignore_function` (`find_unused_code_visitor.py:451,461`).
- **Variables** `_ignore_variable` (`:97-106`): exempt if in `IGNORED_VARIABLE_NAMES`, single-underscore `_x` (not `__x`), or dunder.
- **Imports** `_ignore_import` (`:78-84`): all imports in `__init__.py`, and `*` star imports, exempt. `__future__` skipped entirely (`find_unused_code_visitor.py:481-483`).
- **Classes** `_ignore_class` (`:74-75`): name contains `'Test'` in a test file. Functions `_ignore_function` (`:87-88`): `test_*` or `PYTEST_FUNCTION_NAMES` in test files. Methods also `test_*`/pytest in test files (`:92-94`).
- **Test-file detection** `_is_test_file` (`:58-63`): globs `*/test/*`, `*/tests/*`, `*/test*.py`, `*[-_]test.py`, case-insensitive.
- **`__all__`:** `_assigns_special_variable__all__` (`:66-71`) → `_mark_all_exports_used` marks every listed string used (`find_unused_code_visitor.py:503-508`).
- **`# noqa`:** `ignored()` calls `noqa.ignore_line` (`find_unused_code_visitor.py:297`); `parse_noqa` (`noqa.py:54-63`) maps flake8 `F401`→DC07, `F841`→DC01.
- Ignored definitions are also added to `used_names` (`_define` `:332`), so suppression propagates everywhere.

## Q6: Error-code categories & message formatting

### Findings
- **Code map** `ERROR_TYPE_TO_ERROR_CODE` (`deadcode/constants.py:36-49`): DC01 variable, DC02 function, DC03 class, DC04 method, DC05 attribute, DC06 name, DC07 import, DC08 property, DC09 unreachable_code, **DC11** unused_file, DC12 commented_out_code, DC13 ignore_expression. **No DC10.** `UnusedCodeErrorCode` Literal (`constants.py:20-33`).
- Second equivalent map `ERROR_CODES` (`ignore.py:23-36`, uses `'empty_file'` for DC11) — used only for noqa lookups.
- **Stored on item:** `CodeItem.error_code = ERROR_TYPE_TO_ERROR_CODE[type_]` (`code_item.py:82`).
- **Location:** `filename_with_position` (`code_item.py:92-99`) → `file:line:col:`. `name_line`/`name_column` set from `last_node.lineno/col_offset` (`find_unused_code_visitor.py:321-322`); first line via `lines.get_first_line_number` (decorator line if present, `lines.py:79-82`).
- **Message** `get_unused_names_error_message` (`deadcode/actions/get_unused_names_error_message.py:7-35`): empty→`None`; `quiet`→`''`; `count`→count string; else per item `'{filename_with_position} \033[91m{error_code}\033[0m '` + `item.message` or default `'{Type} \`{name}\` is never used'` (type underscores→spaces, capitalized; name bold `\033[1m`). `no_color` strips ANSI (`:25-26`). `fix` appends `'Removed N unused code item(s)!'` (`:29-33`). Joined by `\n` (`:35`).

## Q7: Documentation on framework recognition / entrypoint config

### Findings
- **`notes:690-692`** wishlist: "Framework recognition: Django models, urls; FastAPI routes - these could be provided as an configuration example." → FastAPI handling expected via **example configuration (ignore options)**, not built-in recognition.
- **`notes:696-700`**: lists "fastapi route decorator functions" as a known hard false-positive case; "I don't think this project would solve any of those cases."
- **`BACKLOG.md:2-4`**: `[~] [T16]` FastAPI test cases (in progress); SQLAlchemy/Alembic and Django pending. Task statements only, no mechanism.
- **`docs/unused-detection-and-ignoring.md:51-62`**: explicitly documents `*_if_decorated_with` and some `*_if_inherits_from` options as parsed into `Args` and in README, but **never referenced** in visitor/ignore — "silently ineffective"; `self.ignore_decorators` "always remains `[]`". `:91-93` (Scenario 4) shows `--ignore-definitions-if-inherits-from models.Model` working for Django models (inheritance gate IS wired).
- **`docs/cli-and-configuration.md:30-39`** and **`README.md:63-70`**: generic decorator/inheritance option docs, no framework names. `README.md:50-51` shows `[tool.deadcode]` example (`ignore-names-in-files=["migrations"]`).
- **`enhancement_proposals/` and `errors/`**: no matches for framework/fastapi/decorator/route.
- Net intended mechanism: inheritance-based frameworks (Django models) → `--ignore-*-if-inherits-from` (working); decorator-based (FastAPI routes) → `--ignore-*-if-decorated-with` (declared but inert/unimplemented).

## Cross-Cutting Observations
- **Flat-string matching** (Q2) is the core heuristic: any defined name whose string appears in `used_names` anywhere is "used" — explains why decorator-applied framework entrypoints (e.g. FastAPI route handlers never referenced by name) would be flagged.
- **Gap between declared and implemented options** (Q4/Q7): the decorator-based ignore options that would naturally suppress FastAPI route false positives are parsed but inert; only `ignore_names`, `ignore_names_in_files`, `ignore_definitions`, `ignore_definitions_if_inherits_from`, `ignore_bodies_if_inherits_from` actually affect output.
- **Decorator names are computed but discarded** (Q3): `get_decorator_name` works (`@app.get`), but the only consumer is the always-empty `ignore_decorators`.
- **Two test idioms** (Q1): integration tests need real files; the inline `files` dict + `assertEqual` on `main()`'s return string is the dominant pattern for new option/scenario tests.

## Open Areas
- Whether any test currently exercises decorator-based ignore options end-to-end: none found wired through CLI args (only direct `visitor.ignore_decorators` assignment in unit tests).
- `tests/files/subdir/` fixtures have no observed active consumer (Q1).
- Exact behavior of `name` (DC06) and `ignore_expression` (DC13) categories not deeply traced (outside question scope).

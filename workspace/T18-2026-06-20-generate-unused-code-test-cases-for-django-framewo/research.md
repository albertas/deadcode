# Research Findings

## Q1: How are the existing framework scenario tests in `tests/frameworks/` structured?

### Findings
- All three files subclass `BaseTestCase`; tests define synthetic source as an
  in-memory `self.files: dict[str, str]`, call `deadcode.cli.main([...])`, and
  `self.assertEqual(output, expected_string)` on the exact returned string.
- **`test_fastapi.py`** (`tests/frameworks/test_fastapi.py`):
  - `TestFastapiRoutes` (`:5`). `test_route_handlers_suppressed_unused_helper_still_reported`
    (`:6`): one file `main.py` (`:7-42`); options `--no-color`,
    `--ignore-definitions-if-decorated-with=@app.*`, `…=@router.*` (`:44-51`);
    asserts single line `main.py:31:0: DC02 Function \`_unused_helper\` is never used` (`:53`).
  - `test_pydantic_models_suppressed_via_inherits_from` (`:55`): file `models.py`
    (`:56-69`); option `--ignore-definitions-if-inherits-from=BaseModel` (`:71`);
    asserts two lines — `DC03 Class \`UnusedPlainClass\`` and `DC01 Variable
    \`unused_attribute\`` joined with `\n` (`:73-77`).
- **`test_sqlalchemy.py`** (`tests/frameworks/test_sqlalchemy.py`): `TestSqlalchemyDeclarative` (`:5`).
  - `test_2_0_models_…` (`:6`): SQLAlchemy 2.0 `Base(DeclarativeBase)`/`User(Base)`;
    `--ignore-definitions-if-inherits-from=Base` + `--ignore-bodies-if-inherits-from=Base`
    (`:29-36`); asserts `models.py:16:0: DC02 Function \`_unused_helper\`` (`:38`).
  - `test_1_x_models_…` (`:40`): `Base = declarative_base()` 1.x style; same option
    pair (`:60-67`); asserts `DC01 Variable \`UNUSED_CONSTANT\`` (`:70`).
  - `test_event_listeners_suppressed_via_decorator` (`:72`):
    `--ignore-definitions-if-decorated-with=@event.*` (`:90-95`); asserts
    `DC02 Function \`_unused_listener_helper\`` (`:98`).
  - `test_flask_sqlalchemy_db_model_suppressed` (`:100`): `User(db.Model)`;
    `--ignore-definitions-if-inherits-from=db.Model` + `--ignore-bodies-if-inherits-from=db.Model`
    (`:119-126`); asserts `DC01 Variable \`UNUSED_FLAG\`` (`:129`).
- **`test_alembic.py`** (`tests/frameworks/test_alembic.py`): `TestAlembicMigrations` (`:5`).
  - `…suppressed_via_ignore_names` (`:6`): one migration file; six separate
    `--ignore-names=` flags (`upgrade`, `downgrade`, `revision`, `down_revision`,
    `branch_labels`, `depends_on`) (`:32-43`); asserts `DC02 Function
    \`_unused_migration_helper\`` (`:45-48`).
  - `…suppressed_via_ignore_names_in_files` (`:50`): two files (a migration +
    `service.py`); `--ignore-names-in-files=*versions*` glob (`:74-80`); asserts only
    `service.py:1:0: DC02 Function \`_genuinely_unused\`` (`:83`).
- Canonical structure: assign `self.files` → call `main([...])` (always with
  `--no-color`) → `assertEqual`. No teardown; cleanup via `addCleanup` in `BaseTestCase`.

## Q2: What does `BaseTestCase` provide and how do `fix_indent`, file mocking, and `main()` work together?

### Findings
- `BaseTestCase(TestCase)` at `deadcode/utils/base_test_case.py:10`; `files: dict[str, str] = {}`
  (`:11`); `maxDiff = None` (`:13`). `patch()` helper registers `addCleanup(patcher.stop)` (`:15-18`).
- `setUp` (`:37-57`) installs six patches: `deadcode.cli.find_python_filenames` →
  `_get_filenames` returning `list(self.files.keys())` (`:20-21`, `:40-41`); builtin
  `open` in `find_unused_code_visitor`, `fix_unused_code_visitor`, and
  `fix_or_show_unused_code` → `_read_file_side_effect` (`:43-50`);
  `fix_or_show_unused_code.os.remove` → mock (`:52`); `parse_arguments.parse_pyproject_toml`
  → `{}` (`:54-55`), preventing the project's own `pyproject.toml` from affecting tests.
- `_read_file_side_effect` (`:23-35`): builds a `MagicMock`, sets `.filename`, runs
  `fix_indent(self.files[filename])`, and wires `mock.__enter__().read`/`readlines`/`write`
  so the visitor's `with open(...) as f: f.read()` returns the synthetic source.
  Writes are captured into `self.updated_files` via `cache_file_content` (`:27-29`).
- `fix_indent(doc)` at `deadcode/utils/fix_indent.py:25-50`: `expandtabs().splitlines(True)`
  (`:31`); finds the minimum left margin of non-blank lines via `_find_common_margin`
  (`:4-12`); `lstrip()`s line 0 (`:39`); strips `margin` chars from lines `[1:]` via
  `_strip_margin` (`:15-22`); pops leading blank lines (`:48-49`); returns `''.join(lines)`.
  Returns `None` only on `UnicodeError` (`:33`). Net effect: naturally-indented
  triple-quoted fixtures become left-aligned source.
- `main()` at `deadcode/cli.py:10-29`: `parse_arguments` (toml mocked) → `find_python_filenames`
  (mocked → file keys) → `find_unused_names` (opens files → mocked) → optional
  `fix_or_show_unused_code` → `get_unused_names_error_message`; returns a `\n`-joined
  message string or `None`. The real filesystem walker `find_python_filenames.py:10`
  and the visitor `open` call sites (`find_unused_code_visitor.py:102`,
  `fix_unused_code_visitor.py:80`) are all bypassed.
- Assertion helpers: `assertFiles` (`:59-85`) and `assertUpdatedFiles` (`:87-96`) compare
  expected vs actual after running both through `fix_indent`; `os.remove` calls inspected
  via `self.os_remove.mock_calls` (`:64`).

## Q3: What suppression/ignore CLI options does the argument layer expose, and how do they differ?

### Findings
- Parsing in `deadcode/actions/parse_arguments.py`; result is the `Args` dataclass
  (`deadcode/data_types.py:15-35`), fields typed `Iterable[Pathname]`, default `()`.
- All list options registered with `nargs='*', action='append', type=str, default=[]`.
  After `parse_args` (`:188`), every list field is flattened by
  `flatten_lists_of_comma_separated_values` (`deadcode/utils/flatten_lists.py:6-12`):
  flattens sublists then splits on `','`, so both space- and comma-separated values
  become one flat `list[str]`. `pyproject.toml` values (`:210-225`) `extend` the CLI lists (`:197`).
- Matching uses `fnmatchcase` (case-sensitive glob) via `_match` (`ignore.py:49-51`) and
  `_match_many` (`ignore.py:54-55`) — patterns are globs (`*`, `?`, `[seq]`), not regex.
- **Active options** (effect scope):
  | Flag | Registered | `Args` field | Suppresses | Visitor site |
  |---|---|---|---|---|
  | `--ignore-names` | `:50-59` | `ignore_names` | name only | `find_unused_code_visitor.py:287` |
  | `--ignore-names-in-files` | `:151-158` | `ignore_names_in_files` | all names in matching file paths | `:288` |
  | `--ignore-definitions` | `:84-93` | `ignore_definitions` | name + body (by name match) | `:543` |
  | `--ignore-definitions-if-decorated-with` | `:105-115` | `ignore_definitions_if_decorated_with` | name + body (by decorator) | `:545` |
  | `--ignore-definitions-if-inherits-from` | `:94-104` | `ignore_definitions_if_inherits_from` | name + body of class (by base) | `:544` |
  | `--ignore-bodies-if-inherits-from` | `:76-83` | `ignore_bodies_if_inherits_from` | body only; class name still tracked | `:552-558` |
- Key distinction: `--ignore-definitions-if-inherits-from` fires in `visit()` *before*
  `_define()` for the class, so the class name itself is also suppressed;
  `--ignore-bodies-if-inherits-from` fires *after* `_dispatch_pre_visit`/scope-push (`:621`),
  so only the body's child definitions are suppressed — the class name can still be reported.
- **Inert options** — declared in `Args` and parsed but never read anywhere in the
  visitor (documented at `docs/unused-detection-and-ignoring.md:49-61`):
  `ignore_bodies_of` (`:60-67`), `ignore_bodies_if_decorated_with` (`:68-75`),
  `ignore_if_decorated_with` (`:117-124`), `ignore_if_inherits_from` (`:125-132`),
  `ignore_names_if_inherits_from` (`:134-141`), `ignore_names_if_decorated_with` (`:142-149`).
  Note: `self.ignore_decorators` (`find_unused_code_visitor.py:50`), checked by
  `visit_ClassDef`/`visit_FunctionDef`, is always `[]` and never assigned from args.

## Q4: How does the visitor detect used class/base/decorator/assignment names, and how do inheritance/decorator ignore rules match?

### Findings
- `FindUnusedCodeVisitor` (`ast.NodeVisitor`) keeps per-type `defined_*` `LoggingList`s
  and one flat `used_names` `LoggingSet` (`find_unused_code_visitor.py:56-66`). Final
  unused list: `[item for item in defined_items if item.name not in used_names]`
  (`ignore.py:39-42`); `CodeItem.__eq__` compares against a plain string (`code_item.py:130-136`).
- `_define()` (`:273-327`) is the single definition path: builds a `CodeItem`, registers
  it in scopes, then — via the inner `ignored()` closure (`:284-291`) — either calls
  `add_used_name(name)` (whitelisting it) or appends to the collection (`:325-327`).
  `add_used_name` (`:88-96`) adds the bare name string to `used_names`.
- Node handlers: `visit_ClassDef` → `defined_classes` (`:442-448`); `visit_FunctionDef`
  → `defined_funcs`/`defined_methods`/`defined_props` based on decorators and `self`
  first-arg (`:450-469`); `visit_Attribute` Store→`defined_attrs`, Load→`add_used_name(node.attr)`
  (`:344-348`); `visit_Name` Load/Del→`add_used_name`, Store/Param→`_define_variable`→`defined_vars`
  (`:501-505`); imports→`_add_aliases`→`defined_imports` (`:211-236`).
- `__all__` assignments mark their string entries as used (`:507-512`, `ignore.py:66-71`).
- The `should_ignore_new_definitions` flag (`:289`) routes all `_define` calls in a
  subtree to `add_used_name` when set by `_apply_ignore_definitions` (`:531-550`) or
  `_apply_ignore_bodies` (`:552-558`); reset after the node (`:628-631`).
- **Inheritance matching**: `get_inherits_from` (`:415-440`) resolves each base via
  `utils.get_base_name` (`utils.py:64-77`): `ast.Name`→`base.id`; dotted `ast.Attribute`→
  joined `db.Model`. For dotted names BOTH the full `db.Model` and the leaf `Model` are
  added to the list (`:428-432`); transitive bases are pulled from already-seen scopes
  (`:435-438`). Stamped onto `node.inherits_from` (`:610`) and `CodeItem.inherits_from` (`:317`).
  `_apply_ignore_definitions` matches via `_match_many(inherits_from, …)` (`:544`), so
  `*Model` matches both forms.
- **Decorator matching**: `utils.get_decorator_name` (`utils.py:53-61`) unwraps `ast.Call`,
  walks the attribute chain, prepends `@` → `@app.route`, `@event.listens_for`.
  `_apply_ignore_definitions` matches `_match_many(decorators, args.ignore_definitions_if_decorated_with)`
  (`:545`); patterns like `@app.*` match.
- Code-item type → error code (`constants.py:36-49`): class=DC03, function=DC02,
  method=DC04, property=DC08, import=DC07, variable=DC01, attribute=DC05.

## Q5: How are string-literal, dotted-attribute, and dynamic references handled, and what are the limitations?

### Findings
- **Attribute access**: `visit_Attribute` (`find_unused_code_visitor.py:344-348`). Load
  context adds only the bare trailing identifier `node.attr` (not the dotted path or
  receiver) to `used_names`; Store context defines it. Because comparison is a global
  name-string check (`ignore.py:40`), any `obj.foo` anywhere marks every defined `foo`
  used — no scope/receiver-type constraint.
- **String literals**: there is NO `visit_Constant`/`visit_Str`. Only four specific
  string-use patterns are handled:
  1. `__all__` list/tuple entries → `add_used_name` (`:507-512`, `ignore.py:66-71`).
  2. `getattr(obj,"name")` / `hasattr(obj,"name")` second-arg string literal (`:364-372`);
     only when `func` is a bare `ast.Name` and the arg is a literal (`setattr` not handled).
  3. Old-style `"%(name)s" % locals()` via regex (`:350-362`).
  4. New-style `"{name}".format(**locals())` via `_handle_new_format_string` (`:374-402`).
- **Type comments** are re-parsed and visited (`:575-579`), so names in `# type:` comments
  count as uses.
- **Not handled / false-positive sources**: arbitrary string literals (e.g. `x = "MyClass"`),
  PEP 563 string annotations (`from __future__ import annotations`), `setattr` string args,
  and `getattr` accessed as an attribute. Documented as a global name-string comparison
  with "no scope awareness at decision time" (`docs/unused-detection-and-ignoring.md:9-13`).
  `--ignore-names="…,*Mixin"` is the designed escape hatch (`docs/invocation.md:156`).
  `tests/test_accurate_usage_detection.py:7` is `@skip`ped — receiver-type-aware method
  resolution is a known unresolved limitation (TODO at `:9-49`).

## Q6: How are findings reported (codes, format, line/col), and what doc conventions govern new test modules?

### Findings
- **Error codes** in `ERROR_TYPE_TO_ERROR_CODE` (`constants.py:36-49`): DC01 variable,
  DC02 function, DC03 class, DC04 method, DC05 attribute, DC06 name, DC07 import,
  DC08 property, DC09 unreachable_code, DC11 unused_file, DC12 commented_out_code,
  DC13 ignore_expression. **DC10 does not exist** (sequence skips it). Assigned at
  `code_item.py:82` via `error_code = ERROR_TYPE_TO_ERROR_CODE[type_]`.
- **Message format** (`get_unused_names_error_message.py:21-24`):
  `<filepath>:<line>:<column>: <DCxx> <Type> \`<name>\` is never used`, e.g.
  `foo.py:1:0: DC01 Variable \`unused_variable\` is never used`. `filename_with_position`
  built at `code_item.py:93-99`. `type_` is `.replace("_"," ").capitalize()`. A custom
  `CodeItem.message` overrides the default text (`:22`). `--fix` appends
  `Removed <N> unused code item[s]!` (`:30`); `--quiet`→`''` (`:14`); `--count`→count (`:17`);
  ANSI stripped when `--no-color` (`:26`, `:31-32`).
- **Line/column convention**: line 1-based, column 0-based — sourced straight from
  `ast` `lineno`/`col_offset` (`find_unused_code_visitor.py:314-315`); stated explicitly
  at `docs/testing-and-tooling.md:79`.
- **Doc conventions for new test modules** (`docs/testing-and-tooling.md`): file naming
  `test_<snake_case_subject>.py` (`:41`); class naming `Test<DescriptiveName>` (dominant)
  or `<DescriptiveName>Tests` (`:42`); methods `test_<behavior_snake_case>` (`:43`);
  `unittest`-style classes only, no plain pytest functions, no `conftest.py` (`:44`);
  empty `__init__.py` present in `tests/cli_args/`, `tests/utils/`, `tests/frameworks/`
  (`:45`); `BaseTestCase` subclasses set `files` as indented triple-quoted strings
  normalized by `fix_indent` (`:49`, `:67`); group by subdirectory mirroring package
  structure (`:9-18`); pair positive findings with `None`-asserting negative tests (`:80`);
  version-gate 3.12+ syntax with `@skipUnless(sys.version_info >= (3, 12), …)` (`:83-98`).

## Cross-Cutting Observations
- **Whitelist-at-definition model**: every ignore mechanism funnels through `_define`'s
  `ignored()` closure (`find_unused_code_visitor.py:284-291`), converting a suppressed
  definition into a `used_names` entry rather than filtering at report time.
- **Glob, case-sensitive matching everywhere**: `fnmatchcase` is the single matching
  primitive (`ignore.py:49-55`) for names, file paths, decorators, and base classes.
- **Dotted names produce dual entries** (full + leaf) for both bases (`get_inherits_from`)
  and decorators, so patterns can match either form.
- The framework tests in Q1 already exercise exactly the four active ignore options from
  Q3 (`--ignore-names`, `--ignore-names-in-files`, `--ignore-definitions-if-decorated-with`,
  `--ignore-definitions-if-inherits-from` + `--ignore-bodies-if-inherits-from`).

## Open Areas
- The six inert ignore options (Q3) are parsed but have no runtime effect; any test
  relying on them as functional would not behave as their `--help` text implies.
- Receiver-type-aware usage detection (Q5) is explicitly unimplemented/skipped, so
  method/attribute uses are matched by bare name only across the whole codebase.

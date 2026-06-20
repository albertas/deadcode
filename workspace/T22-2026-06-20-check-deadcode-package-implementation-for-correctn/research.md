# Research Findings

Scope: `deadcode/visitor/`, `deadcode/actions/`, `deadcode/utils/`, `tests/`.
All references are `file:line`. Describes what exists; no recommendations.

## Q1: Definition vs. use routing in `FindUnusedCodeVisitor`

### Findings
- **Two sinks.** Definitions go to `_define()` (`find_unused_code_visitor.py:273-327`),
  which appends a `CodeItem` to a typed `LoggingList` collection. Uses go to
  `add_used_name()` (`:88-96`), which adds to `self.used_names` and calls
  `self.scopes.mark_as_used()`. Final unused set = defined names not in
  `used_names` via `_get_unused_items` (`ignore.py:39-42`).
- **Custom traversal.** `visit()` is overridden (`:599-631`); it does NOT call
  `ast.NodeVisitor.generic_visit`. It runs `_dispatch_pre_visit` (calls
  `visit_<Class>`, `:560-563`), pushes scope (`_maybe_push_scope`, `:565-573`),
  then `_visit_children` (`:581-592`) recurses all child AST nodes, then
  `_dispatch_post_visit` (`visit_<Class>_after_visiting_child_nodes`, `:594-597`).
- **`visit_Name` (`:501-505`)** is the central router by `ctx`:
  - `ast.Load` / `ast.Del` → `add_used_name(node.id)` (unless name in
    `IGNORED_VARIABLE_NAMES = {'object','self'}`, `ignore.py:9`).
  - `ast.Param` / `ast.Store` → `_define_variable(node.id, node)` (`:329-335`),
    which delegates to `_define(..., ignore=_ignore_variable)`.
  - `ast.Param` is a Python-2-era context; modern function args are `ast.arg`
    nodes and `visit_arg` is **commented out** (`:337-339`), so parameters are
    not registered as definitions.
- **`visit_Attribute` (`:344-348`)**: `ast.Store` → `_define(self.defined_attrs,...)`;
  `ast.Load` → `add_used_name(node.attr)`. Attribute names are matched only by
  bare attr string (no receiver tracking).
- **Definition `visit_*` methods**: `visit_ClassDef` (`:442-448`, →`defined_classes`),
  `visit_FunctionDef`/`visit_AsyncFunctionDef` (`:341-342,450-469`, splits into
  property/method/function by decorators + first-arg `self`), `_add_aliases`
  (`:211-236`, imports → `defined_imports`). `_define_variable` for vars/attrs.
- **`NestedScope`** (`utils/nested_scopes.py`): `scope` is a dotted string built
  from `scope_parts` (`:84-86`), pushed/popped per class/function (`:565-573`,
  `:630-631`). `_define` calls `self.scopes.add(code_item)` (`:320`) recording
  the item under its scope path. `add_used_name` calls `mark_as_used` which
  increments `number_of_uses` on the resolved `CodeItem` (`nested_scopes.py:64-83`).
  Note: actual unused detection uses the flat `used_names` set, not scope-aware
  resolution — `NestedScope` primarily supports `get_inherits_from` base lookup
  (`:436-438`) and usage counts.

## Q2: Modern Python syntax handling

### Findings
- **Only one dedicated modern `visit_*`: `visit_MatchClass` (`:526-529`)** — marks
  `node.kwd_attrs` as used. Everything else relies on generic child traversal in
  `_visit_children` (`:581-592`) to reach inner `ast.Name` nodes.
- **PEP 695 `type X = ...` (`ast.TypeAlias`)**: no `visit_TypeAlias`. The alias
  name is an `ast.Name` target with `ast.Store` ctx → defined as a variable via
  `visit_Name`; the value's names reached as `Load` children. (confirmed: grep
  finds no `visit_TypeAlias`.)
- **PEP 695 generics `def f[T]` / `class C[T]`**: no `visit_TypeVar`/`visit_arg`.
  Type params traversed as children; references reached as `Name` Load nodes.
- **`match`/`case`**: no `visit_Match`/`visit_MatchAs`/`visit_MatchStar`/etc.;
  only `visit_MatchClass` for keyword attrs. Capture patterns and subjects reached
  via generic traversal.
- **Walrus `:=` (`ast.NamedExpr`)**: no dedicated method; target is `ast.Name`
  Store → defined as variable; reads are Load Names.
- **f-strings (`ast.JoinedStr`/`ast.FormattedValue`)**: no dedicated method;
  interpolated `Name` nodes are normal Load children → marked used.
- **`async def`**: `visit_AsyncFunctionDef` (`:341-342`) just delegates to
  `visit_FunctionDef`. Scope push handles both (`:569`).
- **`# type:` comments**: `_visit_type_comment` (`:575-579`) re-parses the comment
  string via `ast.parse(..., mode='func_type'|'eval')` and visits the resulting
  tree, so names in type comments count as uses. Requires AST built with
  `type_comments=True` (see `actions/parse_abstract_syntax_tree.py`).
- Version gating of these features is in tests, not source (see Q5).

## Q3: Ignore / suppression mechanisms

### Findings
Suppression occurs at several distinct pipeline points:

1. **Per-`_define` `ignored()` check (`:284-291`, applied at `:322`).** A definition
   is ignored (and instead added to `used_names`, `:325`) if ANY of:
   - `ignore(self.filename, name)` — the per-collection predicate from
     `visitor/ignore.py` (`_ignore_class/_import/_function/_method/_variable`,
     `ignore.py:74-106`).
   - `_match(name, self.args.ignore_names)` — `--ignore-names` glob (`ignore.py:49-51`).
   - `_match(self.filename, self.args.ignore_names_in_files)` — `--ignore-names-in-files`.
   - `self.should_ignore_new_definitions` — set by the definition/body ignore flags.
   - `noqa.ignore_line(...)` — `# noqa` per-line suppression.
2. **`_ignore_*` predicates (`ignore.py:74-106`).** Built-in heuristics:
   star imports + `__init__.py` imports (`_ignore_import:78-84`); `Test*` classes
   in test files (`_ignore_class:74-75`); `test_*`/pytest hooks in test files
   (`_ignore_function:87-88`, `_ignore_method:91-94`); dunder methods
   (`_is_special_name`); `_`/`_x` private vars + `self`/`object` (`_ignore_variable:97-106`).
   Test-file detection: `_is_test_file` glob (`ignore.py:58-63`).
3. **`should_ignore_new_definitions` flag** set in `_apply_ignore_definitions`
   (`:531-550`) and `_apply_ignore_bodies` (`:552-558`), turned off in teardown of
   `visit()` (`:628-629`). Driven by `--ignore-definitions` (name glob),
   `--ignore-definitions-if-inherits-from` (`_match_many` on `inherits_from`),
   `--ignore-definitions-if-decorated-with` (decorator names), and
   `--ignore-bodies-if-inherits-from`. While the flag is on, all nested `_define`
   calls are suppressed → ignores the definition *and* its body's definitions.
4. **Decorator whitelist via `self.ignore_decorators`** (`visit_ClassDef:443-448`,
   `visit_FunctionDef:462-463`) — skips defining if decorator matches. **This list
   is initialized empty (`:50`) and never populated from CLI args**; only set
   directly in tests (`tests/visitor/test_find_unused_code_visitor.py:92,98`).
   The CLI path uses `--ignore-definitions-if-decorated-with` (mechanism 3) instead.
5. **`__all__` exports** — `_mark_all_exports_used` (`:507-512`) called from
   `visit_Assign/AugAssign/AnnAssign` (`:514-521`); each string element of
   `__all__` is added to `used_names` (`_assigns_special_variable__all__`, `ignore.py:66-71`).
6. **`# noqa`** — `noqa.parse_noqa` (`noqa.py:54-63`) maps flake8 codes
   (`F401→DC07`, `F841→DC01`) and `DCxx` (incl. legacy 3-digit forms) to canonical
   codes; `ignore_line` (`:66-68`) checks the line in the per-code set or the
   `'all'` set. `# type: ignore` is NOT treated as noqa (only `noqa` regex, `:4-14`).
- **Parsed-but-unused CLI flags**: `--ignore-if-decorated-with`,
  `--ignore-if-inherits-from`, `--ignore-names-if-inherits-from`,
  `--ignore-names-if-decorated-with`, `--ignore-bodies-of`,
  `--ignore-bodies-if-decorated-with` are defined in `parse_arguments.py:60-149`
  but never referenced in the visitor (only the six in Q1/Q3 grep are used).

## Q4: Dynamic-usage heuristics

### Findings
- **`getattr`/`hasattr` (`visit_Call:364-372`)**: if `node.func` is a bare `ast.Name`
  with id `getattr` (2-3 args) or `hasattr` (exactly 2 args), and the 2nd arg is a
  string `ast.Constant`, that string is `add_used_name`'d. Boundaries: only
  literal string second args; non-literal (variable) attr names not handled;
  `getattr` requires 2-3 args, `hasattr` exactly 2; only matches unqualified
  `getattr`/`hasattr` (not `builtins.getattr`).
- **`"{}".format(**locals())` (`visit_Call:374-383` → `_handle_new_format_string:385-402`)**:
  triggers only when func is `<str constant>.format` AND a `**`-kwarg whose value
  is exactly `locals()` (`_is_locals_call:404-413`). Field names parsed via
  `string.Formatter().parse`; brackets stripped (`a[0].b`→`a.b`), dotted parts
  split, each identifier marked used. Invalid format strings → no names (`:392-394`).
  Boundary: requires literal string receiver and a literal `locals()` `**` kwarg
  with no args/keywords; `format(**vars())` or `.format(x=...)` not matched.
- **`"%(x)s" % locals()` (`visit_BinOp:350-362`)**: triggers only when left is a
  string `ast.Constant`, op is `ast.Mod`, and right is exactly `locals()`. Names
  extracted via regex `%\((\w+)\)` and unioned into `used_names`. Boundary: only
  `% locals()` (literal), only `%(name)s`-style mapping keys.
- `_is_locals_call` requires `locals` to be a bare Name call with no args/kwargs
  (`:404-413`).

## Q5: Test suite organization

### Findings
- **Shared base: `deadcode/utils/base_test_case.py`** (`class BaseTestCase(TestCase)`,
  `:10`), lives in the package, not under `tests/`. `files: dict[str,str]` class
  attr (`:11`); `maxDiff=None` (`:13`). `setUp` (`:37-57`) patches:
  `cli.find_python_filenames`→`self.files.keys()`; `open` in
  `find_unused_code_visitor`/`fix_unused_code_visitor`/`fix_or_show_unused_code`
  → `_read_file_side_effect` (`:23-35`, returns mock reading
  `fix_indent(self.files[name])`); `os.remove`; and `parse_pyproject_toml`→`{}`.
  Writes captured into `self.updated_files`. Assertion helpers: `assertFiles`
  (`:59-85`, post-fix file state + `removed=`), `assertUpdatedFiles` (`:87-96`).
- **Input mechanism**: tests set `self.files = {'foo.py': """...indented source..."""}`
  then call `main(['foo.py','--no-color', ...])`; no real disk I/O. `fix_indent`
  (`deadcode/utils/fix_indent.py:25-50`) strips common indentation. Real-FS
  exceptions: `tests/test_deadcode.py` (uses `tests/files/`) and
  `tests/actions/test_find_python_filenames.py` (real `TemporaryDirectory`).
- **Directory layout**: top-level correctness files; `tests/frameworks/` (Q6);
  `tests/cli_args/` (per-flag suppression + parsing + fix); `tests/fix/`
  (`--fix` removal per construct); `tests/noqa/`; `tests/nested_scope/`;
  `tests/visitor/` (direct `visit_*` / lines / utils unit tests);
  `tests/actions/`, `tests/code_item/`, `tests/utils/`, `tests/files/` (fixtures).
- **Modern-syntax files & gating**:
  - `tests/test_type_alias.py:8` — `@skipUnless(sys.version_info >= (3,12), ...)`
    on the class.
  - `tests/test_pep695_generics.py:8` — `@skipUnless(sys.version_info >= (3,12), ...)`.
  - `tests/test_match_statement.py` — **no version gate** (relies on host ≥3.10).
  - `tests/test_walrus.py` — **no version gate** (walrus is 3.8+).
  Gating uses `unittest.skipUnless`; no `pytest.mark.skipif`. Unconditional `@skip`
  appears in several files (e.g. `test_accurate_usage_detection.py:7`).
- **Assertion patterns** (two only):
  - Reported: `self.assertEqual(unused_names, 'foo.py:1:0: DC01 Variable `x` is never used')`
    — `main()` returns newline-joined `{file}:{line}:{col}: {CODE} {Type} `name`
    is never used`; with `--fix` appends `\n\nRemoved N unused code item[s]!`.
  - Not reported: `assert unused_names is None` / `self.assertEqual(..., None)` /
    `self.assertIsNone(...)` (all equivalent). Fix tests add `assertFiles({...})`.

## Q6: Framework-specific test coverage & suppression

### Findings
(`tests/frameworks/test_{django,fastapi,sqlalchemy,alembic}.py`)
- **Pattern across all four**: each test feeds framework-shaped definitions plus a
  deliberately-unused helper/constant, then asserts only the helper is reported.
  Suppression always via CLI flags (mechanisms 3, 1.2, 1.3 from Q3) — never the
  unwired `ignore_decorators` whitelist.
- **Django** (`test_django.py`, 7 tests):
  - `models.Model`, `ListView`, `admin.ModelAdmin`, `BaseCommand`, `AppConfig`
    classes → `--ignore-definitions-if-inherits-from=<base>` +
    `--ignore-bodies-if-inherits-from=<base>` (e.g. `:26-27,97-98,155-156,220-221,251-252`).
  - `@admin.register(...)` / `@receiver(...)` → `--ignore-definitions-if-decorated-with=@admin.register*` / `@receiver*` (`:128,187`).
  - Function views referenced in `urlpatterns` → `--ignore-names=urlpatterns` (`:70`).
  - settings constants → `--ignore-names-in-files=*settings*` (`:282`).
- **FastAPI** (`test_fastapi.py`, 2 tests):
  - `@app.*` / `@router.*` route handlers (incl. `websocket`, `on_event`, async)
    → `--ignore-definitions-if-decorated-with=@app.*` + `@router.*` (`:48-49`);
    `get_db` kept alive via `Depends(get_db)` reference.
  - Pydantic `class X(BaseModel)` → `--ignore-definitions-if-inherits-from=BaseModel`
    (`:71`, no body-ignore, so `UnusedPlainClass`/`unused_attribute` still reported).
- **SQLAlchemy** (`test_sqlalchemy.py`, 4 tests):
  - 2.0 `DeclarativeBase` subclass, 1.x `declarative_base()` subclass, Flask
    `db.Model` → `--ignore-definitions-if-inherits-from=Base|db.Model` +
    `--ignore-bodies-if-inherits-from=...` (`:33-34,65-66,124-125`). Dotted base
    `db.Model` matched (see `get_inherits_from` leaf-splitting, `:428-433`).
  - `@event.listens_for(...)` → `--ignore-definitions-if-decorated-with=@event.*` (`:94`).
- **Alembic** (`test_alembic.py`, 2 tests):
  - `upgrade`/`downgrade` + `revision`/`down_revision`/`branch_labels`/`depends_on`
    → six `--ignore-names=<name>` flags (`:36-41`).
  - whole `versions/` dir → `--ignore-names-in-files=*versions*` (`:79`).

## Cross-Cutting Observations
- Unused detection is **name-string based** (flat `used_names` set vs. defined
  `CodeItem.name`), not scope-resolved; `NestedScope` adds usage counts and base
  resolution but does not gate the reported set (`ignore.py:39-42`).
- `_define`'s "ignore = mark as used" trick (`:325`) means every suppression path
  collapses into `used_names`, so a single mechanism (membership in `used_names`)
  ultimately filters output.
- Inheritance resolution flattens dotted bases into both full and leaf names so
  `db.Model` and `*Model` globs both match (`:428-433`, `utils.get_base_name:64-77`).
- Decorator names are normalized to `@a.b.c` strings (`utils.get_decorator_name:53-61`)
  and matched with `fnmatchcase` globs (`ignore.py:49-55`).

## Open Areas
- **Parsed-but-unused CLI flags** (Q3): `--ignore-if-decorated-with`,
  `--ignore-if-inherits-from`, `--ignore-names-if-inherits-from`,
  `--ignore-names-if-decorated-with`, `--ignore-bodies-of`,
  `--ignore-bodies-if-decorated-with` are defined in `parse_arguments.py` but have
  no consumer in the visitor — no test exercises their effect on output.
- `NestedScope.mark_as_used` self-documents (`nested_scopes.py:64-80`) that method
  invocations on instances/classes are not scope-resolved; not further traced here.
- Whether `ast.parse` for `match`/`walrus` tests is guarded on older interpreters
  is left to the host environment (no in-file gate; see Q5).

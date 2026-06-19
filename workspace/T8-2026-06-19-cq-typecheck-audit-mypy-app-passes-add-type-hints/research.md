# Research Findings

## Q1: Structure of the visitor classes (`find_unused_code_visitor.py`, `fix_unused_code_visitor.py`)

### Findings — `FindUnusedCodeVisitor`
- Subclasses `ast.NodeVisitor` (`deadcode/visitor/find_unused_code_visitor.py:42`).
- Overrides `ast.NodeVisitor.visit` (`find_unused_code_visitor.py:504-583`): manually walks `ast.iter_fields`, dispatches `visit_<ClassName>` before child traversal (`:529-533`) and `visit_<ClassName>_after_visiting_child_nodes` after (`:572-575`), and manages a `scope_parts` stack. It does NOT call `generic_visit`.
- `visit_*` methods (all return `-> None`), with the AST node each operates on:
  - `visit_AsyncFunctionDef` `:340` → `ast.AsyncFunctionDef` (delegates to `visit_FunctionDef`)
  - `visit_Attribute` `:343` → `ast.Attribute`
  - `visit_BinOp` `:349` → `ast.BinOp`
  - `visit_Call` `:358` → `ast.Call`
  - `visit_ClassDef` `:424` → `ast.ClassDef`
  - `visit_FunctionDef` `:432` → `ast.FunctionDef | ast.AsyncFunctionDef` (param annotated as union)
  - `visit_If` `:453`, `visit_IfExp` `:456`, `visit_While` `:496`
  - `visit_Import` `:459`, `visit_Import_after_visiting_child_nodes` `:464` (empty `pass` post-hook), `visit_ImportFrom` `:467`
  - `visit_Name` `:483`, `visit_Assign` `:489`
  - `visit_MatchClass` `:500` → param **unannotated**, carries `# type: ignore`
- Other annotated methods: `__init__(filenames: list[str], args: Args) -> None` `:45`; `scope -> str` property `:84`; `add_used_name(name: str, scope: str | None = None) -> None` `:88`; `get_unused_code_items() -> Iterable[CodeItem]` `:154`; seven `unused_*` properties `-> Iterable[CodeItem]` `:173-199`; `_log(*args, file: TextIO | None = None, force: bool = False) -> None` `:201` (`# type: ignore`); `_define(...)` `:273` (uses `Callable[[Path, str], bool] | None`); `get_inherits_from(node: ast.AST) -> list[str] | None` `:408`.
- `__init__` instance attributes carry explicit annotations even though runtime values are `LoggingList`/`LoggingSet`/`defaultdict`: e.g. `self.defined_attrs: list[CodeItem]`, `self.used_names: set[str]`, `self.noqa_lines: dict[str, set[int]]`, `self.scopes: NestedScope`, `self.additional_code_parts_to_remove: dict[Filename, list[Part]]` (`:45-82`). `self.file_content_lines` is set later in `visit_abstract_syntax_trees` `:140` **without annotation**.

### Findings — `FixUnusedCodeVisitor`
- Subclasses `ast.NodeVisitor` (`deadcode/visitor/fix_unused_code_visitor.py:60`). Overrides `visit` (`:422-443`) — dispatches pre-child only, no `_after_visiting_child_nodes` hook.
- `visit_*` methods — note **param-annotation mismatches vs runtime node**:
  - `visit_With` `:261` → operates on `ast.With` but param annotated `node: ast.ClassDef` (mismatch)
  - `visit_ClassDef` `:278` → `ast.ClassDef`
  - `visit_ImportFrom` `:319` → operates on `ast.ImportFrom` but param annotated `node: ast.Import` (mismatch); delegates to `visit_Import`
  - `visit_Import` `:325` → `ast.Import`
  - `visit_Assign` `:398` → `ast.Assign`
- `__init__(find_unused_code_visitor: FindUnusedCodeVisitor) -> None` `:67`. Attrs `self.args`, `self.filenames` set from the passed visitor **without annotation**; `self.additional_code_parts_to_remove: dict[Filename, list[Part]]` annotated `:74`.
- Methods with **missing annotations**: `get_chars_to_remove(self, original_code_lines, fixed_code, first_line, first_col) -> list[tuple[int,int,int,int]]` `:168` (4 params untyped); `add_code_adjustments_for_cleaned_up_code_items(self, node) -> str` `:213` (param untyped, declares `-> str` but body has no `return`). Nested `should_remove(elem: Any)` funcs at `:337` and `:415` use `Any`.

## Q2: Data structures in `data_types.py` (and `code_item.py`)

### Findings
- Type aliases (plain assignments, not `TypeAlias`) — `data_types.py:8-11`: `AbstractSyntaxTree = ast.Module`, `FileContent = str`, `Filename = str`, `Pathname = str`.
- `Args` `@dataclass` `:14-35`: not frozen, all fields have defaults. `bool` fields default `False`; 17 collection fields typed `Iterable[Pathname]` defaulting to `()`. `Iterable` from `collections.abc` (`:5`).
- `Part(NamedTuple)` `:38-51` (from `typing.NamedTuple`, `:4`): `line_start/line_end/col_start/col_end: int` (required); `insert_code: str | None = None`; `insert_code_if_character_is_not_removed: tuple[int, int] | None = None`. Has class docstring + inline block comments.
- `CodeItem` (`deadcode/visitor/code_item.py:38-139`): plain class, uses `__slots__` (`:43-55`, 11 names), no class-level annotations — types live only in `__init__` signature `:57-68`: `name: str`, `type_: UnusedCodeType`, `filename: Path`, `code_parts: list[Part] | None = None` (coerced to `[]` `:77-80`), `scope: str | None`, `inherits_from: list[str] | None`, `name_line/name_column: int | None`, `message: str = ''`, `number_of_uses: int = 0`. `error_code` slot assigned `ERROR_TYPE_TO_ERROR_CODE[type_]` `:82` (type `UnusedCodeErrorCode`). Properties `scoped_name -> str`, `filename_with_position -> str`; `__repr__`, `__eq__(str | CodeItem)`, `__hash__`. A `# TODO` says it should be a dataclass; `:1-29` has commented-out `VariableInfo` dataclass referencing non-existent `IndexInt`/`VariableTypes`.
- Supporting `Literal` types in `constants.py`: `UnusedCodeType` (12 literals, `:4-17`), `UnusedCodeErrorCode` (12 literals, DC10 absent, `:20-33`), and annotated constant `ERROR_TYPE_TO_ERROR_CODE: dict[UnusedCodeType, UnusedCodeErrorCode]` `:36-49`.

## Q3: Data flow `parse_abstract_syntax_tree` → `find_unused_names` → `fix_or_show_unused_code` → `cli.py`

### Findings
- `parse_abstract_syntax_tree(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree` (`deadcode/actions/parse_abstract_syntax_tree.py:6`). Calls `ast.parse(..., type_comments=True)` `:9`; on exception returns bare `ast.Module()` `:13`. NOT called by `find_unused_names` directly — called inside both visitors' `visit_abstract_syntax_trees` (`find_unused_code_visitor.py:111`, `fix_unused_code_visitor.py:89`).
- `find_unused_names(filenames: list[Filename], args: Args) -> tuple[Iterable[CodeItem], list[tuple[int, int, int, int]]]` (`deadcode/actions/find_unused_names.py:9-12`). Returns `(unused_code_items, additional_code_parts_to_remove)` `:24`. First element comes from `get_unused_code_items()` (a sorted `list[CodeItem]`, declared `Iterable[CodeItem]`). Second comes from `FixUnusedCodeVisitor.visit_abstract_syntax_trees() -> dict[Filename, list[Part]]` (`fix_unused_code_visitor.py:76`).
  - **Annotation discrepancy:** return declares the 2nd element `list[tuple[int,int,int,int]]`, but the actual value is `dict[Filename, list[Part]]` (a dict of `Part` NamedTuples, not a list of 4-tuples).
- `fix_or_show_unused_code(unused_items: Iterable[CodeItem], additional_code_parts_to_remove: dict[Filename, list[tuple[int, int, int, int]]], args: Args) -> str` (`deadcode/actions/fix_or_show_unused_code.py:15-19`). Same `dict[..., list[tuple[int,int,int,int]]]` annotation vs runtime `list[Part]` mismatch. Returns `''.join(result)` `:68` or `''` `:69`. Internally groups items by filename, merges parts via `merge_overlaping_file_parts`, calls `remove_file_parts_from_content`, builds `unified_diff`, optionally writes/removes files.
- `cli.py:main(command_line_args: list[str] | None = None) -> str | None` (`deadcode/cli.py:10-12`). Wires: `parse_arguments` → `Args` `:13`; `find_python_filenames(args) -> list[str]` `:15`; unpacks `unused_names, additional_code_parts_to_remove = find_unused_names(...)` `:18`; conditionally `file_diff = fix_or_show_unused_code(...)` `:21-22` (only when `(args.fix or args.dry) and unused_names`); `get_unused_names_error_message(unused_names, args) -> str | None` `:24-25`; returns combined message or `None`.
- All four boundary functions have fully annotated params + returns; the only gaps are the `dict`-vs-`list`/`Part`-vs-`tuple` discrepancy in the second tuple element threaded through Q3.

## Q4: Helpers under `deadcode/utils/`, `visitor/lines.py`, `actions/remove_file_parts_from_content.py`

### Findings
- `remove_from_list(elements: list, should_remove: Callable) -> None` (`deadcode/utils/remove_from_list.py:4`) — **bare `list`** (no element type) and **bare `Callable`** (no subscript). `Callable` from `collections.abc` `:1`.
- `flatten_lists.py`: `T = TypeVar('T')` `:3`; `flatten_lists_of_comma_separated_values(list_of_comma_separated_values: list[list[str]] | None) -> list[str]` `:6-8`; `flatten_list(list_of_lists: list[list[T]] | None) -> list[T]` `:15` (fully generic).
- `print_ast(node: ast.AST) -> None` (`print_ast.py:4`, `# pragma: no cover`).
- `fix_indent(doc: str) -> str | None` (`fix_indent.py:4`).
- `nested_scopes.py` class `NestedScope`: `__init__(self) -> None` `:17` with `self._scopes: dict[str | CodeItem, Any] = {}` `:18`; `add(code_item: CodeItem) -> None` `:20`; `get(name: str, scope: str) -> CodeItem | str | None` `:37` (local `scopes: list[dict[CodeItem | str, dict[Any, Any]]]` `:48`); `mark_as_used(name: str, scope: str) -> None` `:64`. `Any` from `typing` `:1`.
- `add_colors_to_diff(diff: str) -> str` (`add_colors_to_diff.py:1`).
- `visitor/lines.py` — fully annotated: `_get_last_child_with_lineno(node: ast.AST) -> ast.AST | None` `:4` (local `last_field: ast.AST | list[ast.AST]` `:28`); `get_last_line_number(node: ast.AST) -> int` `:40`; `get_first_line_number(node: ast.AST) -> int` `:68` (local `lineno: int` `:79`).
- `actions/remove_file_parts_from_content.py`: `T = TypeVar('T')` `:6`; `list_get(list_: list[T], index: int) -> T | None` `:9`; `ends_with_semicolon`, `indentation_is_not_childs`, `get_indentation`, `remove_as_from_end`, `remove_comma_from_begining` all `(str...) -> str/bool`; `get_code_parts_for_the_same_line(code_parts: list[tuple[int, int, int, int]], index: int) -> list[tuple[int, int, int, int]]` `:44-46`; `remove_unused_fragments_from_a_line(line: str, code_parts, index: int) -> tuple[str, int]` `:61` — **`code_parts` unannotated** (body unpacks it as 6-tuples `:101,108,118`, not 4-tuples); `remove_file_parts_from_content(content_lines: list[str], unused_file_parts: list[Part]) -> list[str]` `:128` (locals annotated `list[str]` `:141-142`).

## Q5: Established type-annotation conventions across `deadcode/`

### Findings
- **No `from __future__ import annotations` anywhere**; no string/forward-reference annotations in active code (only in commented-out `code_item.py:10-26`).
- **Modern generics only** — `list[...]`, `dict[...]`, `set[...]`, `tuple[...]`; no `typing.List/Dict/Set/Tuple`. **`| None` only**; `Optional` appears only in commented-out code (`code_item.py`). Unions use `|`, not `typing.Union`.
- **Import source split is consistent:** `Iterable`/`Callable` from `collections.abc` (`data_types.py:5`, `find_unused_names.py:1`, `fix_or_show_unused_code.py:3`, `remove_from_list.py:1`, `find_unused_code_visitor.py:13`, `ignore.py:4`, `get_unused_names_error_message.py:1`); `Any`/`TypeVar`/`Literal`/`NamedTuple`/`TextIO` from `typing` (`nested_scopes.py:1`, `flatten_lists.py:1`, `remove_file_parts_from_content.py:2`, `constants.py:1`, `data_types.py:4`, `find_unused_code_visitor.py:12`).
- **Generics:** two independent module-local `T = TypeVar('T')` (`flatten_lists.py:3`, `remove_file_parts_from_content.py:6`).
- **Dataclass fields:** built-in type names + defaults (`Args`); `NamedTuple` uses `int`/`str | None`/`tuple[int,int] | None`.
- **Module-level constants:** mostly unannotated (type aliases `data_types.py:8-11`; `Literal` aliases `constants.py:4-33`; `NOQA_REGEXP = re.compile(...)` `noqa.py:4` — no `re.Pattern[str]` annotation anywhere). The one annotated constant is `ERROR_TYPE_TO_ERROR_CODE: dict[UnusedCodeType, UnusedCodeErrorCode]` (`constants.py:36`).
- **Uninferable locals get inline annotations** where the RHS is ambiguous: `nested_scopes.py:18,48`; `base_test_case.py:38`; `remove_file_parts_from_content.py:141-142`; `merge_overlaping_file_parts.py:92`; `visitor/utils.py:31` (`eval_result: bool = ast.literal_eval(node)`); `lines.py:28,79`; `find_python_filenames.py:12` (`paths: list[str] = list(args.paths)`).
- `Any` used deliberately at `nested_scopes.py:18,48`, `base_test_case.py:20-23` (`*args/**kwargs`), and `fix_unused_code_visitor.py:337,415`.

## Q6: mypy configuration (`pyproject.toml` `[tool.mypy]`, `Justfile` recipes)

### Findings
- `[tool.mypy]` (`pyproject.toml:162-170`): `exclude = ["build", "dist", ".venv"]`; `python_version = "3.11"`; **`strict = true`**; `pretty = true`; `color_output = true`; `show_error_codes = true`; `warn_return_any = true`; `warn_unused_configs = true`.
  - `strict = true` enables the full strict bundle (incl. `disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_untyped_calls`, `disallow_any_generics`, `check_untyped_defs`, `no_implicit_optional`, `warn_redundant_casts`, `warn_unused_ignores`, `warn_return_any`, `no_implicit_reexport`, `strict_equality`, etc.). `warn_return_any` and `warn_unused_configs` are also listed explicitly (redundant under strict but present).
- `Justfile` recipes both run `uv run mypy deadcode/`: `typecheck` (`Justfile:19-20`) and `check-typecheck` (`Justfile:31-32`); both depend on the `sync` recipe (`uv pip sync` + editable install). `check` runs `check-typecheck` among the gates (`Justfile:34`).
- mypy targets only `deadcode/` (tests not type-checked). Ruff lint disables some annotation rules globally that mypy would not enforce: `ANN001/ANN002/ANN202/ANN204/ANN401`, `PGH003` (`pyproject.toml:80-150`); tests additionally ignore `ANN201`, `SLF001`, `D` (`:152-159`).

## Cross-Cutting Observations
- The codebase already aims at mypy `strict`, and the bulk of `deadcode/` is fully annotated with modern syntax (`list[...]`, `| None`, `collections.abc`). The few annotation gaps are concentrated and concrete (listed below).
- **Concrete gaps that strict mypy would flag:**
  - Untyped params: `find_unused_code_visitor.py:500` (`visit_MatchClass`, has `# type: ignore`); `fix_unused_code_visitor.py:168` (`get_chars_to_remove`, 4 params), `:213` (`add_code_adjustments_...`); `remove_file_parts_from_content.py:61` (`code_parts`).
  - Bare containers/callables: `remove_from_list.py:4` (`list`, `Callable`).
  - Return-type/body mismatch: `fix_unused_code_visitor.py:213` declares `-> str` with no `return`.
  - Param-annotation vs runtime-node mismatches: `fix_unused_code_visitor.py:261` (`ast.ClassDef` for an `ast.With`), `:319` (`ast.Import` for an `ast.ImportFrom`).
  - Type-thread discrepancy: 2nd tuple element declared `list[tuple[int,int,int,int]]` in `find_unused_names.py:12` / `fix_or_show_unused_code.py:17` vs actual `dict[Filename, list[Part]]`.
  - Existing `# type: ignore` markers: `find_unused_code_visitor.py:201` (`_log`), `:500` (`visit_MatchClass`).

## Open Areas
- This research did not run mypy to enumerate the live error set; whether mypy currently passes or fails on `deadcode/` was not executed (the questions asked for configuration/structure, not a live run). The gaps above are derived from static reading and would need a `just check-typecheck` run to confirm exact diagnostics.
- `parse_arguments.py`, `get_unused_names_error_message.py`, `merge_overlaping_file_parts.py`, `ignore.py`, `noqa.py`, `visitor/utils.py` were only sampled for conventions, not exhaustively audited for annotation gaps.

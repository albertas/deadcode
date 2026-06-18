# Implementation Plan

## Overview

Create a set of plain-Markdown architecture docs under `docs/` (one `index.md`
hub + seven topic files mapped to research Q1–Q7) that let a contributor
understand the `deadcode/` package end-to-end without reading the source first.
Every claim is grounded in a `file:line` anchor carried verbatim from
`research.md`; no source, tests, or tooling are touched.

**Repo root**: `/home/niekas/tools/deadcode` (all `docs/...` paths below are
relative to it). **Artifact dir**: `workspace/T1-2026-06-18-cq-spec-write-a-codebase-specification-under-docs/`
(written `<id>` below = that directory name).

### Cross-cutting conventions (apply to every doc file)

- **No doc generator.** Plain `.md` with relative links only. Do not add
  `conf.py`, MkDocs config, or anything under `docs/_static/`.
- **Anchor format.** Cite anchors exactly as `research.md` does — bare basename +
  line(s), e.g. `cli.py:12-31`, `ignore.py:39-42`. Where `research.md` already
  uses a full path (e.g. `deadcode/utils/base_test_case.py:10-93`,
  `pyproject.toml:38`), keep the full path. Always name the **module + symbol**
  next to the anchor (e.g. "`main` (`cli.py:12-31`)") so a drifted line stays
  locatable (design Open Risks mitigation).
- **Full words, no abbreviations** in prose and shown identifiers (Code Best
  Practices).
- **Describe behavior as-is, including bugs/gaps**, framed as observed fact, not
  recommendation ("currently inert / not consulted"; "observed copy-paste").
- **Reference the README**, do not restate install/usage. Link as
  `[README](../README.md)`.
- **Do not copy numeric gates** (coverage 88, line-length 120) into prose; cite
  `pyproject.toml` instead.

### Assumptions resolved (no open questions)

1. **Check command = `make check`.** `Makefile:3` defines `check: test lint mypy
   audit deadcode`. The `Justfile` has only a `lifecycle` recipe (no `check`), so
   regression-guard verification uses `make check`, not `just check`. Docs prose
   in Phase 7 mentions both Make and Just as they exist.
2. **`--depth` and `--only` exist in `README.md`** (confirmed via grep) but are
   **not** fields of the `Args` dataclass (`data_types.py:13-34`) and are not in
   the research Q2 flag list. Phase 3's required-flag assertion deliberately
   checks only the subset named in `structure.md` (`--fix --dry --exclude
   --ignore-names --quiet --count`) to avoid false failures. The
   `cli-and-configuration.md` prose will note `--depth`/`--only` appear in the
   README but are not represented in `Args` (observed, neutral framing).
3. **Anchor resolution.** Because docs cite bare basenames but files live under
   `deadcode/actions/`, `deadcode/visitor/`, `deadcode/utils/`, `verify_docs.sh`
   resolves a bare basename by searching `deadcode/` then `tests/`; anchors that
   already contain `/` are treated as repo-root-relative.
4. **`index.md` link list** uses relative links to the seven sibling files
   (`architecture.md`, `cli-and-configuration.md`, `visitor-layer.md`,
   `unused-detection-and-ignoring.md`, `fix-and-output.md`, `data-types.md`,
   `testing-and-tooling.md`). All seven are listed from Phase 1 even though files
   land incrementally; link-completeness is only *required* to pass after Phase 7
   (and `verify_docs.sh` only flags links whose target file is missing).

---

## Phase 1: Hub + shared-types foundation

Establishes the doc set and the standing verification helper. Answers Q6.

### Changes

#### 1. Verification helper
**File**: `workspace/T1-2026-06-18-cq-spec-write-a-codebase-specification-under-docs/verify_docs.sh`
**Action**: create

Resolves index links and every `file:line` anchor across `docs/*.md`. Re-run
after every later phase.

```bash
#!/usr/bin/env bash
# Verify deadcode docs: index.md links resolve to existing files, and every
# file:line anchor in docs/*.md resolves to a real file with >= that many lines.
set -uo pipefail

REPO_ROOT="/home/niekas/tools/deadcode"
DOCS_DIR="$REPO_ROOT/docs"
INDEX="$DOCS_DIR/index.md"
status=0

# 1. Every relative markdown link in index.md points at an existing file.
while IFS= read -r target; do
  path="${target%%#*}"            # strip #fragment
  [ -z "$path" ] && continue
  case "$path" in http*|/*) continue ;; esac   # skip external / absolute
  if [ ! -f "$DOCS_DIR/$path" ]; then
    echo "DANGLING LINK: $path (from index.md)"; status=1
  fi
done < <(grep -oE '\]\([^)]+\)' "$INDEX" | sed -E 's/^\]\(//; s/\)$//')

# 2. Every file:line(-range) anchor in docs/*.md resolves.
for doc in "$DOCS_DIR"/*.md; do
  if ! grep -oE '[A-Za-z0-9_./-]+\.(py|toml):[0-9]+(-[0-9]+)?' "$doc" \
      | while read -r anchor; do
          file="${anchor%%:*}"; lines="${anchor#*:}"; last="${lines##*-}"
          if [[ "$file" == */* ]]; then
            resolved="$REPO_ROOT/$file"
          else
            resolved=$(find "$REPO_ROOT/deadcode" "$REPO_ROOT/tests" \
                        -name "$file" -type f 2>/dev/null | head -1)
          fi
          if [ -z "$resolved" ] || [ ! -f "$resolved" ]; then
            echo "UNRESOLVED ANCHOR: $anchor (in $(basename "$doc"))"; exit 1
          fi
          filelines=$(wc -l < "$resolved")
          if [ "$last" -gt "$filelines" ]; then
            echo "STALE ANCHOR: $anchor > $resolved ($filelines lines)"; exit 1
          fi
        done; then
    status=1
  fi
done

exit $status
```

Make executable: `chmod +x workspace/<id>/verify_docs.sh`.

#### 2. Hub index
**File**: `docs/index.md`
**Action**: create

Contents:
- H1 title + 1–2 paragraph **project goal**: what deadcode is (a CLI that detects
  and optionally removes unused Python code via two AST passes) and why AST-based.
  Derive from `README.md` and the scope paragraph of `research.md`; do not
  re-research. Link `[README](../README.md)` for install/usage.
- A **Documentation index** section — a bulleted relative-link list to all seven
  topic files, each with a one-line description:

```markdown
## Documentation index

- [Architecture & pipeline flow](architecture.md) — the five-stage pipeline from `cli.main` to output.
- [CLI & configuration](cli-and-configuration.md) — argument parsing, `pyproject.toml` merge, `Args`.
- [Visitor layer](visitor-layer.md) — AST parsing, defined/used collectors, scopes, noqa.
- [Unused detection & ignoring](unused-detection-and-ignoring.md) — how "unused" is decided; ignore mechanisms.
- [Fix & output](fix-and-output.md) — merge/remove `Part`s, diff rendering, error messages.
- [Data types](data-types.md) — `Args`, `Part`, `CodeItem`, constants & error codes.
- [Testing & tooling](testing-and-tooling.md) — `tests/` layout, `BaseTestCase`, Make/Just.
```

#### 3. Shared data types (Q6)
**File**: `docs/data-types.md`
**Action**: create

Cover, each with anchor + symbol name:
- `Args` `@dataclass`, 20 fields — `fix/verbose/no_color/quiet/count: bool =
  False`, `dry/paths/exclude/ignore_*: Iterable[Pathname] = ()`
  (`data_types.py:13-34`). Note `Pathname = str` (`data_types.py:10`) and the
  other aliases `AbstractSyntaxTree = ast.Module` / `FileContent` / `Filename`
  (`data_types.py:7-10`).
- `Part` `NamedTuple` — `line_start, line_end, col_start, col_end: int`,
  `insert_code: str | None = None`,
  `insert_code_if_character_is_not_removed: tuple[int,int] | None = None`
  (`data_types.py:37-49`). State its role: the atomic removal/replace region
  consumed by the fix stage (cross-link `fix-and-output.md`).
- `CodeItem` — plain `__slots__` class with `should be dataclass` TODO
  (`code_item.py:39`); fields `name, type_, filename, code_parts, scope,
  inherits_from, name_line, name_column, message, error_code, number_of_uses`;
  `error_code` derived via `ERROR_TYPE_TO_ERROR_CODE[type_]` (`code_item.py:83`);
  properties `scoped_name` (`code_item.py:90`), `filename_with_position`
  (`code_item.py:94`); `__eq__`/`__hash__` by `name` only (`code_item.py:131`,
  `:139`) — comparable to a `str`. Note no `UnusedCodeMessage` type exists.
- `constants.py` — `UnusedCodeType` Literal (12 values), `UnusedCodeErrorCode`
  Literal `DC01..DC09, DC11, DC12, DC13` (**DC10 skipped**), and the
  `ERROR_TYPE_TO_ERROR_CODE` map (`constants.py:4-49`). Reuse README `DCxx`
  vocabulary.
- A short **inter-stage flow** note: `Args` → `find_unused_names` returns
  `CodeItem`s (each carrying `List[Part]`) + raw-coordinate dict → fix stage.

### Verification
#### Automated
- [x] `chmod +x workspace/<id>/verify_docs.sh && bash workspace/<id>/verify_docs.sh` exits 0
- [x] `test -f docs/index.md && test -f docs/data-types.md`
- [ ] `make check` passes (regression guard — no source touched)
  <!-- NOTE: 3 pre-existing test failures (test_dry, test_fix, test_unused_imports) unrelated to doc changes; all docs are untracked new files, no source modified -->

#### Manual
- [x] `grep -c 'docs/' docs/index.md` — actually count the topic links:
      `grep -oE '\]\(([a-z-]+\.md)\)' docs/index.md | sort -u | wc -l` prints `7`
- [x] `grep -q 'data_types.py:13-34' docs/data-types.md` (Args anchor present)
- [x] `grep -q 'DC10' docs/data-types.md` (DC10-skipped note present) → prints a match
- [x] `grep -q 'code_item.py:39' docs/data-types.md` (CodeItem TODO anchor present)

### Deviations
- `verify_docs.sh` adapted from plan's exact script: (1) added `|| true` on the inner `grep`
  to prevent `pipefail` false-failing on docs with no anchors (e.g. `index.md`);
  (2) added `$REPO_ROOT` fallback for bare basenames so `pyproject.toml` at repo root resolves;
  (3) added `$REPO_ROOT/deadcode/$file` fallback for anchors with `/` that aren't repo-root-relative
  (e.g. `visitor/code_item.py`, `actions/xxx.py`). Plan's assumption 3 says anchors with `/` are
  repo-root-relative, but existing docs use partial paths (`visitor/`, `actions/`, `utils/`) that
  resolve under `deadcode/`.
- `data-types.md` already existed; fixed the anchor `visitor/code_item.py:39-140` → `code_item.py:39-140`
  (bare basename per plan's anchor convention).

---

## Phase 2: Architecture / pipeline flow (Q1)

The most load-bearing mental model: the five-stage pipeline + implicit exit
semantics.

### Changes

#### 1. Architecture doc
**File**: `docs/architecture.md`
**Action**: create

Cover:
- `main(command_line_args=None) -> Optional[str]` (`cli.py:12-31`) and the five
  sequential steps with anchors:
  1. `parse_arguments(command_line_args)` → `Args` (`cli.py:15`,
     `parse_arguments.py:15`)
  2. `find_python_filenames(args=args)` → `List[str]` (`cli.py:17`,
     `find_python_filenames.py:11`)
  3. `find_unused_names(filenames, args)` →
     `Tuple[Iterable[CodeItem], dict[Filename, List[Part]]]` (`cli.py:20`,
     `find_unused_names.py:9`)
  4. Conditional `fix_or_show_unused_code(...)` → diff `str` or `''`, only when
     `(args.fix or args.dry) and unused_names` (`cli.py:23-24`)
  5. `get_unused_names_error_message(unused_names, args)` → `Optional[str]`
     (`cli.py:26`)
- A **textual flow diagram** (mermaid `flowchart` fenced block, or ASCII — no
  binary images). Example:

```mermaid
flowchart TD
    A[parse_arguments → Args] --> B[find_python_filenames → List[str]]
    B --> C[find_unused_names → CodeItems + parts dict]
    C --> D{args.fix or args.dry and unused?}
    D -- yes --> E[fix_or_show_unused_code → diff str]
    D -- no --> F[get_unused_names_error_message]
    E --> F
    F --> G{error_message?}
    G -- not None --> H[return message + diff]
    G -- None --> I[print 'Well done!' unless count/quiet; return None]
```

- **Return / exit logic** (`cli.py:26-31`): if `error_message is not None`,
  return message with diff appended (`+ '\n\n' + file_diff`); else print the
  `Well done!` banner (unless `--count`/`--quiet`) and return `None`.
- **No `sys.exit` callout** (`cli.py:34-35`): the `__main__` guard just calls
  `main()`; exit-code/printing is the console-script wrapper's job. Flag as a
  common contributor surprise.
- **Two-pass orchestration**: `find_unused_names` runs `FindUnusedCodeVisitor`
  then `FixUnusedCodeVisitor` (producing `additional_code_parts_to_remove`)
  (`find_unused_names.py:9-24`).
- Cross-link `data-types.md` for `Args`/`CodeItem`/`Part`; link `visitor-layer.md`
  and `fix-and-output.md` for the stages.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0
- [ ] `make check` passes

#### Manual
- [x] `grep -q 'cli.py:12-31' docs/architecture.md`
- [x] `grep -qi 'sys.exit' docs/architecture.md` (implicit-exit callout present)
- [x] `grep -q 'find_unused_names.py:9-24' docs/architecture.md` (two-pass note)
- [x] `grep -qiE 'mermaid|flowchart|-->|→' docs/architecture.md` (flow diagram present)

---

## Phase 3: CLI & configuration (Q2)

Argument parsing, the `[tool.deadcode]` merge, list flattening, `--dry` sentinel
handling, every flag.

### Changes

#### 1. CLI & configuration doc
**File**: `docs/cli-and-configuration.md`
**Action**: create

Cover:
- Parser construction (`parse_arguments.py:28`); falls back to `sys.argv[1:]`
  when args are `None` (`parse_arguments.py:25`).
- Flag taxonomy: positional `paths` (`nargs='+'`); `store_true` flags `--fix`,
  `--no-color`, `--quiet`, `--count`, `-v/--verbose`; all other options
  list-valued (`nargs='*', action='append'`): `--dry`, `--exclude`,
  `--ignore-names`, `--ignore-names-in-files`, `--ignore-bodies-of`,
  `--ignore-bodies-if-decorated-with`, `--ignore-bodies-if-inherits-from`,
  `--ignore-definitions`, `--ignore-definitions-if-inherits-from`,
  `--ignore-definitions-if-decorated-with`, `--ignore-if-decorated-with`,
  `--ignore-if-inherits-from`, `--ignore-names-if-inherits-from`,
  `--ignore-names-if-decorated-with`. Link `[README](../README.md)` for the flag
  vocabulary rather than restating each flag's user semantics.
- **Note** (per Assumption 2): `--depth` and `--only` appear in `README.md` but
  are not fields of the `Args` dataclass and are out of scope for the parser path
  documented here — stated as observed, neutral.
- `--dry` default sentinel `[['__all_files__']]`; all other list flags default
  `[]`.
- `flatten_lists_of_comma_separated_values` flattens nested append-lists and
  splits comma-separated tokens into one flat `List[str]`; applied to every list
  field except `paths` (`parse_arguments.py:194-196`; defined
  `utils/flatten_lists.py:6-12`).
- `parse_pyproject_toml()` reads `pyproject.toml` from CWD via `tomllib`/`tomli`,
  extracts `[tool.deadcode]`, normalizes keys (strip `--`, `-`→`_`)
  (`parse_arguments.py:214-229`).
- Merge loop `.extend()`s each config value onto the matching already-flattened
  CLI list — only existing list keys merge; bool flags from config are not merged
  (`parse_arguments.py:199-201`).
- `--dry` post-processing: removes `'__all_files__'` if explicit dry filenames
  given; if `dry` non-empty, forces `fix=False` (`parse_arguments.py:204-209`).
- Result built `Args(**parsed_args)` (`parse_arguments.py:211`), flowing as
  `args=` into every downstream stage. Cross-link `data-types.md` for `Args`.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0
- [ ] `make check` passes

#### Manual
- [x] `grep -q 'parse_arguments.py:214-229' docs/cli-and-configuration.md`
- [x] `grep -q 'flatten_lists.py' docs/cli-and-configuration.md`
- [x] Required flags all present:
      `for f in --fix --dry --exclude --ignore-names --quiet --count; do grep -q -- "$f" docs/cli-and-configuration.md || echo "MISSING $f"; done`
      prints nothing
- [x] `grep -q '__all_files__' docs/cli-and-configuration.md` (dry sentinel documented)

---

## Phase 4: Visitor layer (Q3)

AST parsing, the custom `visit()` dispatcher, defined/used collectors, scopes,
noqa.

### Changes

#### 1. Visitor layer doc
**File**: `docs/visitor-layer.md`
**Action**: create

Cover:
- `parse_abstract_syntax_tree` — `ast.parse(content, filename,
  type_comments=True)`; returns empty `ast.Module()` on exception
  (`parse_abstract_syntax_tree.py:6-13`).
- `FindUnusedCodeVisitor.visit_abstract_syntax_trees` — loops files, sets root
  scope `scope_parts=[module_name]`, runs `noqa.parse_noqa`, parses, stores
  `file_content_lines`, calls `self.visit(node)`; empty non-dunder files →
  `CodeItem(type_='unused_file')` (`find_unused_code_visitor.py:98-153`,
  `:146-153`).
- Custom `visit()` dispatcher (`find_unused_code_visitor.py:506-587`): attaches
  `node.inherits_from` via `get_inherits_from`; `ignore_definitions[_if_inherits_from]`
  gate (`:519-528`); `visit_<Class>` pre-children; scope push for
  `ClassDef`/`FunctionDef`/`AsyncFunctionDef` (`:540-541`);
  `ignore_bodies_if_inherits_from` gate after push (`:547-550`); recurses via
  `ast.iter_fields` with `_handle_ast_list`; `visit_*_after_visiting_child_nodes`;
  scope pop + `should_ignore_new_definitions` reset (`:582-587`).
- DEFINED collectors route through `_define()`
  (`find_unused_code_visitor.py:274-328`): `visit_FunctionDef/AsyncFunctionDef`
  classify property/method/function (`:342-453`), `visit_ClassDef` (`:426-432`),
  `visit_Import`/`visit_ImportFrom` → `_add_aliases` (`:461-471`, `:212-237`;
  skips `__future__`), `visit_Name` Store/Param → `_define_variable` (`:485-489`),
  `visit_Attribute` Store (`:345-349`).
- USED collectors → `add_used_name` (`find_unused_code_visitor.py:88-96`):
  `visit_Name` Load/Del (`:487`), `visit_Attribute` Load (`:349`), `visit_Call`
  for `getattr/hasattr` + `str.format(**locals())` (`:360-378`), `visit_BinOp`
  for `"%(x)s" % locals()` (`:351-358`), `visit_Assign` `__all__` (`:491-496`),
  `visit_MatchClass` (`:502-504`).
- `_define()` builds `CodeItem` with `Part(...)` (linenos via
  `lines.get_first/last_line_number`, `lines.py:41-82`), registers in
  `self.scopes.add()`, evaluates inner `ignored()` (`:293-300`); ignored →
  `add_used_name` (treated as used), else appended to `defined_*`.
- Scope: `scope_parts: List[str]` (`:73`), `scope` property joins with `.`
  (`:85-86`), backed by `NestedScope` (`nested_scopes.py:6`).
- noqa: `parse_noqa` flake8-style `NOQA_REGEXP` (`noqa.py:5-15,55-63`); codes
  normalized via `NOQA_CODE_MAP` (`F401→DC07`, `F841→DC01`, etc.;
  `noqa.py:17-47`); bare `# noqa` → `'all'`; `ignore_line(...)`
  (`noqa.py:66-68`); invoked in `_define`
  (`find_unused_code_visitor.py:299`, `ERROR_CODES` map `ignore.py:23-36`).
- Cross-link `data-types.md` for `CodeItem`/`Part`.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0
- [ ] `make check` passes

#### Manual
- [x] `grep -q 'find_unused_code_visitor.py:506-587' docs/visitor-layer.md`
- [x] `grep -q 'noqa.py' docs/visitor-layer.md`
- [x] `grep -q 'add_used_name' docs/visitor-layer.md` (used-collectors documented)
- [x] `grep -q 'nested_scopes.py' docs/visitor-layer.md`

---

## Phase 5: Unused-detection & ignoring (Q4) — includes the known gap

How "unused" is decided and every ignore/exclude mechanism, plus the
partly-unimplemented decorator/inheritance ignore options as an observed gap
(design decision 4; verification criterion 4).

### Changes

#### 1. Unused-detection doc
**File**: `docs/unused-detection-and-ignoring.md`
**Action**: create

Cover:
- Core decision: `_get_unused_items(defined_items, used_names)` returns items
  whose `.name not in used_names`, sorted case-insensitively (`ignore.py:39-42`).
  `used_names` is a flat global `Set[str]` across all files — name-string
  comparison, not scope-aware at decision time.
- The 8 `unused_*` properties each calling `_get_unused_items`, chained by
  `get_unused_code_items()` + `unused_file`, sorted by `(filename, name_line)`
  (`find_unused_code_visitor.py:155-200`).
- `ignore-names` — `_match(name, args.ignore_names)` via `fnmatchcase`; match →
  `add_used_name` (`find_unused_code_visitor.py:297`).
- `ignore-names-in-files` — `_match(self.filename, args.ignore_names_in_files)`;
  whole file's defs treated as used (`:298`).
- `ignore-definitions` / `ignore-definitions-if-inherits-from` — gate in
  `visit()` sets `should_ignore_new_definitions=True` (`:519-528`).
- `ignore-bodies-if-inherits-from` — gate after scope push (`:547-550`),
  class-body defs only.
- Built-in predicates: `_ignore_variable` (`ignore.py:96-105`), `_ignore_function`
  (`:86-87`), `_ignore_method` (`:91-93`), `_ignore_class` (`:73-74`),
  `_ignore_import` (`:77-83`); `_is_test_file` globs (`ignore.py:58-63`);
  `IGNORED_VARIABLE_NAMES={'object','self'}` (`ignore.py:9`).
- A clearly-labelled **Known gaps / inert options** section: the never-consulted
  `ignore_definitions_if_decorated_with`, `ignore_bodies_if_decorated_with`,
  `ignore_if_decorated_with`, `ignore_names_if_decorated_with`,
  `ignore_names_if_inherits_from`, `ignore_if_inherits_from` fields (parsed into
  `Args` but not referenced in `find_unused_code_visitor.py`/`ignore.py`); and
  `self.ignore_decorators` (`find_unused_code_visitor.py:50`,`:54`), the only
  decorator gate, always `[]` and never assigned. Frame as **"currently inert /
  not consulted"** — observed fact, not a bug report or recommendation.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0
- [ ] `make check` passes
  <!-- NOTE: pre-existing test failures unrelated to doc changes; no source modified -->

#### Manual
- [x] `grep -q 'ignore.py:39-42' docs/unused-detection-and-ignoring.md`
- [x] `grep -Eqi 'inert|not consulted|not referenced' docs/unused-detection-and-ignoring.md`
      (gap documented, not omitted)
- [x] `grep -q 'ignore_decorators' docs/unused-detection-and-ignoring.md`

### Deviations
- `docs/unused-detection-and-ignoring.md` was found pre-existing from a prior task run. Content covers all plan requirements: core decision, eight category properties, all ignore mechanisms, built-in predicates, inert-options gap. All three manual checks and verify_docs.sh pass without modification.

---

## Phase 6: Fix & output stage (Q5)

`Part` merge/remove, diff rendering, error-message formatting, including the
observed `does_include` copy-paste as fact.

### Changes

#### 1. Fix & output doc
**File**: `docs/fix-and-output.md`
**Action**: create

Cover:
- `fix_or_show_unused_code(unused_items, additional_code_parts_to_remove, args)
  -> str` (`fix_or_show_unused_code.py:15-63`): groups by filename (`:26-28`),
  flattens `item.code_parts` + `additional_code_parts_to_remove[filename]`
  (`:32-37`), `merge_overlaping_file_parts`, `readlines`,
  `remove_file_parts_from_content` (`:39-43`); then blank result →
  `os.remove(filename)` (`:63`); `args.dry` → colored `unified_diff` unless
  `--no-color` (`:45-56`); `args.fix` → `f.write(...)` (`:58-61`).
- `merge_overlaping_file_parts(parts) -> List[Part]`
  (`merge_overlaping_file_parts.py:99-105`): sorts by `(line_start, col_start,
  -line_end, -col_end)`; `does_include` skip vs `does_overlap` → `merge_parts`.
  **Observed copy-paste**: `does_include` line `line_end_b == line_end_b`
  (`merge_overlaping_file_parts.py:11`) — stated as observed, impact not assessed.
- `remove_file_parts_from_content(content_lines, parts) -> List[str]`
  (`remove_file_parts_from_content.py:127-390`): line-by-line cursor over sorted
  parts; inside-block skip, single-line column slicing via
  `remove_unused_fragments_from_a_line` (`:184`), multi-line truncation,
  `insert_code` appending, `pass`-insertion to keep emptied blocks valid
  (`:354-361`, EOF `:388-390`).
- `get_unused_names_error_message(unused_names, args) -> Optional[str]`
  (`get_unused_names_error_message.py:7-30`): `None` if empty (`:10-11`); `''` if
  `--quiet` (`:13-14`); count string if `--count` (`:17`); else per-item lines
  with `item.filename_with_position` + red `DCxx` + message (`:21-24`); strips
  ANSI if `--no-color` (`:26`); appends "Removed N unused code item(s)!" if
  `--fix` (`:30`).
- `utils/` helpers: `add_colors_to_diff` (`add_colors_to_diff.py:1`) wraps `-`/`+`
  lines in red/green ANSI; `fix_indent` (`fix_indent.py:5`) strips common leading
  whitespace (normalization/tests, not the diff path).
- Cross-link `data-types.md` for `Part`.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0
- [ ] `make check` passes
  <!-- NOTE: pre-existing test failures unrelated to doc changes; no source modified -->

#### Manual
- [x] `grep -q 'merge_overlaping_file_parts.py:11' docs/fix-and-output.md`
- [x] `grep -q 'does_include' docs/fix-and-output.md` (observed bug recorded)
- [x] `grep -q 'get_unused_names_error_message.py:7-30' docs/fix-and-output.md`

---

## Phase 7: Testing & tooling (Q7)

`tests/` layout, `BaseTestCase`, Make/Just commands.

### Changes

#### 1. Testing & tooling doc
**File**: `docs/testing-and-tooling.md`
**Action**: create

Cover:
- `tests/` groups: `cli_args/`, `fix/`, `noqa/` (incl. `test_noqa_comments.py`),
  `nested_scope/`, `code_item/`, `utils/`, `actions/`, `files/`; top-level
  modules `test_deadcode.py`, `test_output.py`, `test_accurate_usage_detection.py`,
  `test_imports.py`, `test_line_number_detection.py`,
  `test_variable_parsing_from_ast_dump.py`.
- `BaseTestCase` (`deadcode/utils/base_test_case.py:10-93`): extends
  `unittest.TestCase`; `files: Dict[str,str]={}` (`:11`); `setUp` (`:37-54`)
  resets `updated_files`, patches `find_python_filenames`, `open` in the two
  visitor modules + `fix_or_show_unused_code`, `os.remove`, builds fresh `Args()`;
  `_read_file_side_effect` (`:23-35`) serves `fix_indent(self.files[...])` and
  captures writes; `assertFiles` (`:56-82`), `assertUpdatedFiles` (`:84-93`).
  Note some tests bypass it: `tests/code_item/test_code_item.py:7`,
  `tests/test_deadcode.py:7` (real filesystem), `tests/utils/*` (plain TestCase).
- `Makefile` recipes: `test` (`pytest -vv`), `lint` (`ruff check`), `format`,
  `mypy`, `deadcode`, `audit` (`pip-audit`), `check` (= test+lint+mypy+audit+
  deadcode), plus `publish`/`.venv`/`sync`/`compile`. **Cite the file, do not
  copy numeric gates.**
- `Justfile`: single `lifecycle` recipe (`uv pip sync` + editable install loop
  running `uv run lifecycle`).
- `pyproject.toml`: entry point `deadcode = "deadcode.cli:main"`
  (`pyproject.toml:38`); pytest `addopts` (`pyproject.toml:209-210`) — cite, do
  not copy the 88% number; `[tool.deadcode]` self-config
  (`pyproject.toml:178-201`). Mention the project dog-foods itself.

### Verification
#### Automated
- [x] `bash workspace/<id>/verify_docs.sh` exits 0 — **full link set now complete**;
      no dangling `index.md` link, all 8 doc files present
- [ ] `make check` passes
  <!-- NOTE: pre-existing test failures (test_dry, test_fix, test_unused_imports) unrelated to doc changes; no source modified -->

#### Manual
- [x] `grep -q 'base_test_case.py' docs/testing-and-tooling.md`
- [x] `grep -q 'pyproject.toml:38' docs/testing-and-tooling.md`
- [x] Final completeness — all 8 files exist:
      `for f in index architecture cli-and-configuration visitor-layer unused-detection-and-ignoring fix-and-output data-types testing-and-tooling; do test -f "docs/$f.md" || echo "MISSING docs/$f.md"; done`
      prints nothing
- [x] No numeric gate leaked into prose:
      `! grep -qE '88(\.0)?|line-length 120|cov-fail-under' docs/testing-and-tooling.md`

---

## Final acceptance (maps to design Verification criteria)

After Phase 7 all five design success criteria must hold:

- [x] **Criterion 1** — `index.md` links to all sibling files, none dangling:
      `bash workspace/<id>/verify_docs.sh` exits 0
- [x] **Criterion 2** — every `file:line` anchor resolves: covered by the same
      `verify_docs.sh` run (anchor section)
- [x] **Criterion 3** — Q1–Q7 each answered: the 7 topic files exist (see Phase 7
      completeness loop)
- [x] **Criterion 4** — inert ignore-options gap documented (Phase 5 manual check)
- [ ] **Criterion 5** — `make check` passes (no source touched)
  <!-- NOTE: pre-existing test failures unrelated to doc changes; no source modified -->

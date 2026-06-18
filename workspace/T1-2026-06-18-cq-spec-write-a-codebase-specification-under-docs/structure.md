# Structure Outline

## Approach

Write plain Markdown under `docs/` (no Sphinx/MkDocs), one hub `index.md` plus
seven topic files mapped to research Q1–Q7 and to the package's own module
boundaries (actions / visitor / utils / data_types+constants). Every claim is
grounded in `file:line` carried verbatim from `research.md`, with module+symbol
names cited alongside line numbers so stale anchors stay locatable.

Because this deliverable is documentation, a "vertical slice" is **one complete
doc file**: it fully answers its research question(s), grounds claims in
resolvable `file:line` anchors, and is wired into `index.md` so the hub's link
set stays complete after every phase. Each phase is independently valuable — if a
later phase is dropped, the docs written so far remain correct and linked. All
paths below are relative to the repo root `/home/niekas/tools/deadcode`.

A reusable verification helper is introduced in Phase 1 and re-run after every
later phase, so link-completeness and anchor-resolution are continuously
enforced rather than checked once at the end.

---

## Phase 1: Hub + shared-types foundation

Establishes the documentation set: the `index.md` hub (project goal + link
index) and `data-types.md` (Q6 — the shared `Args`/`Part`/`CodeItem`/constants
that every other doc cross-links to). Also adds a small verification script.

**Files**: `docs/index.md`, `docs/data-types.md`,
`workspace/<id>/verify_docs.sh`

**Key changes**:
- `docs/index.md` — project goal (derived from `README.md` + `research.md` scope)
  and a relative-link list to all seven topic files (links may point at
  not-yet-written files; completeness is enforced once all phases land).
- `docs/data-types.md` documents: `Args` `@dataclass` 20 fields
  (`data_types.py:13-34`), `Part` `NamedTuple`
  (`data_types.py:37-49`), `CodeItem` `__slots__` class incl. `should be
  dataclass` TODO (`code_item.py:39`, `:83`, `:90`, `:94`, `:131`, `:139`),
  type aliases (`data_types.py:7-10`), `constants.py` Literals + the
  `ERROR_TYPE_TO_ERROR_CODE` map (DC10 skipped) (`constants.py:4-49`).
- `verify_docs.sh` — for each markdown link target in `docs/index.md`, assert the
  file exists; for each `path:line` anchor in `docs/*.md`, assert the file has
  ≥ that many lines.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0 (all `index.md` links
resolve to existing files; all anchors in `data-types.md` resolve);
`test -f docs/index.md && test -f docs/data-types.md`;
`grep -c 'docs/' docs/index.md` reports ≥ 7 link entries; `make check` still
passes (regression guard — no source touched).

---

## Phase 2: Architecture / pipeline flow (Q1)

Documents the single most load-bearing mental model: the five-stage pipeline
`cli.main` → output/file mutation, with a textual flow diagram and the implicit
exit semantics callout.

**Files**: `docs/architecture.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/architecture.md` covers `main(command_line_args=None) -> Optional[str]`
  (`cli.py:12-31`) and the five steps: `parse_arguments` → `find_python_filenames`
  → `find_unused_names` → conditional `fix_or_show_unused_code` →
  `get_unused_names_error_message`. Includes a text/mermaid flow diagram,
  return/exit logic (`cli.py:26-31`), the **no `sys.exit`** callout
  (`cli.py:34-35`), and the two-pass `find_unused_names` orchestration
  (`find_unused_names.py:9-24`). Cross-links data-types for `Args`/`CodeItem`/`Part`.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0; `grep -q 'cli.py:12-31'
docs/architecture.md` and `grep -qi 'sys.exit' docs/architecture.md` (the implicit-
exit callout is present); `make check` passes.

---

## Phase 3: CLI & configuration (Q2)

Documents argument parsing, the `pyproject.toml` `[tool.deadcode]` merge, list
flattening, the `--dry` sentinel post-processing, and every flag.

**Files**: `docs/cli-and-configuration.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/cli-and-configuration.md` covers parser construction
  (`parse_arguments.py:28`), `store_true` vs list-valued flags
  (`parse_arguments.py` Q2 list), `flatten_lists_of_comma_separated_values`
  (`utils/flatten_lists.py:6-12`), `parse_pyproject_toml`
  (`parse_arguments.py:214-229`), the `.extend()` merge loop
  (`parse_arguments.py:199-201`), `--dry` sentinel handling
  (`parse_arguments.py:204-209`), and `Args(**parsed_args)`
  (`parse_arguments.py:211`). Links README for flag vocabulary; links data-types
  for `Args`.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0; `grep -q
'parse_arguments.py:214-229' docs/cli-and-configuration.md`; every long-form flag
name from README is present —
`for f in --fix --dry --exclude --ignore-names --quiet --count; do grep -q -- "$f"
docs/cli-and-configuration.md || echo "MISSING $f"; done` prints nothing;
`make check` passes.

---

## Phase 4: Visitor layer (Q3)

Documents the AST-traversal subsystem: parsing, the custom `visit()` dispatcher,
defined/used collectors, scopes, and noqa handling.

**Files**: `docs/visitor-layer.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/visitor-layer.md` covers `parse_abstract_syntax_tree`
  (`parse_abstract_syntax_tree.py:6-13`), `visit_abstract_syntax_trees`
  (`find_unused_code_visitor.py:98-153`), the `visit()` dispatcher with scope
  push/pop and ignore gates (`find_unused_code_visitor.py:506-587`), DEFINED
  collectors via `_define()` (`:274-328`), USED collectors via `add_used_name`
  (`:88-96`), `NestedScope` (`nested_scopes.py:6`), and noqa parsing +
  `NOQA_CODE_MAP` (`noqa.py:5-68`). Cross-links data-types for `CodeItem`/`Part`.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0; `grep -q
'find_unused_code_visitor.py:506-587' docs/visitor-layer.md` and `grep -q
'noqa.py' docs/visitor-layer.md`; `make check` passes.

---

## Phase 5: Unused-detection & ignoring (Q4) — includes the known gap

Documents how "unused" is decided and every ignore/exclude mechanism, and
explicitly records the partly-unimplemented decorator/inheritance ignore
options as an observed gap (design decision 4; verification criterion 4).

**Files**: `docs/unused-detection-and-ignoring.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/unused-detection-and-ignoring.md` covers `_get_unused_items`
  (`ignore.py:39-42`), the 8 `unused_*` properties + `get_unused_code_items`
  (`find_unused_code_visitor.py:155-200`), `ignore-names` /
  `ignore-names-in-files` (`:297-298`), `ignore-definitions[-if-inherits-from]`
  gate (`:519-528`), `ignore-bodies-if-inherits-from` (`:547-550`), built-in
  predicates + `_is_test_file` (`ignore.py:58-105`), and a clearly-labelled
  **Known gaps / inert options** section for the never-consulted
  `ignore_*_if_decorated_with` / `*_if_inherits_from` fields and the always-empty
  `self.ignore_decorators` (`find_unused_code_visitor.py:50,54`), framed as
  "currently inert / not consulted".

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0; `grep -q 'ignore.py:39-42'
docs/unused-detection-and-ignoring.md`; `grep -Eqi 'inert|not consulted|not
referenced' docs/unused-detection-and-ignoring.md` (gap documented, not omitted);
`make check` passes.

---

## Phase 6: Fix & output stage (Q5)

Documents `Part` merge/remove, diff rendering, and error-message formatting,
including the observed `does_include` copy-paste bug as fact.

**Files**: `docs/fix-and-output.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/fix-and-output.md` covers `fix_or_show_unused_code`
  (`fix_or_show_unused_code.py:15-63`), `merge_overlaping_file_parts`
  (`merge_overlaping_file_parts.py:99-105`) with the noted `does_include`
  copy-paste (`:11`), `remove_file_parts_from_content`
  (`remove_file_parts_from_content.py:127-390`),
  `get_unused_names_error_message` (`get_unused_names_error_message.py:7-30`),
  and `utils/` helpers `add_colors_to_diff` / `fix_indent`. Cross-links data-types
  for `Part`.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0; `grep -q
'merge_overlaping_file_parts.py:11' docs/fix-and-output.md` and `grep -q
'does_include' docs/fix-and-output.md` (observed bug recorded); `make check` passes.

---

## Phase 7: Testing & tooling (Q7)

Documents the `tests/` layout, `BaseTestCase`, and Make/Just commands.

**Files**: `docs/testing-and-tooling.md`, `docs/index.md` (confirm link)

**Key changes**:
- `docs/testing-and-tooling.md` covers the `tests/` groups + top-level test
  modules, `BaseTestCase` (`deadcode/utils/base_test_case.py:10-93`), the
  `Makefile` recipes (`test`/`lint`/`format`/`mypy`/`deadcode`/`audit`/`check`),
  the `Justfile` `lifecycle` recipe, and the relevant `pyproject.toml` config
  (entry point `:38`, pytest `addopts` `:209-210`, `[tool.deadcode]` self-config
  `:178-201`) — citing the file rather than copying numeric gates that drift.

**Verify**: `bash workspace/<id>/verify_docs.sh` exits 0 (full link set now
complete — all 7 topic files present, no dangling `index.md` link); `grep -q
'base_test_case.py' docs/testing-and-tooling.md`; `make check` passes.

---

## Testing Checkpoints

State that should hold after each phase (useful for resuming after a context
reset). `verify_docs.sh` re-runs every phase and is the standing gate.

- **After Phase 1**: `docs/index.md` + `docs/data-types.md` exist; `index.md`
  lists all seven planned topic links; `verify_docs.sh` passes for written files;
  Q6 answered. `make check` green.
- **After Phase 2**: `architecture.md` exists; five-stage flow + diagram +
  no-`sys.exit` callout present; Q1 answered.
- **After Phase 3**: `cli-and-configuration.md` exists; every README flag named;
  pyproject merge documented; Q2 answered.
- **After Phase 4**: `visitor-layer.md` exists; dispatcher, collectors, scopes,
  noqa documented; Q3 answered.
- **After Phase 5**: `unused-detection-and-ignoring.md` exists; decision logic +
  all ignore mechanisms + the inert-options gap documented; Q4 answered + design
  criterion 4 met.
- **After Phase 6**: `fix-and-output.md` exists; merge/remove/diff/error-message
  + `does_include` observation documented; Q5 answered.
- **After Phase 7**: `testing-and-tooling.md` exists; Q7 answered. Final state:
  all 8 doc files present, `index.md` link set complete with zero dangling links
  (verification criterion 1), all cited anchors resolve (criterion 2), Q1–Q7 each
  covered (criterion 3), gap documented (criterion 4), `make check` passes
  (criterion 5).

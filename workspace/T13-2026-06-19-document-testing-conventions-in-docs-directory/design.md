# Design Discussion

## Current State

A mature, accurate testing document **already exists**: `docs/testing-and-tooling.md`
(203 lines), and it is already linked from the docs hub at `docs/index.md:17`
(`[Testing & tooling](testing-and-tooling.md)`). It already covers the topics the
task names — suite layout, `BaseTestCase`, fixtures, determinism, and the
Make/Just/pyproject tooling (research.md:170-189).

The document is structurally complete but **factually drifted**: its `file:line`
references are systematically stale because the underlying files shifted since it
was written. Verified against the live source:

- `Makefile` recipes are off by ~2 lines. Doc says `check` at `Makefile:3`,
  `test` at `18-19`, `lint` at `21-22`, `format` at `37-38`, `mypy` at `27-28`,
  `deadcode` at `30-31`, `audit` at `40-41` (testing-and-tooling.md:114-121).
  Actual lines are `check`→5, `fix`→6, `test`→20-21, `lint`→23-24, `mypy`→29-30,
  `deadcode`→32-33, `format`→39-40, `audit`→42-43 (research.md:136-146, verified
  in `Makefile`).
- `BaseTestCase` spans are stale: doc cites `setUp` at `base_test_case.py:37-54`,
  `assertFiles` at `56-82`, `assertUpdatedFiles` at `84-93`
  (testing-and-tooling.md:40,56-57); research found `37-57`, `59-85`, `87-96`
  (research.md:43-53). The `patch()` helper at `base_test_case.py:15-18` (verified)
  is undocumented.
- `find_python_filenames` sorted walk cited at line 25
  (testing-and-tooling.md:73); research found line 24 (research.md:111-114).
- Pytest `addopts` cited at `pyproject.toml:209` (testing-and-tooling.md:140);
  research found `pyproject.toml:215` (research.md:157).

The document also contains two **awkward/unverifiable claims** that should not be
propagated: a filler note about the entry point ("the entry is on line 37; line 38
is the blank that follows", testing-and-tooling.md:139) and an aspirational
process claim ("Every ignore entry is tracked and validated: if a rule reaches
zero violations it is removed", testing-and-tooling.md:179) that the research did
not confirm.

A few **real conventions surfaced by research are missing** from the doc:
- Class-naming has two forms: dominant `Test<Name>` plus a minority `<Name>Tests`
  (research.md:21-25).
- Method names are uniformly `test_<behavior_in_snake_case>` (research.md:26-29).
- The suite is **entirely `unittest`-style classes**; no plain pytest functions,
  and **no `conftest.py` anywhere** (research.md:33-34).
- `__init__.py` exists only in `tests/cli_args/` and `tests/utils/`
  (research.md:30-32).
- `test_deadcode.py` is **mixed**: a `BaseTestCase` class plus two real-filesystem
  integration classes (research.md:75-77).
- Coverage omits `base_test_case.py` and the per-file ruff ignores for `tests/*`
  are `S101, PT009, ANN201, SLF001, D` (research.md:158-162) — doc lists four,
  omitting `SLF001`.

## Desired End State

`docs/testing-and-tooling.md` is the single authoritative testing reference, with
**every `file:line` reference matching the current source** and the missing
conventions above folded in. The doc remains indexed from `docs/index.md` (no new
file, no second index entry). Verification:

1. Every `file:line` citation in the doc resolves to the claimed symbol in the
   live tree (spot-check `Makefile`, `base_test_case.py`, `find_python_filenames.py`,
   `pyproject.toml`).
2. The doc names: the two class-naming forms, the `test_*` method convention, the
   `unittest`-only / no-`conftest.py` fact, and the `tests/*` ruff ignore set
   (all five entries).
3. The two unverifiable/filler claims (entry-point blank-line note; "every ignore
   tracked and validated") are removed or softened to what is verifiable.
4. `just check` / `make check` still pass (docs are not linted, but no code is
   touched — this is a no-regression sanity check).

## Patterns to Follow

- **Single authoritative doc, indexed once.** The hub pattern in `docs/index.md:9-17`
  gives each guide one bullet with a one-line summary; `testing-and-tooling.md:3`
  links back to `index.md`. Match it — do not add a second testing file.
- **Cite `file:line`; cite `pyproject.toml` for numeric gates instead of copying
  numbers.** Established at testing-and-tooling.md:112,140 and reinforced by
  research.md:188-189 and CLAUDE.md/Code-Best-Practices ("cite the file rather
  than copying numbers that drift"). This is exactly why the line refs drifted —
  so prefer symbol-anchored refs and avoid restating coverage/line-length numbers.
- **Document both runners as equivalent.** Both `Makefile` and `Justfile` run
  `pytest -n "$(nproc --ignore=1)"`; note where they diverge (Makefile adds
  `audit` + self-`deadcode`; Justfile adds `check-complexity`) — research.md:202-204.
- **Describe the two-tier (really three-tier) test strategy** already named in
  research.md:196-199: mock-backed unit tests via `BaseTestCase` (no disk),
  real-filesystem integration tests anchored to `REPO_ROOT`, and a hybrid that
  uses `BaseTestCase` + `tempfile.TemporaryDirectory()` to exercise real `os.walk`.

**Patterns to NOT follow** (present in the current doc):
- Hand-counted exact line spans that drift (e.g. `setUp` `37-54`). Prefer the
  symbol name + a single anchor line, or a tight range verified at write time.
- Filler meta-notes about blank lines (testing-and-tooling.md:139).
- Unverifiable process claims stated as fact (testing-and-tooling.md:179).

## Design Decisions

1. **Revise in place, do not create a new file** — The task asks for "a single,
   authoritative reference"; `docs/testing-and-tooling.md` already is that and is
   already indexed. A second doc would duplicate content and violate "single
   authoritative reference" plus CLAUDE.md §3 (surgical changes). *Assumption:*
   "document … in the `docs/` directory" is satisfied by updating the existing
   doc, not by adding a parallel `testing-conventions.md`.
2. **Correct all stale `file:line` refs against live source** — The doc's value is
   as a navigable reference; broken anchors defeat it. Use research.md's verified
   numbers as the source of truth (already cross-checked against `Makefile` and
   `base_test_case.py`).
3. **Add the missing conventions, keep additions small** — Fold in class-naming
   variants, `test_*` methods, `unittest`-only/no-`conftest.py`, `__init__.py`
   placement, mixed `test_deadcode.py`, and the full `tests/*` ignore set. These
   are factual gaps, not new structure. *Assumption:* "structured, named, mocked,
   and run" maps to layout + naming + `BaseTestCase` + commands — all already
   sectioned in the doc.
4. **Remove/soften unverifiable claims** rather than research them further —
   Keeping prose to what research verified avoids re-introducing drift.
5. **No index changes beyond the existing entry** — `docs/index.md:17` already
   links the doc with an accurate one-line summary; leave it.
6. **Keep numeric gates as `pyproject.toml` citations** — Do not inline
   line-length, coverage %, or complexity numbers; cite the file (the drift
   lesson plus the project's own convention).

## What We're NOT Doing

- Not creating a new `docs/testing-conventions.md` or any new doc file.
- Not adding a second `docs/index.md` entry or restructuring the index.
- Not changing any test code, `BaseTestCase`, `Makefile`, `Justfile`, or
  `pyproject.toml` — docs only.
- Not auditing or "improving" the other 7 docs in `docs/` (CLAUDE.md §3).
- Not introducing new testing conventions or recommending changes to how tests
  are written — documenting current reality only (research.md:211-212).
- Not exhaustively re-deriving every line span in the suite; correcting the cited
  anchors and the few flagged gaps is sufficient.

## Open Risks

- **Remaining line-ref drift.** Research flagged that some spans were sampled, not
  exhaustively re-read (research.md:206-209). The two temp-dir test modules'
  `setUp` spans in particular should be re-confirmed at write time before citing.
- **Coverage-vs-completeness of "conventions."** "Testing conventions" is broad;
  judgment was applied (Decision 3) to scope it to layout/naming/mocking/running.
  If a reviewer expects e.g. CI-workflow or release-test documentation, that is
  out of scope here and would need a follow-up.
- **Line numbers will drift again.** The root cause is hand-counted refs; mitigated
  by preferring symbol anchors over exact spans, but not eliminated.

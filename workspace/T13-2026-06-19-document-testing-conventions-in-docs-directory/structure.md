# Structure Outline

## Approach

Revise the single existing doc `docs/testing-and-tooling.md` in place (per design
Decision 1): correct every stale `file:line` reference against live source, fold
in the missing conventions, and remove the two unverifiable claims. No new file,
no index change, no code touched.

**Note on slicing.** This is a docs-only task — there is no DB/service/API/UI
stack to cross. "Vertical slice" is therefore mapped onto the doc's own section
boundaries: each phase fully corrects one section (stale anchors **+** missing
facts **+** removed filler for that section) and is independently verifiable by a
scripted check that compares the doc's claims to the live tree. A later phase
failing leaves earlier section corrections valid and valuable. All phases edit the
same file: `docs/testing-and-tooling.md`. Commands below run from repo root
`/home/niekas/tools/deadcode`.

---

## Phase 1: Test Suite Organization + naming conventions

Correct the "Test Suite Organization" section and add the four missing
structural/naming facts: the two class-naming forms (`Test<Name>` dominant,
`<Name>Tests` minority), the `test_<snake_case>` method convention, the
`unittest`-only / no-`conftest.py` fact, the `__init__.py`-only-in-`cli_args`/`utils`
fact, and that `test_deadcode.py` is mixed (mock class + real-FS integration).

**Files**: `docs/testing-and-tooling.md`
**Key changes**:
- New prose under "Test Suite Organization": class/method naming forms; "all
  `unittest`-style classes, no plain pytest functions, no `conftest.py`".
- Note `__init__.py` placement and the mixed nature of `test_deadcode.py`.

**Verify**:
- `rg -n 'CommandLineArgParsingTests|<Name>Tests|test_<' docs/testing-and-tooling.md` — both naming forms + method convention present.
- `rg -n 'conftest|unittest-style|no plain pytest' docs/testing-and-tooling.md` — runner-style fact present.
- Ground-truth source: `test -z "$(find tests -name conftest.py)"` (no conftest) and `find tests -name __init__.py` lists only `tests/cli_args/`, `tests/utils/` (+ the `files/subdir/.../__init__.py` fixture).

---

## Phase 2: BaseTestCase section — fix spans, document `patch()`

Re-confirm and correct the `BaseTestCase` anchors and document the undocumented
`patch()` helper. Update the three-tier strategy framing (mock unit / real-FS
integration / `BaseTestCase`+tempdir hybrid).

**Files**: `docs/testing-and-tooling.md`
**Key changes**:
- `base_test_case.py:10` (class), `setUp` → `37-57`, `assertFiles(files, removed=None)` → `59-85`, `assertUpdatedFiles(expected)` → `87-96`, `_read_file_side_effect` → `23-35`.
- New bullet for `patch(path)` helper (`base_test_case.py:15-18`) — auto-registers cleanup.

**Verify** (each cited span resolves to the claimed symbol):
- `sed -n '15,18p' deadcode/utils/base_test_case.py` shows `def patch`; `sed -n '10p' …`, `sed -n '37,57p' …` (setUp), `sed -n '59,85p' …` (assertFiles), `sed -n '87,96p' …` (assertUpdatedFiles).
- `rg -n 'base_test_case.py:(10|15-18|23-35|37-57|59-85|87-96)' docs/testing-and-tooling.md` — doc cites exactly these.
- `! rg -n '37-54|56-82|84-93|10-93' docs/testing-and-tooling.md` — no stale spans remain.

---

## Phase 3: Deterministic Testing — sorted-walk anchor

Correct the single stale ref in "Directory Walk Determinism".

**Files**: `docs/testing-and-tooling.md`
**Key changes**:
- `find_python_filenames.py:25` → `:24` (the `sorted(...)` glob line).

**Verify**:
- `sed -n '24p' deadcode/actions/find_python_filenames.py` contains `sorted(` glob.
- `rg -n 'find_python_filenames.py:24' docs/testing-and-tooling.md` present; `! rg -n 'find_python_filenames.py:25' docs/testing-and-tooling.md`.

---

## Phase 4: Build and Check Commands — Makefile/Justfile anchors

Correct all stale `Makefile` line refs and confirm the Make/Just equivalence +
divergence note (Makefile adds `audit` + self-`deadcode`; Justfile adds
`check-complexity`).

**Files**: `docs/testing-and-tooling.md`
**Key changes**:
- `check`→`Makefile:5`, `fix`→`6`, `test`→`20-21`, `lint`→`23-24`, `mypy`→`29-30`, `deadcode`→`32-33`, `format`→`39-40`, `audit`→`42-43`.
- Keep both-runners-equivalent prose; cite `Justfile:34` for `check`, `Justfile:10-11` for `test`.

**Verify**:
- `sed -n '5p;6p;20,21p;23,24p;29,30p;32,33p;39,40p;42,43p' Makefile` — each line matches its claimed recipe.
- `rg -n 'Makefile:(5|6|20-21|23-24|29-30|32-33|39-40|42-43)' docs/testing-and-tooling.md` present; `! rg -n 'Makefile:(3|4|18-19|21-22|27-28|30-31|37-38|40-41)' docs/testing-and-tooling.md`.

---

## Phase 5: Configuration Files — fix anchor, drop filler, complete ignore set

Correct the pyproject anchor, remove the two unverifiable/filler claims, and
complete the `tests/*` ruff ignore set to all five entries.

**Files**: `docs/testing-and-tooling.md`
**Key changes**:
- Pytest `addopts` `pyproject.toml:209` → `:215`.
- Remove entry-point blank-line filler ("the entry is on line 37; line 38 is the blank that follows").
- Remove/soften "Every ignore entry is tracked and validated…" claim (research did not confirm).
- `tests/*` ignore list: add `SLF001` → full set `S101, PT009, ANN201, SLF001, D`.

**Verify**:
- `sed -n '215p' pyproject.toml` shows `addopts`; `sed -n '153,162p' pyproject.toml` lists the five `tests/*` ignores including `SLF001`.
- `rg -n 'pyproject.toml:215|SLF001' docs/testing-and-tooling.md` present.
- `! rg -n 'entry is on line 37|tracked and validated|pyproject.toml:209' docs/testing-and-tooling.md` — filler/stale gone.

---

## Phase 6: Full-reference audit + no-regression gate

Sweep every remaining `file:line` citation in the doc and confirm the no-code-change
invariant.

**Files**: `docs/testing-and-tooling.md` (read-only audit)
**Key changes**: none beyond fixes surfaced by the sweep.

**Verify**:
- Extract refs and spot-check: `rg -no '[A-Za-z_./]+\.(py|toml):[0-9-]+' docs/testing-and-tooling.md` — each resolves to the claimed symbol via `sed -n`.
- `git -C /home/niekas/tools/deadcode diff --name-only` lists only `docs/testing-and-tooling.md`.
- `make check` (or `just check`) passes — no code touched, no regression.

---

## Testing Checkpoints

After each phase the following should hold (useful for resuming mid-task):

1. **Phase 1**: doc states both class-naming forms, the `test_*` method rule, the
   `unittest`-only/no-`conftest.py` fact, `__init__.py` placement, and mixed
   `test_deadcode.py`. `find`/`rg` checks above pass.
2. **Phase 2**: every `base_test_case.py` anchor resolves to its symbol; `patch()`
   documented; no stale spans (`37-54`, `56-82`, `84-93`, `10-93`) remain.
3. **Phase 3**: sorted-walk cite reads `find_python_filenames.py:24`.
4. **Phase 4**: all eight `Makefile` recipe anchors correct; no old anchors remain;
   Make/Just divergence noted.
5. **Phase 5**: `addopts` cite is `:215`; both filler claims gone; `tests/*` ignore
   set lists all five entries incl. `SLF001`.
6. **Phase 6**: every `file:line` in the doc resolves; `git diff` touches only the
   one doc file; `make check` / `just check` green.

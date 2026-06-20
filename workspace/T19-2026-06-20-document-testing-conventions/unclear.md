# Needs clarification before this task can proceed

## Why this is blocked

T19 ("Document testing conventions.") appears to be already satisfied by
previously completed work. Testing conventions are currently documented in:

- **`docs/testing-and-tooling.md`** — a thorough document covering:
  - test suite organization (`tests/` directories by area, top-level modules)
  - naming/style conventions (module/class/method naming, unittest style, no `conftest.py`)
  - the `BaseTestCase` mock helper (setUp patching, file mocking, `assertFiles` / `assertUpdatedFiles`)
  - testing new syntax features and Python 3.12+ version-gating with `skipUnless`
  - deterministic testing (walk ordering, config mocking, FS-bypass temp dirs, repo-root anchoring)
  - build/check tooling (`Makefile`, `Justfile`, `pyproject.toml`)
  This was delivered by the already-completed task **T13** ("Document testing
  conventions in docs directory") — see `BACKLOG.md`.

- **`README.md`** — a "Test Determinism" and "Test Coverage" section that
  summarizes the conventions and links to `docs/testing-and-tooling.md`.

There is no `CONTRIBUTING.md`.

Because T19's wording is essentially a duplicate of the completed T13, and it
specifies no location, no audience, and no acceptance criteria, it is not
possible to derive neutral research questions or an implementation plan without
a human deciding what (if anything) is still missing.

## What a human needs to decide

Please clarify one of the following (or describe the intended outcome):

1. **Is T19 a duplicate of T13?** If so, it can be closed as already done.
2. **Different artifact/location** — e.g. a contributor-facing
   `CONTRIBUTING.md`, or an expanded README testing section, distinct from the
   existing architecture-style `docs/testing-and-tooling.md`.
3. **Sync/update** — the existing docs should be refreshed to reflect testing
   conventions introduced by later tasks (e.g. T14–T18 added correctness tests
   and framework tests under `tests/frameworks/`). If so, name the specific
   gaps to document.
4. **Consolidation** — merge/deduplicate the testing material currently split
   between `README.md` and `docs/testing-and-tooling.md`.

Once decided, change `- [?] [T19] ...` back to `- [ ]` in `BACKLOG.md` (with a
clarified description) so this task can run again.

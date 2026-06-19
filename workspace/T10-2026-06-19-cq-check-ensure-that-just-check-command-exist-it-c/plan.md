# Plan

## Phase 1: Verify and (if needed) wire up `just check`

### Current state

The `Justfile` already defines a `check` target that aggregates every
quality check:

```
check: check-format check-lint check-complexity check-typecheck test
```

with the individual recipes:

- `check-format`  -> `ruff format --check deadcode/ tests/`
- `check-lint`    -> `ruff check deadcode/ tests/`
- `check-complexity` -> `ruff check --select C901 deadcode/ tests/`
- `check-typecheck`  -> `mypy deadcode/`
- `test`          -> `pytest -n <nproc-1>`

Running `just check` currently exits `0` (all checks and 176 tests pass; 18
skipped). The acceptance criteria are therefore already met.

### Steps

1. Confirm the `check` recipe exists in the `Justfile` and lists every
   quality recipe as a dependency.
   - verify: the `check:` line names `check-format`, `check-lint`,
     `check-complexity`, `check-typecheck`, and `test`.
2. Run the combined gate.
   - verify: `just check` exits with code `0`.
3. If any sub-check were failing, fix the underlying code (formatting, lint,
   complexity, type, or test failure) until the gate is green. No fixes are
   needed at present.
   - verify: `just check` exits `0` again after any change.

### Notes

- No changes to the `Justfile` are required; the recipe already exists and
  passes. This task is primarily a verification task. Only modify code/config
  if a future run of `just check` regresses.

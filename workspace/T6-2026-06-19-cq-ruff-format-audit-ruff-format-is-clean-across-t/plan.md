# Plan

## Phase 1: Audit `ruff format` cleanliness

**Goal:** Confirm `ruff format` reports no changes across `deadcode/` and `tests/`.

### Steps

1. Run the existing Justfile recipe:
   ```
   just check-format
   ```
   This runs `uv run ruff format --check deadcode/ tests/`.

2. Inspect the result:
   - **If it exits 0** (e.g. "N files already formatted"), the audit passes —
     nothing to change. Done.
   - **If it lists files that would be reformatted**, run `just format`
     (`uv run ruff format deadcode/ tests/`) to apply the canonical formatting,
     then re-run `just check-format` to confirm it now exits clean.

### Verify

- `just check-format` exits 0 with all files reported as already formatted.

### Notes

- Current state (2026-06-19): `just check-format` already exits 0 — "77 files
  already formatted". No formatting changes are needed; this audit is a no-op
  confirmation unless future edits introduce unformatted files.
- The `ANN101` "removed rule" warning emitted during the run is a lint-config
  concern (`pyproject.toml`), not a `ruff format` issue, and is out of scope
  for this task.

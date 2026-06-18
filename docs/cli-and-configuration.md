# CLI & Configuration

This document describes argument parsing, configuration file handling, and the resulting `Args` object that flows through the pipeline. See [Data Types](data-types.md) for the `Args` type definition and [Architecture](architecture.md) for the pipeline context. See [index.md](index.md) for the full guide.

## Argument Parsing Basics

`parse_arguments(args: Optional[List[str]]) -> Args` (`parse_arguments.py:15-211`) constructs an `argparse.ArgumentParser`, adds all CLI flags, parses the provided arguments (or `sys.argv[1:]` if `args` is `None`; `parse_arguments.py:24-25`), flattens list values, merges `pyproject.toml` config, and returns an `Args` object.

## CLI Flags and Argument Types

### Positional Arguments

- **`paths`** (`nargs='+'`) — required list of directories or files to search for Python code

### Boolean Flags (store_true, default False)

- `--fix` — automatically remove detected unused code from files
- `--no-color` — disable ANSI color codes in output
- `--quiet` — suppress all output (tool still exits with non-zero code if unused items found)
- `--count` — output only the count of unused items, not the list
- `-v, --verbose` — emit debug logs

### List Flags (nargs='*', action='append', default [])

All other options accept zero or more values, can be repeated, and are internally flattened:

**Ignore mechanisms** (apply to definitions and usages):
- `--ignore-names` — ignore items whose name matches a glob pattern
- `--ignore-names-in-files` — ignore all definitions in files matching a path pattern
- `--ignore-names-if-inherits-from` — ignore class names that inherit from specified base classes
- `--ignore-names-if-decorated-with` — ignore names decorated with specified decorators
- `--ignore-bodies-of` — ignore the body (not the name) of items matching a name pattern
- `--ignore-bodies-if-decorated-with` — ignore bodies of decorated items
- `--ignore-bodies-if-inherits-from` — ignore class bodies inheriting from specified bases
- `--ignore-definitions` — ignore entire definitions (name + body) matching a name pattern
- `--ignore-definitions-if-inherits-from` — ignore full definitions of classes inheriting from specified bases
- `--ignore-definitions-if-decorated-with` — ignore full definitions of decorated items
- `--ignore-if-decorated-with` — ignore both name and body if decorated
- `--ignore-if-inherits-from` — ignore both name and body if class inherits from specified base

**Other list options**:
- `--dry` — show a diff of what would be changed (can optionally take filenames to limit scope)
- `--exclude` — glob patterns for paths to skip entirely

### Special Handling: `--dry` Sentinel

The `--dry` flag defaults to `[['__all_files__']]` (`parse_arguments.py:41`). This sentinel value signals "show all changes" when `--dry` is passed without filenames. Post-processing (`parse_arguments.py:204-205`) removes the sentinel if explicit filenames are given. If `dry` is non-empty, `fix` is forced to `False` (`parse_arguments.py:208-209`).

## Configuration Merging

`parse_pyproject_toml() -> Dict[str, Any]` (`parse_arguments.py:214-229`) reads `[tool.deadcode]` from `pyproject.toml` in the current working directory. Keys are normalized (strip `--`, replace `-` with `_`) to match `Args` field names.

In `parse_arguments`, after CLI parsing, each key from `pyproject.toml` that exists in `Args` is `.extend()`ed onto the corresponding CLI list (`parse_arguments.py:199-201`). This means CLI values take precedence—config values are appended to CLI-provided lists, not vice versa. Boolean flags from the config file are **not** merged (e.g., config cannot override a CLI `--fix` or `--no-color`).

### List Flattening

`flatten_lists_of_comma_separated_values(value: Iterable)` (`utils/flatten_lists.py:6-12`) is applied to every list field except `paths` after CLI parsing (`parse_arguments.py:194-196`). It flattens nested lists (from repeated `action='append'` calls) and splits comma-separated tokens into a single flat `List[str]`.

Example: `deadcode . --ignore-names "A,B" --ignore-names "C"` becomes `Args(ignore_names=['A', 'B', 'C'])`.

## Noted Configuration Gaps

The README mentions CLI options `--depth` and `--only` (`README.md`), but these are **not** implemented in the parser or `Args` dataclass (`data_types.py:13-34`). They parse without error (unknown arguments are ignored) but have no effect on analysis. This is an observed limitation, not a recommendation for change.

## Example Workflow

```bash
# Show unused code
deadcode .

# Dry-run of a fix
deadcode . --dry

# Apply fixes and show diff
deadcode . --fix --dry

# Apply fixes silently to specified files
deadcode foo.py bar.py --fix

# Apply fixes with exclusions and name ignoring
deadcode . --fix --exclude venv,tests --ignore-names "*Mixin,BaseTestCase"

# Using config from pyproject.toml
# In pyproject.toml:
# [tool.deadcode]
# exclude = ["venv", "tests"]
# ignore-names = ["*Mixin"]
# Then: deadcode . --fix
```

See [README](../README.md) for the full CLI reference and user-facing examples.

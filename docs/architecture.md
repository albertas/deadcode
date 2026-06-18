# Architecture & Pipeline Flow

This document describes the five-stage pipeline that forms the core of Deadcode, from CLI invocation through final output. See [Data Types](data-types.md) for the structures used throughout. See [index.md](index.md) for the full guide.

## The Five-Stage Pipeline

The main entry point `main` (`cli.py:12-31`) orchestrates five sequential stages:

```
  1. parse_arguments()         → Args
        ↓
  2. find_python_filenames()   → List[str]
        ↓
  3. find_unused_names()       → (CodeItems, Parts dict)
        ↓
  4. fix_or_show_unused_code() [conditional] → diff str
        ↓
  5. get_unused_names_error_message() + print → None or error string
```

### Stage 1: Argument Parsing

`parse_arguments(command_line_args: Optional[List[str]]) -> Args` (`cli.py:15`, `parse_arguments.py:15`)

Parses CLI flags and merges `pyproject.toml` configuration to produce a single `Args` object. Details in [CLI & configuration](cli-and-configuration.md).

### Stage 2: File Discovery

`find_python_filenames(args: Args) -> List[str]` (`cli.py:17`, `find_python_filenames.py:11`)

Searches the filesystem for Python files matching `args.paths` and respecting `args.exclude` patterns. Returns a flat list of file paths for analysis.

### Stage 3: AST Analysis (Two-Pass)

`find_unused_names(filenames: List[str], args: Args) -> Tuple[Iterable[CodeItem], dict[Filename, List[Part]]]` (`cli.py:20`, `find_unused_names.py:9-24`)

The most complex stage, running two passes over all files (`find_unused_names.py:9-24`):

1. **First pass: `FindUnusedCodeVisitor`** — traverses the AST of each file, collecting all defined names (variables, functions, classes, imports) and all uses of those names, annotating with scope, type, and location. Applies ignore rules to filter out items.
2. **Second pass: `FixUnusedCodeVisitor`** — uses the first pass's results to identify additional code fragments to remove (e.g., comments, unreachable code), yielding `additional_code_parts_to_remove`.

Returns a tuple of unused `CodeItem`s and a dict mapping each filename to its list of `Part`s to remove.

### Stage 4: Optional Diff/Fix Generation

Conditional on `(args.fix or args.dry) and unused_names` (`cli.py:23-24`):

`fix_or_show_unused_code(unused_names: Iterable[CodeItem], additional_code_parts_to_remove: dict, args: Args) -> str` (`cli.py:24`, `fix_or_show_unused_code.py:15`)

Merges all `Part`s for each file, applies removals (and optional insertions), and either prints a unified diff (if `args.dry`) or modifies files in-place (if `args.fix`). Returns a diff string or empty string. Details in [Fix & output](fix-and-output.md).

### Stage 5: Error Message & Exit

`get_unused_names_error_message(unused_names: Iterable[CodeItem], args: Args) -> Optional[str]` (`cli.py:26`, `get_unused_names_error_message.py:7`)

Formats unused items into a human-readable report or returns `None` if no items. Details in [Fix & output](fix-and-output.md).

## Return Value and Exit Logic

`main` returns `Optional[str]`:

- If `error_message is not None`: returns the message, optionally appending the diff (`+ '\n\n' + file_diff`).
- Otherwise: prints the `Well done! ✨ 🚀 ✨` banner (unless `--count` or `--quiet` is set) and returns `None`.

**Key implicit exit behavior** (`cli.py:34-35`): `main()` does **not** call `sys.exit()`. The `if __name__ == '__main__'` guard just calls `main()` and returns. The actual exit code and printing is handled by the console-script wrapper (configured in `pyproject.toml:38` as `deadcode = "deadcode.cli:main"`). This is a common contributor surprise—the return value becomes the process's exit code and stdout message.

## Visitor Layer Architecture

Stage 3's visitors are detailed in [Visitor layer](visitor-layer.md), but the high-level design is:

- **`FindUnusedCodeVisitor`**: Walks every file's AST, dispatching to specialized `visit_*` methods for each node type, maintaining scope state, and calling `_define()` for definitions and `add_used_name()` for uses.
- **`FixUnusedCodeVisitor`**: Secondary pass over the same visitor to identify additional removal regions.

Both are orchestrated by `find_unused_names` in the `deadcode/actions/` pipeline.

## Module Organization

The codebase is factored into three main subsystems:

- **`deadcode/actions/`** — the five-stage pipeline steps (parsing, discovery, analysis, fix, output formatting)
- **`deadcode/visitor/`** — AST traversal, scope tracking, and ignore logic
- **`deadcode/utils/`** — helper functions (formatting, indentation, color output)

Additionally:
- **`deadcode/cli.py`** — the main entry point
- **`deadcode/data_types.py`** — shared type definitions (`Args`, `Part`)
- **`deadcode/constants.py`** — error codes and type mappings

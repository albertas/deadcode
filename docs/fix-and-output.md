# Fix & Output

This document describes how unused code is removed or displayed, and how error messages are formatted. See [Data Types](data-types.md) for `Part` and `CodeItem` types, and [Architecture](architecture.md) for the pipeline context. See [index.md](index.md) for the full guide.

## The Fix / Diff Generation Stage

`fix_or_show_unused_code(unused_items: Iterable[CodeItem], additional_code_parts_to_remove: dict, args: Args) -> str` (`actions/fix_or_show_unused_code.py:15-63`)

This stage processes all unused items and generates either a diff (if `args.dry`) or modifies files in-place (if `args.fix`):

1. **Group by filename** (`:26-28`) — collect all unused `CodeItem`s for each file
2. **Flatten and merge `Part`s** (`:32-37`) — for each file, extract `code_parts` from all unused items, add any `additional_code_parts_to_remove` from the second visitor pass, and call `merge_overlaping_file_parts`
3. **Read file content** (`:39-40`) — load the file as a list of lines
4. **Remove fragments** (`:42`) — call `remove_file_parts_from_content` to excise or replace the parts
5. **Output decision** (`:44-63`):
   - If the updated content is non-empty:
     - If `args.dry` and the filename matches `args.dry` patterns: generate a colored `unified_diff` (`:45-56`)
     - Else if `args.fix`: write the updated content back to the file (`:58-61`)
   - If the updated content is empty (entire file removed): delete the file (`:63`)

Returns a concatenated diff string (colored unless `--no-color`) or empty string if no changes.

## Part Merging

`merge_overlaping_file_parts(parts: List[Part]) -> List[Part]` (`actions/merge_overlaping_file_parts.py:99-127`)

Merges overlapping code removal regions:

1. Sorts parts by `(line_start, col_start, -line_end, -col_end)` — earlier parts first, larger parts prioritized within a start position
2. Iterates through sorted parts, checking against the accumulator of non-overlapping parts:
   - If a new part is completely inside an existing part (`does_include`): skip it (already covered)
   - Else if a new part overlaps with an existing part (`does_overlap`): merge them (`merge_parts`) and replace the existing part in the accumulator
   - Else: append the new part as non-overlapping

Returns a list of non-overlapping `Part`s ready for removal.

**Observed bug**: The `does_include` function (`merge_overlaping_file_parts.py:5-15`) has a copy-paste error at `merge_overlaping_file_parts.py:11`: `(line_end_b == line_end_b)` should be `(line_end_b == line_end_s)`. This checks whether the bigger part's end line equals itself (always true) rather than comparing it to the smaller part's end. Despite this, the function still works in practice because the overlap check is correct, but the logic is incorrect.

## Fragment Removal and Insertion

`remove_file_parts_from_content(file_content_lines: List[str], parts: List[Part]) -> List[str]` (`actions/remove_file_parts_from_content.py:127-390`)

Applies removal and insertion operations:

1. Maintains a cursor over sorted `Part`s
2. For each part:
   - **Single-line parts**: uses `remove_unused_fragments_from_a_line` to slice out columns via string slicing (`:184`)
   - **Multi-line parts**: removes lines between start and end, truncates columns on boundary lines
   - **Insert code**: appends `insert_code` if specified
   - **Placeholder insertion**: if removing a function/class body leaves an empty block, inserts `pass` to maintain valid Python syntax (`:354-361`)
3. Handles end-of-file edge cases (`:388-390`)

Returns the modified file content as a list of lines.

## Error Message Formatting

`get_unused_names_error_message(unused_names: Iterable[CodeItem], args: Args) -> Optional[str]` (`get_unused_names_error_message.py:7-30`)

Formats unused items for output:

- Returns `None` if no unused items (no error)
- Returns empty string `''` if `--quiet` (suppress output but exit with error code)
- Returns count string if `--count` (e.g., `"42"`)
- Otherwise, for each item, formats a line: `{filename}:{line}:{column}: {error_code} {message}` with ANSI color codes:
  - Error code in red: `\033[91m...\033[0m`
  - Item name in bold: `\033[1m...\033[0m`
  - Default message: `"{Type} `{name}` is never used"` (type capitalized, underscores replaced with spaces)
- If `--fix` was applied, appends a line: `"Removed N unused code item(s)!"` (bold)
- Strips ANSI codes if `--no-color` (`:26, :31-32`)

## Diff Rendering

`unified_diff` from Python's `difflib` generates the standard unified diff format (lines starting with `-`, `+`, or `@@`). If `args.no_color` is not set, `add_colors_to_diff` (`utils/add_colors_to_diff.py:1`) wraps removal lines in red ANSI codes and addition lines in green.

## Putting It Together

When `--dry` is set without `--fix`, the stage generates a colored diff showing all proposed changes without modifying files. When `--fix` is set without `--dry`, changes are applied silently. When both are set, changes are applied and a diff is displayed. When neither is set, no `fix_or_show_unused_code` is called (pipeline stage 4 is skipped).

The error message (stage 5) is always generated if there are unused items, regardless of the fix/dry settings—it becomes the return value or stdout depending on the console wrapper.

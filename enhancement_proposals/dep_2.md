# DEP 2 - Fixing code after removal of unused code fragments

**Status**: Proposed

**Type**: Feature

**Created**: 2024-04-16

## Problem statement

Sometimes code becomes invalid after removal of a part of it. `deadcode --fix` removes the code fragments it reports as unused, and removing a
fragment can leave the remaining code no longer parseable. Three scenarios occur.

### Incomplete imports

When an unused name is removed from an import statement whose only remaining name it is, a naive removal could leave an import statement with an
empty name list. For example, when the unused name `bar` is removed from:

```python
from foo import (bar)
```

the resulting import clause would no longer be valid:

```python
from foo import ()
```

An import clause with no names is not valid Python, so the whole import statement has to be removed together with the last of its names.

### Empty code blocks

When all expressions are removed from an indented block, the block body becomes empty, which is invalid Python. For example, removing the
`unused = None` statement from this file:

```python
class Foo:
    unused = None

print(Foo())
```

would leave an invalid empty class body:

```python
class Foo:

print(Foo())
```

### Blank lines around removed definitions

When a method in the middle of a class is removed, the blank lines before and after it have to be reconciled, so that exactly one blank line
remains between the remaining methods and the usual two blank lines separate the class from the code that follows it. When the last method of a
class is removed, the blank lines between the class body and the following code have to be reduced the same way.

### How deadcode works today

`deadcode --fix` applies targeted cleanups while it removes code. Findings are grouped per file in `deadcode/actions/fix_or_show_unused_code.py`,
and import findings are split from the rest. Import removal parts are computed by `deadcode/actions/get_unused_import_parts.py`, which re-parses
the file with `ast.parse` and falls back to the raw reported parts when the file no longer parses; when every non-wildcard alias of a statement is
unused, the whole statement becomes one removable part, otherwise each unused alias is returned together with one adjacent comma, so the remaining
aliases keep valid comma placement. Overlapping parts are merged by `deadcode/actions/merge_overlaping_file_parts.py`, and the removal plus its
targeted cleanups happen in `deadcode/actions/remove_file_parts_from_content.py`: dangling `as` keywords, leading commas, and trailing commas are
cleaned up, a `pass` statement is inserted when a removal empties an indented block whose previous line ends with a colon, and blank lines are
kept valid by empty-line bookkeeping. The test suite asserts that every file updated by `--fix` still parses via `assert_valid_python`
(`tests/conftest.py`).

## Considered alternatives

### Modify AST nodes and render them back as valid code

- Idea: keep whole AST nodes and use them when removing code — update a partially unused node, render it back as source code, and diff the
  rendered result against the original source to find the parts to remove. A node modified this way renders to valid code, which a demonstration
  script in the original proposal showed.
- Trade-off: the rendered node is valid by construction, but the design needs node-anchored machinery the codebase does not have (for example
  per-node before/after hooks that update child nodes), and it specifies no representation for the diff between the original and the modified
  node that the existing line-and-column `Part` ranges could use.
- Why not chosen: it was prototyped in commit `5fdd707` but never implemented; the shipped approach reaches valid output incrementally, without
  retaining and re-rendering AST nodes.

### Memorise initial expression positions and re-validate from them

- Idea: memorise the source positions of expressions during the initial AST parse, then after a removal re-parse the memorised ranges and check
  their validity.
- Trade-off: it keeps a second source of truth about source positions, which duplicates what a fresh parse of the file already provides.
- Why not chosen: re-parsing the file detects exactly the same breakage without any memorised positions, so the extra bookkeeping buys nothing.

### Detect and validate surrounding expressions during removal

- Idea: remember nothing extra; when a part is removed, detect the surrounding expression context and validate the result as part of the removal
  step itself.
- Trade-off: it couples the cleanup to the removal, but it needs no retained AST nodes and no memorised positions, and the removal step already
  knows the shape of what it just deleted.
- Why not chosen: this is the chosen direction; it is described in the next section.

### Do nothing and keep manual fixes

- Idea: report the unused fragments and leave it to the user to repair any invalid result of a removal.
- Trade-off: no implementation cost, but `--fix` output would sometimes not be valid Python, contradicting the tool's contract that a fixed file
  can be written back and parsed.
- Why not chosen: the tool asserts that every `--fix` output parses (`assert_valid_python`, `tests/conftest.py`), so leaving invalid output in
  place is not acceptable.

## Chosen solution

Validated removal. The rejected alternatives are modifying AST nodes and rendering them back (prototyped in `5fdd707`, never implemented, and
needing machinery the codebase lacks), memorising initial expression positions for re-validation (duplicates what a fresh parse gives and keeps a
second source of truth), and doing nothing (leaves `--fix` output invalid, contradicting the tool's contract). The chosen approach was selected
because it produces valid output incrementally: every cleanup runs while the part is being removed, using only the local context of the removal,
so no retained AST nodes, no second source of position truth, and no manual repair steps are needed.

The approach works as follows:

1. Unused code parts are located with the text/AST hybrid described in the problem statement: import parts come from
   `deadcode/actions/get_unused_import_parts.py`, which re-parses the file with `ast.parse` and falls back to the raw parts on `SyntaxError`.
2. Every part is a character range `Part(line_start, line_end, col_start, col_end)` (`deadcode/data_types.py`), and overlapping ranges are merged
   by `deadcode/actions/merge_overlaping_file_parts.py` before removal.
3. `deadcode/actions/remove_file_parts_from_content.py` removes the ranges and applies the targeted cleanups during the same removal step: a
   whole import statement whose last alias is removed goes away entirely, so the invalid clause `from foo import ()` is never produced; a `pass`
   statement is inserted when a removal empties an indented block; dangling `as` keywords, leading commas, and trailing commas are cleaned up;
   and blank lines are reconciled around the removal.

Applied to the examples from the problem statement, `--fix` produces the following verified output.

The import statement is removed entirely, and only the kept code remains:

```python
print(1)
```

The emptied class body gains a `pass` statement:

```python
class Foo:
    pass

print(Foo())
```

Removing the middle method `spam()` keeps exactly one blank line between the remaining methods and two blank lines before the following code:

```python
class Foo:
    def bar(self):
        pass

    def eggs(self):
        pass


foo = Foo()
print(foo.bar())
print(foo.eggs())
```

Removing the last method `eggs()` leaves one blank line between the class body and the following code, not both of the blank lines that were
originally after the class:

```python
class Foo:
    def bar(self):
        pass

    def spam(self):
        pass

foo = Foo()
print(foo.bar())
print(foo.spam())
```

## Scope

In scope: the removal-time cleanups described above — whole-statement and per-alias import removal, `pass` insertion into emptied blocks, comma
and `as` cleanup, and blank-line reconciliation around removals.

Out of scope: handling context-manager (`with`) blocks after removal. No context-manager-specific adjustment exists today, and this DEP does not
specify one.

## Implementation notes

The pipeline lives in `deadcode/actions/`: orchestration in `fix_or_show_unused_code.py`, import part computation in
`get_unused_import_parts.py`, part merging in `merge_overlaping_file_parts.py`, and removal plus cleanups in
`remove_file_parts_from_content.py`. The behaviour suite under `tests/fix/` covers import removal (`test_unused_imports.py`), method removal
(`test_method_def.py`), and class removal (`test_class_def.py`), and `assert_valid_python` in `tests/conftest.py` asserts that every updated file
still parses.

## Open questions

- Should removing the last class method preserve all blank lines that followed the class, instead of collapsing them to one? The shipped
  behaviour keeps one blank line, while the original proposal expected both trailing lines to be preserved.
- Should the targeted cleanups stay in the removal step, or should the removal provide only removable parts and let a separate pass make the
  result valid? The current architecture applies cleanups during removal; splitting them out would need a specification of how removal stays
  valid in the meantime.

## References

- Process: [DEP process and template](../docs/dep.md).
- Import removal commits: `552edfe` ("Remove a subset of unused names from still-used import statements") and `a8a3d4b` ("Remove fully unused
  import statements safely").
- Original proposal commits: `1955911` ("Add enhancement proposal 2 for fixing code") and `5fdd707` ("Update DEP2 by chosing a different
  solution").

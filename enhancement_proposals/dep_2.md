# DEP 2 - Fixing code after removal of unused code fragments

**Status**: Proposed

**Type**: Feature

**Created**: 2024-04-16

## Problem statement

Code can become invalid after removal of a part of it. For example, when an unused name is being removed from an import:

```
from foo import (bar)
```

the resulting import statement might no longer be valid:

```
from foo import ()
```

This invalid import clause should be removed altogether. Import clauses are not the only victims: when all expressions are removed from a compound
statement, an empty block is left behind (`class Foo:` with no body), and removing lines in the middle of a file can disturb the empty-line rhythm
around the removed block. A `--fix` tool has to emit files that still parse after every removal, so the removal step cannot simply delete the
reported byte ranges — the surviving code has to stay valid Python.

### How deadcode works today

Deadcode already ships a text-level interim mechanism that keeps fixed files valid:

- Import cleanup: when only some imported names are unused, `get_unused_import_parts` computes removal parts that leave the remaining import valid,
  including comma and parenthesis bookkeeping (`deadcode/actions/get_unused_import_parts.py:96`, helpers at `:14-79`). It is covered by 23 tests in
  `tests/fix/test_unused_imports.py`.
- Empty blocks: when a removal leaves an empty compound statement, `remove_file_parts_from_content` appends an indented `pass` line
  (`deadcode/actions/remove_file_parts_from_content.py:153-160`, and `:186-187` for the file-end case).
- Empty lines: the same module preserves the empty-line rhythm around a removed block, emitting either the lines that were before or the ones that
  were after it (`deadcode/actions/remove_file_parts_from_content.py:82-83`, `:111-141`, `:144-185`).
- Pipeline: `fix_or_show_unused_code` groups findings per file, computes the import removal parts, merges all file parts, and applies them to the
  file content (`deadcode/actions/fix_or_show_unused_code.py:18`, `:42`, `:45`, `:47`).

Every fixed file must parse: the `assert_valid_python` test contract (`tests/conftest.py:12`) asserts it for all fix tests. Known gaps are recorded
as TODOs in the code (`deadcode/actions/fix_or_show_unused_code.py:24`, `deadcode/actions/remove_file_parts_from_content.py:127`).

These text-level adjustments are the current interim mechanism. The chosen solution below moves the correctness-preserving work into the
AST-modification step itself.

## Considered alternatives

### Keep the current text-level adjustments and add more case by case

- Idea: do nothing beyond today's shipped behaviour — keep the text-level adjustments for imports, empty blocks, and empty lines, and add a new
  hand-written adjustment for every newly discovered invalid-output case.
- Trade-off: no architecture change and no new mechanism to build, but each new case needs bespoke bookkeeping in the text-removal step, and the
  adjustments drift away from the AST that actually defines validity.
- Why not chosen: this is the current interim mechanism, not a direction; keeping it as the end state would grow the text-removal step indefinitely
  instead of making validity a property of node modification.

### Preserve the whole AST node and update it during removal

- Idea: keep the parsed AST node of each statement and update the node itself when code is removed.
- Trade-off: the node is the natural unit of validity, so modifying it produces structurally valid code without text-level bookkeeping.
- Why not chosen: rendering the modified node back and using it as the file output would replace the original text wholesale and lose the author's
  formatting and comments; the chosen solution uses the rendered node only to compute a diff, so this option is subsumed by it.

### Memorise initial expression places and re-validate after removal

- Idea: memorise the expression places from the initial AST parsing, so that the statement could once again be converted to AST to check its
  validity after removal.
- Trade-off: no statement knowledge is lost, but validity is only checked after the fact, and the check needs a full re-parse of the statement.
- Why not chosen: it validates instead of computing; the chosen solution derives the removable parts directly from the diff between the original
  chunk and the rendered, modified node, in one pass.

### Remember nothing and validate surrounding expressions on removal

- Idea: remember nothing; on removal, detect the surrounding expression and validate it.
- Trade-off: no bookkeeping at all, but detection without a record of what was removed cannot say which parts of the surrounding expression are
  removable, and a validate-and-repair pass could loop.
- Why not chosen: the removable parts have to be known before the write-out, and the chosen solution obtains them from the node diff during the AST
  walk itself.

## Chosen solution

Parse the file to an AST, walk the nodes, and for a partially unused node modify the node, render it back, and diff the original chunk against the
rendered one. Save the diff parts as the removable parts. The final write applies only the saved parts to the original text — the rendered code is
used to compute the diff, it is not the file output. This keeps the author's formatting and comments everywhere outside the removed parts.

Concretely, after walking a node:

- If the node is only partially unused, modify the node that is being walked, render it, find the diff between the original and the modified node,
  and save the unused parts so that they get removed during the write-out.

The write-out step applies only the saved removable parts; no other fixes are applied there. The correctness-preserving adjustments — import
cleanup, `pass` insertion for empty blocks, and empty-line preservation — migrate from the text-removal step into the AST-modification step, where
validity is achieved by modifying and rendering nodes. The shipped text-level adjustments described under "How deadcode works today" remain the
interim mechanism until that migration happens.

The AST node can have methods handling its child nodes before and after the walk, e.g. `BEFORE` and `AFTER`, so that a node's own adjustments run
around the adjustments of its children.

This example demonstrates how AST nodes can be fixed:

```
import ast


def print_ast(node: ast.AST) -> None:
    print(ast.dump(node, indent=4))  # type: ignore


nodes = ast.parse("""
from labas import (
    foo as spam,
    bar
)
""")

# Apply code clean-up rules:
nodes.body[0].names.pop()
nodes.body[0].names.pop()

# Show the node after clean-up
print_ast(nodes)

# Show code after clean-up
print(ast.unparse(nodes))
```

The rejected alternatives are keeping the current text-level adjustments case by case, preserving the whole AST node as the file output, memorising
initial expression places and re-validating after removal, and remembering nothing and validating surrounding expressions on removal. Node
modification with render-back and diff-based part removal was selected because it makes validity a property of the modified node while still writing
only the saved diff parts, so the original formatting survives outside the removals.

### Solution for empty code blocks

When all expressions are removed from a block, the chosen approach must guarantee that the surviving compound statement stays valid, e.g. by
carrying a `pass` statement after the node is modified. For example, given:

```
class Foo:
    unused = None

print(Foo())
```

removing `unused = None` yields an invalid empty class body:

```
class Foo:

print(Foo())
```

A `pass` statement has to be added in such cases:

```
class Foo:
    pass

print(Foo())
```

### Preserving empty lines after code removal

When a method in the middle of a class has to be removed, either the lines before or the lines after the removed method have to be preserved. E.g.
if `spam()` was removed:

```
class Foo:
    def bar(self):
        pass

    def spam(self):
        pass

    def eggs(self):
        pass


print(Foo())
```

The result should be:

```
class Foo:
    def bar(self):
        pass

    def eggs(self):
        pass


print(Foo())
```

When the last method from a class is being removed, the empty lines which were after the class have to be preserved. E.g. if `eggs()` was removed:

```
class Foo:
    def bar(self):
        pass

    def spam(self):
        pass

    def eggs(self):
        pass


print(Foo())
```

The result should be:

```
class Foo:
    def bar(self):
        pass

    def spam(self):
        pass


print(Foo())
```

## Scope

In scope: the removal-quality requirements of the fix pipeline — validity of the output after every removal, `pass` insertion for empty code blocks,
and empty-line preservation around removals — as described in the chosen solution.

Out of scope: implementing the strategy in `deadcode/` (a separate future task) and the fix-pipeline rewrites proposed in DEP 3, such as single-run
cascading removals.

## Implementation notes

The current pipeline entry is `fix_or_show_unused_code` (`deadcode/actions/fix_or_show_unused_code.py:18`), which computes import removal parts via
`get_unused_import_parts` (`deadcode/actions/get_unused_import_parts.py:96`), merges parts with `merge_overlaping_file_parts`, and applies them via
`remove_file_parts_from_content` (`deadcode/actions/remove_file_parts_from_content.py:153-160`, `:186-187`, `:82-83`, `:111-141`, `:144-185`). The
chosen solution re-anchors that correctness-preserving work in the AST-modification step; the exact hook names on the AST nodes (e.g. `BEFORE` and
`AFTER`) and the diff granularity (node-level vs chunk-level) are left to the implementing change. The `assert_valid_python` contract
(`tests/conftest.py:12`) must keep holding for every fixed file.

## References

All pages linked from this DEP were retrieved on 2026-11-14.

- DEP 3, "Removal of unused code might create new unused code": [dep_3.md](dep_3.md) — the overlapping fix-pipeline machinery, such as
  `merge_overlaping_file_parts`, that this DEP's removal step builds on.
- Test contract: `assert_valid_python` in [tests/conftest.py](../tests/conftest.py) — every fixed file must parse.
- Process: [DEP process and template](../docs/dep.md).

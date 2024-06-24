# DEP 2 - Fixing code after removal of unused code fragments
**Status**: Proposed
**Type**: Feature
**Created**: 2024-04-16

## Problem statement
### Incomplete imports
Sometimes code becomes invalid after removal of a part of it.
For example, when an unused name is being removed from an import:

```
from foo import (bar)
```
the resulting import statement might be no longer valid:

```
from foo import ()
```

This invalid import clause should be removed all together.
Various strategies exist, how it could be removed:
- whole AST node could be preserved and used when removing code - node could be updated as well.
- initial expression places could be memorised from initial AST parsing,
  so that the statement could once again be converted to AST to check its validity.
- nothing could be remembered - on removal surrounding expression could be detected and validated.


## Chosen solution
AST node can be modified and rendered back as valid code.
AST node should have methods BEFORE and AFTER handling its child nodes.

Compare original code chunk with cleaned up one and remember parts to remove during AST parsing.

After walking a node:
  If node is only partially unused:
    Modify the node, which is being walked.
    Render the node.
    Find the diff between original and modified nodes.
    Save the unused parts: so that those get removed during rendering.

During removal part no fixes should be applied, only removable code parts should be provided (no AST adjustmnets to make them valid).
Currently implemented adjustments for import, context manager, pass for empty code blocks should be removed from the writing to file part.

This examples demonstrates, how AST nodes can be fixed:
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

# Show nodes after clean-up
print("Fixed and cleaned up code, which can get merged")
print_ast(nodes)

# Show code after clean-up
print("Fixed and cleaned up code, which can get merged")
print(ast.unparse(nodes))
```

## Examples of code adjustments
### Empty code block
Another case is when all expressions are being removed from a block, e.g.

```
class Foo:
    unused = None

print(Foo())
```

Which yields invalid result after removal:
```
class Foo:

print(Foo())
```

### Solution for Empty code block
A pass statement has to be added in such cases:
```
class Foo:
    pass

print(Foo())
```


### Preserving empty lines after code removal
When a method in the middle of a class have to be removed,
either lines before or after the class have to be preserved.
E.g. if `spam()` was removed:

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

When a last method from a class is being removed empty lines, which were
after the class have to be preserved. E.g. if `eggs()` was removed:

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

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

### Solution for incomplete imports
Memorise the places of an original AST expression and evaluate its validity after applied changes.
If the statement is no longer valid and it is import expression - remove it all together.

The chosen approach will be easiest to implement and efficient.


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

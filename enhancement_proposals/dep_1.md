# DEP 1 - More accurate usage detection

**Status**: Proposed

**Type**: Feature

**Created**: 2024-01-14

## Problem statement

Usage detection can be more accurate. It is common in other unused-code detection tools to simply construct two sets: the names used in definitions
and the names used in usage expressions, and then report the names that are in the defined set but not in the usage one. This name-based comparison
is cheap, but it cannot tell which definition a usage refers to.

In larger projects, cases where definitions share a name are quite common. In this example:

```python
class Foo:
    def validate(self):
        pass

class Bar:
    def validate(self):
        pass

Foo().validate()
```

`validate` would not be reported if the simple name-set strategy is used, even though only `Foo.validate` is actually used and `Bar.validate` is
dead. However, it is possible to track the types of definitions and usages and more accurately identify the usages. This proposal specifies a
strategy that could be used to more accurately track the types of variables and scope parts.

The feature-request list records related requests: "Distinguish between definitions with same name, but different files" (`README.md:348`, since
addressed by DEP 5 for module-level names) and "Include package names into code item scope (dot-separated path)" (`README.md:359`); both are
symptoms of the same name-only comparison.

### How deadcode works today

Deadcode parses each file with `ast` and traverses it once with a visitor. All usage names are collected into one global `used_names` set
(`deadcode/visitor/dead_code_visitor.py:71`), and a definition is reported unused when its name is absent from that set
(`deadcode/visitor/ignore.py:68-75`). A name used anywhere therefore keeps every definition with that name alive, no matter where the usage lives
or which definition it actually refers to.

The visitor already records a scope string for every definition and retains per-module structures — `module_exports`, `bare_used_names`,
`wildcard_imports`, `explicit_imports`, `qualified_imports`, `import_edges`, and `module_definitions`
(`deadcode/visitor/dead_code_visitor.py:74-80`) — and DEP 5's definition-anchored usage resolution (DAUR) now resolves module-level usages through
lexical scope and import paths. That resolution identifies which definition a usage refers to for module-level names, but it does not track the
type of every scope part, which is what this proposal adds for methods, attributes, and variables.

## Considered alternatives

### Keep the current name-based matching

- Idea: keep collecting definition names and usage names into two global sets and report a definition when its name is absent from the usage set.
- Trade-off: this is the simplest and cheapest approach, but it cannot distinguish definitions that share a name, so a name is reported only when
  no definition with that name is used.
- Why not chosen: it misreports exactly the overlapping-name cases this DEP targets, such as the `Foo.validate`/`Bar.validate` example above.

### Track definitions and usages by their scope strings

- Idea: build a dot-separated scope string for every definition and every usage, and compare those strings instead of bare names.
- Trade-off: this separates definitions in different modules and classes, but it still treats classes, functions, and variables with the same scope
  as equivalent, because the string carries no type information about its parts.
- Why not chosen: overlapping names inside one scope — for example a function `foo` with a variable `bar` and a class `foo` with a method `bar` —
  still collide, so it does not resolve the cases this DEP targets.

### Track the type of every scope part as well as the scope string

- Idea: keep the scope information from the previous option and additionally record a type (package, module, class, method, variable) associated
  with every scope part.
- Trade-off: it needs more metadata per definition and per usage, and types cannot always be recovered statically, so a fallback strategy is
  required.
- Why not chosen: this is the chosen direction; it is described in the next section.

## Chosen solution

Track the types of definitions and usages as well as their scopes, so that overlapping names can be matched to the definition that the expression
actually refers to. The rejected alternatives are keeping the current name-based matching and tracking scope strings without types. Type-aware
scope tracking was selected because it subsumes both — it reduces to name matching when types are unavailable, and it adds the kind information
that separates same-named scopes — and because it resolves overlapping names by kind: a class, a function, and a variable that share one scope
string remain distinct once every scope part carries a type.

The generic-name fallback rule is explicit: when a type cannot be resolved statically, deadcode falls back to generic name matching for that usage,
just like vulture does; when such a name matches more than one definition, a warning is issued if enough verbosity is enabled.

### Scope construction for definitions

A dot-separated scope name identifies a scope in each line:

```python
# foo.py         # foo
class Bar:       # foo.Bar
    def spam():  # foo.Bar.spam
        pass     # foo.Bar.spam
```

If the `foo.py` file is not on the working path, its scope is prefixed with the dot-separated package names. For example, if `foo.py` is in the
`ham.eggs` package, then the scope of the `spam` method is `ham.eggs.foo.Bar.spam`.

### Matching a defined type with a type in an expression

Say we have a `Bar` type definition and an expression which uses it:

```python
# foo.py         # SCOPE
class Bar:       # foo.Bar
    def spam():  # foo.Bar.spam
        pass     # foo.Bar.spam
Bar().spam()     # foo, TYPE: Bar
```

On the expression line `Bar().spam()` the scope is `foo` and the identified type name is `Bar`. This type `Bar` is used to search for a type
definition (a `CodeItem` instance) in the namespace `foo`; usages are marked on it, and usages of related attributes and methods are associated
with that type.

### Providing only a part of the scope via options is fine

All of these scopes match the `spam` method of the example above:

- `ham.eggs.foo.Bar.spam`
- `foo.Bar.spam`
- `Bar.spam`
- `spam`

The less specific the scope is, the more cases it matches: the scope `spam` would also match a variable named `spam` in any scope. In some sense,
scopes like `spam` have wildcards `*.spam`, matching any scope prefix.

### Identifying types of scope parts

When creating the scope parts, each part could also have a type (e.g. package, module, class, method, variable) associated with it. When a usage
expression is detected, its type could be resolved by using the types of the scope parts instead of simply comparing scope strings.

For example, this code snippet contains two different objects, which would collide under a generic `foo.bar` scope:

```python
def foo():
    bar = 1

class foo:
    def bar(self):
        pass

foo().bar = 1
```

Deadcode could internally track the type of each scope part, and when an expression is detected, the defined type is searched by taking the types
of the scope parts, not only the scope string. For example, a special notation like `>foo%bar` and `#foo>bar` for scopes could be used for the above
example to identify definitions accurately.

The user could also provide the precise types of scope parts by using a different separator instead of `.`. These separators could be used for
scope part separation:

- `.` means any type of scope.
- `/` means a package or module scope.
- `#` means a class scope.
- `>` means a function or method scope.
- `%` means a variable or a variable attribute.

For example, the user could provide the path `ham.eggs.foo.Bar.spam` as well as a more specific one, `ham/eggs/foo#Bar>spam`, to exactly match the
types of the scope parts.

### Type tracking for method arguments and returned values

#### Tracking the type of arguments

When an argument is passed into a function or a method, the type remains the same, but the variable name might change, or the value might be put
into a container like a tuple or a dictionary. Deadcode will attempt to track the types of function and method parameters; however, in some cases
the type will be lost and deadcode will fall back to a generic name-matching strategy.

In this example:

```python
class Foo:
    def bar(self):
        pass

def eggs(ham):
    ham.bar()

spam = Foo()
eggs(spam)
```

Deadcode will be able to accurately detect that the type of `ham` is `Foo`.

#### Tracking the types of returned values

It can be hard to track exact types of variables, for example:

```python
class Eggs:
    pass

class Bar:
    def spam():
        return Eggs()

variable = Bar().spam()
print(variable)
```

Parsing the returned type of `Bar.spam` is complicated. In some cases, the returned type might only be determined dynamically during runtime, and
it might depend on the method's implementation details. Hence, in some cases the types will not be identified, because the runtime is not available
during static code analysis.

The Deadcode policy for this is: when a type is lost because it cannot be identified accurately, deadcode loses a way to identify the type of the
variables or attributes precisely, and a generic name-matching strategy is used instead in those cases, just like vulture does. If more than one
definition with the same name is detected, a warning should be issued (if enough verbosity is enabled). In addition, type hints could be used to
try to detect the type more easily in such cases.

## Scope

In scope: the detection strategy described above — scope construction, type-aware scope-part matching, partial-scope option matching, argument and
returned-value type tracking, and the generic-name fallback.

Out of scope: implementing the strategy in `deadcode/` — the implementation is a separate future task.

## Implementation notes

The scope and type tracking hooks into the visitor's existing single traversal: the visitor already maintains `scope_parts`
(`deadcode/visitor/dead_code_visitor.py`) and the per-module structures introduced by DEP 5 (binding tables and import edges), so the definition
side can reuse the `CodeItem` records, and the usage side can reuse the definition-anchored resolution wherever the receiver or the qualification
path is statically known. The type of each scope part extends the existing scope metadata rather than replacing it. Where exactly each hook
attaches is left to the implementing change; this DEP specifies the matching strategy, not a design specification.

## Open questions

- How verbose should the warning be when the generic-name fallback matches more than one definition — a `--verbose` log line or a reported finding?
- Should the type of a scope part be recorded for builtins and imported names as well, or only for definitions the visitor constructs itself?

## References

All pages linked from this DEP were retrieved on 2026-11-14.

- DEP 3, "Removal of unused code might create new unused code": [dep_3.md](dep_3.md) — relies on the generic-name fallback for unresolvable usages.
- DEP 5, "Resolving name shadowing": [dep_5.md](dep_5.md) — definition-anchored usage resolution (DAUR), the in-repo mechanism the type tracking
  builds on.
- Process: [DEP process and template](../docs/dep.md).

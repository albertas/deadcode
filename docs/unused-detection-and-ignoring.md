# Unused Detection & Ignoring

This document describes how Deadcode decides whether a code item is unused and the mechanisms to ignore items from reporting. See [Visitor layer](visitor-layer.md) for the AST traversal context and [Architecture](architecture.md) for the pipeline flow. See [index.md](index.md) for the full guide.

## Core Unused Decision

The core decision is made by `_get_unused_items(defined_items: Iterable[CodeItem], used_names: Set[str]) -> Iterable[CodeItem]` (`visitor/ignore.py:39-42`):

An item is **unused** if and only if its `name` is not in the global `used_names` set. Items whose names **are** in `used_names` (at least one use detected anywhere in the codebase) are marked used, regardless of scope.

This is a **global, name-string comparison**—no scope awareness at decision time. For example, if a function `foo()` is defined in module A and called in module B, it is marked used. Conversely, if two functions named `foo` are defined in different modules and neither is called, both are reported unused.

The resulting unused items are sorted case-insensitively (`ignore.py:41`) and returned.

## Combining All Unused Categories

The eight unused-item categories (attributes, classes, functions, imports, methods, properties, variables, unreachable code, and unused files) are collected separately during the visitor pass, then combined and deduplicated by `get_unused_code_items()` and `unused_file` property (`visitor/find_unused_code_visitor.py:155-200`), sorted by filename and line number.

## Ignore Mechanisms

### Name-Based Ignoring

**`--ignore-names`** — patterns matching item names:
An item whose `name` matches any pattern in `args.ignore_names` (via `fnmatchcase`, case-sensitive glob matching) is passed to `add_used_name()`, treating it as used and removing it from output (`visitor/find_unused_code_visitor.py:297`).

### File-Based Ignoring

**`--ignore-names-in-files`** — patterns matching file paths:
All definitions in a file whose path matches any pattern in `args.ignore_names_in_files` are treated as used (`find_unused_code_visitor.py:298`).

### Inheritance-Based Ignoring

**`--ignore-definitions-if-inherits-from`** — base class names:
In the visitor's `visit()` dispatcher, if a class definition's base class is in `args.ignore_definitions_if_inherits_from`, the gate sets `self.should_ignore_new_definitions = True`, causing all definitions inside that class to be marked used (`:519-528`).

**`--ignore-bodies-if-inherits-from`** — base class names (class bodies only):
After the scope is pushed for a class, if the class inherits from a specified base, a gate prevents the body's definitions from being collected; they are instead marked used (`:547-550`).

### Built-in Predicates

Independent of `args`, the visitor applies built-in ignore rules:

- **Test classes** — classes with "Test" in the name are ignored in test files (`ignore.py:73-74`)
- **Test functions/methods** — functions starting with `test_` or pytest setup/teardown methods are ignored in test files (`:86-87`, `:91-93`)
- **Special variables** — underscore-prefixed variables, dunder names, and `self`/`object` are ignored (`:96-105`, `:9`)
- **Star imports and `__init__.py` imports** — these are ignored as they are conventionally re-exported (`:77-83`)
- **`__all__` exports** — names listed in `__all__` (via any of three assignment forms: `__all__ = [...]`, `__all__ += [...]`, `__all__: ... = [...]`) are marked used, as they are explicitly exported (see [Visitor layer](visitor-layer.md) for details)

## Known Gaps: Inert Ignore Options

The following configuration options are **currently inert / not consulted** in the code:

- `ignore_bodies_if_decorated_with`
- `ignore_if_decorated_with`
- `ignore_names_if_decorated_with`
- `ignore_names_if_inherits_from`
- `ignore_if_inherits_from`

These options are parsed into the `Args` dataclass (`data_types.py:21-27, :29-30`) and appear in the README CLI documentation, but are **never referenced** in `find_unused_code_visitor.py` or `ignore.py`. Additionally, `self.ignore_decorators` (`find_unused_code_visitor.py:50, :54`) is defined but always remains `[]` and is never assigned.

This is an observed limitation—the decorator and some inheritance-based ignore options are not yet implemented. They do not cause errors; they are silently ineffective.

## Filtering Pipeline

The full filtering pipeline is:

1. **Visitor phase**: For each definition, the visitor checks if it matches `ignore_names` patterns → `add_used_name()` if matched
2. **Visitor phase**: Checks if file matches `ignore_names_in_files` → all defs in file marked used
3. **Visitor phase**: Checks inheritance- and decorator-based gates in `visit()` dispatcher → definitions marked used if conditions met
4. **Visitor phase**: Applies built-in predicates (test classes, test functions, special variables, `__all__` exports) → `add_used_name()` if matched
5. **Noqa phase**: Checks for `# noqa` comments on definition lines (supporting `#noqa`, `# noqa`, `#  noqa`, and specific codes like `# noqa: dc07` or `# noqa: DC07`) → `add_used_name()` if matched (`visitor/noqa.py` and `find_unused_code_visitor.py:299`)
6. **Post-visitor**: `_get_unused_items()` compares all defined names against `used_names` → final unused set

Any item that reaches step 6 with its name not in `used_names` is reported as unused.

## Example Scenarios

**Scenario 1**: Function `helper()` defined but never called.
- Step 1-5: No matches. `used_names` does not contain `'helper'`.
- Step 6: Item is unused, reported with error code DC02.

**Scenario 2**: Function `test_foo()` defined in `test_example.py`.
- Step 4: Built-in predicate `_ignore_function` matches; `add_used_name('test_foo')` called.
- Step 6: Name is in `used_names`, item is not unused, not reported.

**Scenario 3**: Class `MyMixin` defined, `--ignore-names "*Mixin"` flag set.
- Step 1: Pattern matches; `add_used_name('MyMixin')` called.
- Step 6: Name is in `used_names`, item is not unused, not reported.

**Scenario 4**: Method defined in a class inheriting from `django.db.models.Model`, `--ignore-definitions-if-inherits-from models.Model` set.
- Step 3: Inheritance gate matches; method definitions inside the class are marked used.
- Step 6: All methods are in `used_names`, not reported.

**Scenario 5**: Function decorated with `@app.get("/items")`, `--ignore-definitions-if-decorated-with=@app.*` set.
- Step 3: Decorator gate matches `@app.get` against `@app.*`; the function definition (name and body) is marked used.
- Step 6: Name is in `used_names`, item is not unused, not reported.

**Scenario 6**: Class inheriting from `db.Model` (Flask-SQLAlchemy), `--ignore-definitions-if-inherits-from=db.Model --ignore-bodies-if-inherits-from=db.Model` set.
- Step 3: Inheritance gate matches the dotted base `db.Model`; the class name and its `Column` body members are marked used.
- Step 6: Class and columns are in `used_names`, not reported.

**Scenario 7**: Alembic migration file under `versions/`, `--ignore-names-in-files=*/versions/*` set (or `--ignore-names=upgrade,downgrade,revision,down_revision,branch_labels,depends_on`).
- Step 1: Path / name pattern matches; the migration's names are marked used.
- Step 6: Names are in `used_names`, not reported.

See [Visitor layer](visitor-layer.md) for more details on how items are collected and ignored.

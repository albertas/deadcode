# DEP 4 - Resolving name shadowing
**Status**: Proposed
**Type**: Feature
**Created**: 2026-11-12

## Problem statement

This DEP is a proposal for later work. It does not change any analysis code in this repository.

Issue [Resolve name shadowing](https://github.com/albertas/deadcode/issues/101) reports that deadcode misses an unused definition when the same
name is defined in more than one file and used in only one of them. The issue body says:

> If the same name is defined in couple of files, but is used only in one file. The unsued name should be detected and flagged as dead code.

and proposes:

> deadcode should build metadata (place of definition) for each defined/used name and use the metadata when comparing the definitions against the usages.

### Reproduction

Create a directory with two modules. `a.py` defines and uses `foo`:

```python
# a.py
def foo():
    return 1


print(foo())
```

`b.py` defines `foo` but never uses it:

```python
# b.py
def foo():
    return 2
```

Running `deadcode /tmp/shadowcase --no-color` on this project currently prints `Well done! ✨ 🚀 ✨` and exits with status `0`.
No finding is emitted for `b.py`, although `b.py:1` defines a function that nothing uses.

### Root cause

Definitions are recorded as names, and usages are collected into the global `used_names` and `bare_used_names` sets.
The unused filter in `deadcode/visitor/ignore.py` checks only whether a definition's name is a member of those sets.
A use of `foo` in any file therefore satisfies every definition named `foo`, so `a.py:foo` also marks `b.py:foo` as used.
`CodeItem` already stores `filename`, `scope`, `line`, and `column`, but the unused filter ignores that metadata and compares names alone.

### Impact

The same false negative affects module-level functions, classes, and variables when another module defines and uses the same name.
It also affects methods, attributes, builtin-shadowing names, lambda parameters, and comprehension variables whenever they share a name with a used
definition elsewhere.

### Expected behavior

After the proposed change, the reproduction should report the unused definition in `b.py` as:

```text
b.py:1:1: DC02 Function `foo` is never used
```

That is, the finding ``DC02 Function `foo` is never used`` is emitted for `b.py:1`, while `a.py:foo` remains unreported because `a.py` uses it.

## Considered alternatives

### Global name-set comparison

- Idea: keep collecting every definition name and every usage name in two global sets and report a definition when its name is absent from the usage set.
- Trade-off: this is the simplest and most memory-light approach, but a use in any file satisfies every same-named
  definition, so it cannot tell which definition a usage refers to.
- Why not chosen: it is the status quo that produces the #101 false negative, so it cannot satisfy this proposal.

### Naive place-of-definition metadata

- Idea: attach the place of definition to each name, as the issue suggests, and compare the usage module with the
  definition module before deciding that a definition is unused.
- Trade-off: module comparison works for direct use in the defining module, but a usage in `a.py` of a name imported
  from `b.py` is recorded in `a.py`, so the `b.py` definition would be wrongly reported. Import-aware propagation is
  required to avoid that regression.
- Why not chosen: the plain module comparison replaces one false negative with false positives on ordinary cross-module imports.

### Scope- and type-aware usage tracking (DEP 1)

- Idea: track the scope and type of every definition and usage, then match usages to definitions through those scopes and types, as DEP 1 specifies.
- Trade-off: it is the largest program of the alternatives and still loses types on function returns and arguments;
  DEP 1 itself falls back to name matching when a type cannot be inferred, so it does not by itself guarantee the #101 case.
- Why not chosen: it is the long-term destination rather than the smallest fix for the reported false negative, and its size delays the fix.

### Scoped binding tables (pyflakes/pylint)

- Idea: model the bindings of each lexical scope and resolve a name to the binding visible at its use site,
  following the design used by pyflakes and pylint.
- Trade-off: pyflakes and pylint resolve lexical shadowing inside a file, but their tables are a per-scope linter design built for diagnostics in one module.
- Why not chosen: the tables do not by themselves establish cross-module definition identity, which whole-project dead-code detection needs for #101.

### Import and qualified-name resolution

- Idea: resolve imports and qualified names so a usage is tied to the module and member path it refers to.
- Trade-off: this improves cross-module identity, but it still leaves two same-named top-level definitions in different
  modules competing for the same bare usage.
- Why not chosen: it does not separate the two same-named definitions in the reproduction, which is exactly the reported symptom.

## Chosen solution

The chosen solution is definition-anchored usage resolution (DAUR).
Its one-sentence summary is: "A definition is reported unused only when no usage resolves to it; a usage resolves to a definition through lexical scope in
its own module or through a statically known import/qualification path."

DAUR fixes the `a.py`/`b.py` reproduction, reuses the `CodeItem` metadata that already exists (`filename`, `scope`, `line`, `column`), and needs only
per-module binding tables plus import edges. It avoids type inference for module-level names, so it does not inherit DEP 1's loss of types on returns and
arguments, and it keeps a conservative fallback so dynamic usage cannot turn into a false positive.

The rejected alternatives are global name-set comparison, naive place-of-definition metadata, scope- and type-aware tracking (DEP 1), scoped binding
tables (pyflakes/pylint), and import and qualified-name resolution alone. DAUR wins on accuracy for #101 because it identifies which definition a usage
can refer to; it wins on false-positive risk because unresolved usage falls back to the current behavior; it wins on memory because it stores only local
binding tables and import edges; and it wins on effort because stage A is a small change, while DEP 1 remains the long-term destination.

## Scope

### In scope

- Stage A (`module-level`): module-level functions, classes, and module variables across files, with lexical resolution plus `import` and
  `from ... import` propagation.
- Stage B (`members`): methods and attributes when the receiver class or instance is statically known from a constructor call, an annotation, or a
  class-name reference.
- Stage C (`remaining shadowing`): a builtin-name table, lambda and comprehension lexical scopes, and same-file redefinition handling.

### Out of scope

- Implementing any analysis change in this DEP.
- Tests for the DEP content or for documentation.
- Sphinx or `docs/` pages for this proposal.
- README or release-note links to DEP 4.
- Rule-code or output-format changes.
- Merging or depending on the unmerged DEP-process branch.
- Defining the exact Stage B receiver heuristic or the package-path module key; both are open questions below.

## Implementation notes

The staged outline is A -> B -> C, and each stage is independently shippable. Stage A alone fixes the #101 reproduction and covers module-level functions,
classes, and variables; stage B extends the same resolution to methods and attributes; stage C closes the remaining shadowing cases.

The data model is a per-module binding table. For each module, a map from a bound name to the `CodeItem` definitions it can denote is stored, together with
the module's import edges: `from module import name`, `import module as alias`, and statically known `__all__` exports.

The resolution order is: (1) lexical scope in the usage's own module, (2) import edges from the usage module to the defining module, and (3) qualified
member access when the receiver's class or instance is statically known.

The fallback rule is conservative. When a usage cannot be resolved statically, today's global-name matching is kept for that name, so dynamic usage
suppresses findings instead of creating false positives.

When a name resolves to more than one definition and lexical or import evidence cannot separate them, the implementation emits a warning only in verbose
mode rather than choosing a definition silently.

The rollout is default-on DAUR with a `--legacy-name-matching` CLI option (or the equivalent config key) for one release, then removal of that opt-out.

The compatibility contract is unchanged. Rule codes DC01-DC13, message wording, the `filename:line:column: DCxx message` format, exit statuses `0`, `1`,
and `2`, `# noqa` mapping, and all existing suppression options stay as they are; only which definitions are reported changes.

This DEP changes no code.

## Open questions

- What exact heuristics should Stage B use to decide that a receiver's class or instance is statically known?
- Should the legacy name-matching opt-out become permanent, or should it be removed after one release as proposed?
- How should package paths appear in module keys, given that the current scope uses the file basename?

## References

- Issue #101, "Resolve name shadowing": https://github.com/albertas/deadcode/issues/101
- DEP 1, "More accurate usage detection": [dep_1.md](dep_1.md)
- DEP 3: [dep_3.md](dep_3.md)
- README limitation: "In case there are several definitions using the same name - they all wont be reported if at least one usage of
  that name is being detected" (`README.md`, limitation section).
- README feature requests: "Distinguish between definitions with same name, but different files", including package names in scopes, and handling redefinitions.
- pyflakes scoped binding implementation: https://github.com/PyCQA/pyflakes/blob/main/pyflakes/checker.py
- pylint variable checker and redefinition messages: https://github.com/pylint-dev/pylint/blob/main/pylint/checkers/variables.py

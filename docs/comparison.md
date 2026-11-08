# Comparison with vulture

This page compares `deadcode` 2.6.0 with `vulture` 2.16, using facts retrieved on 2026-11-08.
It covers released versions only: unreleased changes on the `vulture` `main` branch, which target 2.17, are excluded because no release contains them.

## Key differences for developers

- Automatic removal: `deadcode` can remove dead code with `--fix` and preview the changes with `--dry`;
  `vulture` has no automatic fixing and documents manual deletion followed by a rerun.
- Rule codes and `# noqa`: `deadcode` reports `DC01`–`DC13` rule codes and accepts them in `# noqa` comments;
  `vulture` reports item types with confidence percentages and its `# noqa` handles only F401 and F841 plus bare `# noqa`.
- Suppression scope: `deadcode` offers separate name, body, and definition decorator options;
  `vulture` has one `--ignore-decorators` option that covers function and class names only.
- Whitelist mechanism: `deadcode` has no whitelist file and relies on ignore options and `# noqa`;
  `vulture` generates whitelist files with `--make-whitelist` and loads bundled whitelists for imported modules.
- Argument reporting: `deadcode` does not report unused function arguments; `vulture` reports them at 100% confidence.
- Test coverage: `deadcode` maintains 100% test coverage.

## At a glance

| Aspect | deadcode | vulture |
|---|---|---|
| Version | 2.6.0 | 2.16 |
| Release date | 2026-11-08 | 2026-03-25 |
| Licence | AGPLv3 | MIT |
| Development status | 4 - Beta | 5 - Production/Stable |
| Python support | `>=3.10` | `>=3.9` |
| Runtime dependency | `tomli>=2.0.1` on Python < 3.11 | `tomli>=1.1.0` on Python < 3.11 |
| Console command | `deadcode` | `vulture` |
| Repository | [albertas/deadcode](https://github.com/albertas/deadcode) | [jendrikseipp/vulture](https://github.com/jendrikseipp/vulture) |

## Detection and findings

| Dimension | deadcode | vulture |
|---|---|---|
| Detection rule style | `DC01`–`DC13` rule codes with a message per finding | Item types `V101`–`V107` and `V201` behind findings that show a confidence percentage |
| Unused arguments | Not reported, because arguments are not defined as variables | Reported at 100% confidence |
| Class-level assignments | Reported as DC06 `name` | Reported as a `variable` (V107) |
| `__all__` semantics | Restricts wildcard exports and is honoured only when statically readable | Marks the listed names as used |
| Unreachable code | DC09 for unsatisfiable conditions and DC13 for code after terminal statements | Reachability analysis also handles `while True` without a `break` |
| Finding line format | `filename:line:column: DCxx message` | `filename:line: unused type 'name' (NN% confidence)` |

## Automatic fixing and integrations

- `deadcode` removes code with `--fix`, performs import-aware multi-line removal and deletes files that become empty, and previews changes with `--dry`.
- `vulture` has no automatic fixing option and documents manual deletion followed by a rerun.
- `deadcode` has no whitelist file and suppresses findings through ignore options and `# noqa`.
- `vulture` generates whitelist files with `--make-whitelist` and loads bundled whitelists for imported modules.
- Both tools publish a pre-commit hook.
- The `vulture` README documents a third-party GitHub Action and a third-party VS Code extension.

## Configuration and suppression

| Dimension | deadcode | vulture |
|---|---|---|
| Configuration section and key spelling | `[tool.deadcode]`; the README shows hyphenated keys and the parser accepts hyphenated or underscored keys | `[tool.vulture]`; keys are underscored, such as `ignore_names` |
| CLI versus TOML precedence | TOML list values are extended into CLI lists | CLI values overwrite TOML values |
| `--exclude` syntax | Relative path patterns are used as given | Comma-separated patterns are matched against absolute paths, patterns without wildcards become `*PATTERN*`, and matching is case-insensitive |
| Decorator suppression scope | Separate name, body, and definition decorator options; patterns require `@` | One `--ignore-decorators` option that covers function and class names only |
| `--ignore-names-in-files` | Supported | No equivalent option |
| `# noqa` coverage | All DC codes, `DC`, bare noqa, F401/F841, and legacy DC00x aliases | F401/F841 and bare noqa only |
| `--config` | No equivalent option; `[tool.deadcode]` is read from `pyproject.toml` in the current directory | `--config` points at another `pyproject.toml` file |

## Adapting suppression to a framework

`deadcode` exposes suppression as a small matrix rather than a single switch. Three options select the scope — `--ignore-names`, `--ignore-bodies-of`, and
`--ignore-definitions` — and the `-if-decorated-with` and `-if-inherits-from` qualifiers select what triggers it, with a variant for each of the three scopes.
`--ignore-names-in-files` narrows a name ignore to matching files. All of them accept glob patterns, work from both the command line and `[tool.deadcode]`, and
compose with per-line `# noqa` comments that accept every `DC` code. Framework-heavy code therefore needs configuration, not source changes or a hand-maintained
allowlist.

FastAPI is the documented example: the whole guide reduces to two settings, one for the route, event, middleware, and exception-handler decorators and one for the
Pydantic model base class.

```toml
[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
```

Because `deadcode` parses source and never imports it, the same mechanism generalises: any library that marks live code with a decorator or a base class can be adapted
by naming that decorator or base class, and unrelated code stays under full analysis.

`vulture` offers one decorator option, `--ignore-decorators`, which suppresses the decorated function or class name but not its body and has no inheritance-based
counterpart. The FastAPI cases that `deadcode` covers in two lines need individual `--ignore-names` patterns or a whitelist module in `vulture`, and the recommended
whitelist mechanism marks names as used across the whole code base, so adapting the tool to a framework can also hide genuine dead code.

| Adaptation need | deadcode | vulture |
|---|---|---|
| Framework-decorated handlers, such as FastAPI `@app.*` and `@router.*` | Name, body, or definition suppression matched by decorator glob | `--ignore-decorators`, which covers names only |
| Members of a framework base class, such as Pydantic `BaseModel` fields and validators | Name, body, or definition suppression matched by base class name, dotted path, or glob | No equivalent; list every name or add a whitelist entry |
| A name that is safe only in one file | `--ignore-names-in-files` | A whitelist entry, which applies to the whole code base |
| A single finding | `# noqa` with any `DC` code | `# noqa` for F401/F841 only, otherwise a whitelist entry |

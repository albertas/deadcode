# Comparison with vulture

This page compares `deadcode` 2.6.0 [5] with `vulture` 2.16 [15], using facts retrieved on 2026-11-08.
It covers released versions only: unreleased changes on the `vulture` `main` branch, which target 2.17, are excluded because no release contains them [7].

## Key differences for developers

- Automatic removal: `deadcode` can remove dead code with `--fix` and preview the changes with `--dry` [1];
  `vulture` has no automatic fixing and documents manual deletion followed by a rerun [6].
- Rule codes and `# noqa`: `deadcode` reports `DC01`–`DC13` rule codes and accepts them in `# noqa` comments [1];
  `vulture` reports item types with confidence percentages and its `# noqa` handles only F401 and F841 plus bare `# noqa` [6].
- Suppression scope: `deadcode` offers separate name, body, and definition decorator options [1];
  `vulture` has one `--ignore-decorators` option that covers function and class names only [6].
- Whitelist mechanism: `deadcode` has no whitelist file and relies on ignore options and `# noqa` [1];
  `vulture` generates whitelist files with `--make-whitelist` and loads bundled whitelists for imported modules [6][10].
- Argument reporting: `deadcode` does not report unused function arguments [1]; `vulture` reports them at 100% confidence [6].
- Exit status on findings: `deadcode` exits `1` when it finds dead code [1]; `vulture` exits `3` [6].

## At a glance

| Aspect | deadcode | vulture |
|---|---|---|
| Version | 2.6.0 [2] | 2.16 [15] |
| Release date | 2026-11-08 [1] | 2026-03-25 [7] |
| Licence | AGPLv3 [2] | MIT [8] |
| Development status | 3 - Alpha [2] | 5 - Production/Stable [8] |
| Python support | `>=3.10` [2] | `>=3.9` [8] |
| Runtime dependency | `tomli>=2.0.1` on Python < 3.11 [2] | `tomli>=1.1.0` on Python < 3.11 [8] |
| Console command | `deadcode` [2] | `vulture` [8] |
| Repository | https://github.com/albertas/deadcode [2] | https://github.com/jendrikseipp/vulture [8] |

## Detection and findings

| Dimension | deadcode | vulture |
|---|---|---|
| Detection rule style | `DC01`–`DC13` rule codes with a message per finding [1] | Item types `V101`–`V107` and `V201` behind findings that show a confidence percentage [10] |
| Unused arguments | Not reported, because arguments are not defined as variables [4] | Reported at 100% confidence [6][10] |
| Class-level assignments | Reported as DC06 `name` [1] | Reported as a `variable` (V107) [10] |
| `__all__` semantics | Restricts wildcard exports and is honoured only when statically readable [1] | Marks the listed names as used [10] |
| Unreachable code | DC09 for unsatisfiable conditions and DC13 for code after terminal statements [1] | Reachability analysis also handles `while True` without a `break` [7][11] |
| Finding line format | `filename:line:column: DCxx message` [1] | `filename:line: unused type 'name' (NN% confidence)` [10] |

## Automatic fixing and integrations

- `deadcode` removes code with `--fix`, performs import-aware multi-line removal and deletes files that become empty, and previews changes with `--dry` [1].
- `vulture` has no automatic fixing option and documents manual deletion followed by a rerun [6].
- `deadcode` has no whitelist file and suppresses findings through ignore options and `# noqa` [1].
- `vulture` generates whitelist files with `--make-whitelist` and loads bundled whitelists for imported modules [6][14].
- Both tools publish a pre-commit hook [1][6].
- The `vulture` README documents a third-party GitHub Action and a third-party VS Code extension [6].

## Configuration and suppression

| Dimension | deadcode | vulture |
|---|---|---|
| Configuration section and key spelling | `[tool.deadcode]`; the README shows hyphenated keys and the parser accepts hyphenated or underscored keys [1] | `[tool.vulture]`; keys are underscored, such as `ignore_names` [6][9] |
| CLI versus TOML precedence | TOML list values are extended into CLI lists [1] | CLI values overwrite TOML values [9] |
| `--exclude` syntax | Relative path patterns are used as given [1] | Comma-separated patterns are matched against absolute paths, patterns without wildcards become `*PATTERN*`, and matching is case-insensitive [9][10] |
| Decorator suppression scope | Separate name, body, and definition decorator options; patterns require `@` [1] | One `--ignore-decorators` option that covers function and class names only [6] |
| `--ignore-names-in-files` | Supported [1] | No equivalent option [6][9] |
| `# noqa` coverage | All DC codes, `DC`, bare noqa, F401/F841, and legacy DC00x aliases [1] | F401/F841 and bare noqa only [6][12] |
| `--config` | No equivalent option; `[tool.deadcode]` is read from `pyproject.toml` in the current directory [1] | `--config` points at another `pyproject.toml` file [6][9] |

## Command line and output

- `deadcode` provides `--only`, `--count`, `--quiet`, and `--no-color` output and filtering options [1].
- `vulture` has none of these options [6].
- `deadcode` has no confidence filter; `vulture` provides `--min-confidence` to filter findings below a threshold [6][9].
- `deadcode` orders findings by filename and name line by default [1].
- `vulture` orders by lowercased filename and first line by default and offers `--sort-by-size` [10].
- `deadcode` exits `1` when it finds dead code [1]; `vulture` exits `3` [6][13].
- For invalid input, `deadcode` exits `2` for usage errors and `1` for unexpected errors [1].
- For invalid input, `vulture` exits `1` for invalid input and `2` for invalid command-line arguments [6][13].

## Known limitations

**deadcode**

- Development status is Alpha and the Python floor is `>=3.10` [1][2].
- Findings carry no confidence scores [1].
- Names are compared without scope, so one usage suppresses every definition with the same name [1].
- Unused function arguments are not reported [4].
- `--fix` edits or removes a file without reparsing the result [1].

**vulture**

- Dynamic dispatch, `getattr`, and implicit framework calls can produce false positives [6].
- Decorators that cannot be parsed are simplified to a partial pattern [6].
- Forward references in quoted annotations are not resolved [6].
- No automatic fixing is provided [6].

## Pros and cons of deadcode

**Pros**

- Automatic removal: `--fix` edits or removes code with import-aware multi-line removal and deletes files that become empty, and `--dry` previews the diff [1].
- Scoped suppression: separate name, body, and definition options cover decorated routes and model base classes [1].
- Project rule codes: findings carry `DC01`–`DC13` codes and `# noqa` accepts any code, `DC`, bare noqa, F401/F841, and legacy aliases [1].
- Output modes: `--only`, `--count`, `--quiet`, and `--no-color` filter findings and fit CI logs [1].
- FastAPI support: a guide with configuration recipes and fixtures covers decorator suppression and model inheritance [4].
- Documented feature contract: `docs/features.md` maps each documented feature to its source, tests, and README section [3].

**Cons**

- Licence and status: the package is licensed AGPLv3 and declared `3 - Alpha` [2].
- Python floor: it requires `>=3.10`, so it cannot run on 3.9 [2].
- Confidence: findings carry no confidence score and there is no threshold option [1].
- Scope handling: names are compared without scope, so one usage suppresses every same-name definition [1].
- Whitelists: there is no whitelist file mechanism; suppression uses ignore options and `# noqa` [1].
- Arguments: unused function arguments are not reported [4].
- Fix validity: `--fix` edits or removes a file without reparsing the result [1].

## Pros and cons of vulture

**Pros**

- Confidence: each finding carries a percentage and `--min-confidence` filters the report [6][9].
- Whitelists: `--make-whitelist` generates a whitelist file and bundled whitelists load automatically for imported modules [6][14].
- Review by size: `--sort-by-size` orders unused functions and classes by line count [6].
- Config path: `--config` points at a `pyproject.toml` other than the default [6][9].
- Argument reporting: unused arguments are reported at 100% confidence [6][10].
- Python support: it supports Python `>=3.9` [8].
- Status and licence: the package is declared `5 - Production/Stable` and licensed MIT [8].
- Release history: the changelog records a long release history up to 2.16 [7].

**Cons**

- Automatic fixing: there is none; the README documents manual deletion followed by a rerun [6].
- `# noqa` coverage: only F401, F841, and bare `# noqa` are handled [6][12].
- Scope handling: a same-name usage suppresses all same-name definitions [6].
- Dynamic code: dynamic dispatch, computed `getattr` names, and implicit framework calls can produce false positives [6].
- Decorators: patterns that cannot be parsed are simplified, so `@foo.bar(x, y)` becomes `@foo.bar` [6].
- Forward references: quoted annotations are not resolved [6].

## Choosing between them

`deadcode` and `vulture` take opposite approaches to remediation: `deadcode` offers automatic removal and project rule codes,
while `vulture` ranks findings by confidence and manages exceptions with whitelist files [1][6]. The tradeoff is between editing
code for the reader and helping the reader review findings [1][6].

The page does not pick one package over the other: the useful choice depends on whether automatic remediation and rule-code
suppression or confidence ranking and whitelists matter more to the reader's project [1][6].

## Sources

1. deadcode `README.md`, tag `v2.6.0` — https://github.com/albertas/deadcode/blob/v2.6.0/README.md — accessed 2026-11-08
2. deadcode `pyproject.toml`, tag `v2.6.0` — https://github.com/albertas/deadcode/blob/v2.6.0/pyproject.toml — accessed 2026-11-08
3. deadcode `docs/features.md`, tag `v2.6.0` — https://github.com/albertas/deadcode/blob/v2.6.0/docs/features.md — accessed 2026-11-08
4. deadcode `docs/fastapi.md`, tag `v2.6.0` — https://github.com/albertas/deadcode/blob/v2.6.0/docs/fastapi.md — accessed 2026-11-08
5. deadcode package metadata, PyPI JSON — https://pypi.org/pypi/deadcode/json — accessed 2026-11-08
6. vulture `README.md`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/README.md — accessed 2026-11-08
7. vulture `CHANGELOG.md`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/CHANGELOG.md — accessed 2026-11-08
8. vulture `pyproject.toml`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/pyproject.toml — accessed 2026-11-08
9. vulture `vulture/config.py`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/vulture/config.py — accessed 2026-11-08
10. vulture `vulture/core.py`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/vulture/core.py — accessed 2026-11-08
11. vulture `vulture/reachability.py`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/vulture/reachability.py — accessed 2026-11-08
12. vulture `vulture/noqa.py`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/vulture/noqa.py — accessed 2026-11-08
13. vulture `vulture/utils.py`, tag `v2.16` — https://github.com/jendrikseipp/vulture/blob/v2.16/vulture/utils.py — accessed 2026-11-08
14. vulture `vulture/whitelists/` tree, tag `v2.16` — https://github.com/jendrikseipp/vulture/tree/v2.16/vulture/whitelists — accessed 2026-11-08
15. vulture package metadata, PyPI JSON — https://pypi.org/pypi/vulture/json — accessed 2026-11-08

[![Deadcode Logo](https://raw.githubusercontent.com/albertas/deadcode/main/docs/_static/deadcode-logo-readme.png)](https://deadcode.readthedocs.io/)

<h2 align="center">Find and Fix Unused Python Code</h2>

<p align="center">
<a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit" alt="pre-commit" style="max-width:100%;"></a>
<a href="https://pypi.org/project/deadcode/"><img alt="PyPI" src="https://img.shields.io/pypi/v/deadcode"></a>
<a href="https://www.python.org/downloads/"><img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue"></a>
<a href="https://pepy.tech/project/deadcode"><img alt="Downloads" src="https://static.pepy.tech/badge/deadcode"></a>
<a href="https://github.com/albertas/deadcode/blob/main/LICENSE"><img alt="License: AGPLv3" src="https://raw.githubusercontent.com/albertas/deadcode/main/docs/_static/AGPLv3-license.svg"></a>
<a href="https://codecov.io/gh/albertas/deadcode"><img alt="Coverage" src="https://codecov.io/gh/albertas/deadcode/branch/main/graph/badge.svg"></a>
<a href="https://github.com/albertas/deadcode/actions/workflows/test.yml"><img alt="CI" src="https://github.com/albertas/deadcode/actions/workflows/test.yml/badge.svg?branch=main"></a>
<br/><a href='https://ko-fi.com/V7V21681GD' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi3.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
</p>


<p align="center">
<a href="https://deadcode.readthedocs.io/"><img src="https://img.shields.io/badge/docs-Read%20the%20Docs-blue?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Documentation" height="40"></a>
</p>

## Installation
```shell
pip install deadcode
```

## Usage

> **Full documentation:** [deadcode.readthedocs.io](https://deadcode.readthedocs.io/)

To see unused code findings:
```shell
deadcode .
```

To see suggested fixes for all files:
```shell
deadcode . --fix --dry
```

To see suggested fixes only for `foo.py` file:
```shell
deadcode . --fix --dry --only foo.py
```

To fix:
```shell
deadcode . --fix
```

Tune out some of the false positives, e.g.:
```
deadcode . --exclude=venv,tests --ignore-names=BaseTestCase,*Mixin --ignore-names-in-files=migrations
```

The same options can be provided in `pyproject.toml` settings file:
```
[tool.deadcode]
exclude = ["venv", "tests"]
ignore-names = ["BaseTestCase", "*Mixin"]
ignore-names-in-files = ["migrations"]
ignore-names-if-inherits-from = ["BaseModel", "*.ObjectType"]
```

## Using deadcode on a FastAPI project

FastAPI registers handlers through decorators and populates Pydantic model fields at runtime, so both look unused to a static analyser.
Configure deadcode like this:

```toml
[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
```

Read the [FastAPI guide](https://deadcode.readthedocs.io/en/latest/fastapi.html) for common use cases, the complete example application,
the dependency injection strategy, and the expected output with no wrong detections.

## Using deadcode on a Django project

Django registers models, views, admin classes, middleware, and signal handlers through base classes, decorators, settings strings, and URLconfs, so
framework entry points look unused to a static analyser. Configure deadcode like this:

```toml
[tool.deadcode]
ignore-definitions-if-decorated-with = [
    "@django.contrib.admin.*",
    "@django.contrib.auth.*",
    "@django.dispatch.receiver",
    "@django.utils.decorators.method_decorator",
    "@django.views.decorators.http.require_*",
    "@*register.*",
]
ignore-definitions-if-inherits-from = [
    "django.apps.AppConfig",
    "django.contrib.admin.*",
    "django.core.management.base.BaseCommand",
    "django.db.migrations.Migration",
    "django.db.models.Model",
    "django.forms.*Form",
    "django.utils.deprecation.MiddlewareMixin",
    "django.views.*View",
]
ignore-names-in-files = ["*/settings.py", "*/urls.py"]
```

The example targets Django 5.2 LTS (5.2.19). The three keys replace the
older overlapping name, body, and definition options: one inheritance entry hides a framework subclass name and body, and one decorator entry hides a
decorated definition name and body. deadcode parses `MIDDLEWARE` registrations and resolves absolute-import qualified names, so a registered middleware
name and a `models.Model` base need no separate name pattern.

Read the [Django guide](https://deadcode.readthedocs.io/en/latest/django.html) for the framework areas, the current and legacy
middleware forms, both import forms, database signals, and the expected behaviour.

## Pre-commit hook
Create a `.pre-commit-config.yaml` file in the root of your project directory, if it doesn't exist, and add the following to the file:

```
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
  - repo: https://github.com/albertas/deadcode
    rev: v2.6.1
    hooks:
      - id: deadcode
```

The `rev` is the release tag, so it matches the version published on PyPI. To
run the same hook while developing deadcode itself, use `make pre-commit`.

## Command line options

| Option&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Type | Meaning  |
|-------------------------------------------|------|----------------------------------------------------------------------|
|`--fix`                                    | -    | Automatically remove detected unused code expressions from the code base. |
|`--dry`                                    | -    | Show changes which would be made in files. |
|`--only`                                   | list | Filenames (or path expressions), that will be reflected in the output (and modified if needed). |
|`--exclude`                                | list | Filenames (or path expressions), which will be completely skipped without being analysed. |
|`--ignore-names`                           | list | Removes provided list of names from the output. Glob expressions to match multiple names can also be provided, e.g. `*Mixin` will match all classes ending with `Mixin`. |
|`--ignore-names-in-files`                  | list | Ignores unused names in files, which filenames match provided path expressions. |
|`--ignore-names-if-inherits-from`          | list | Ignores names of classes which inherit from any of the provided class names. The class name may be a plain name, a dotted path such as `graphene.ObjectType`, or a glob such as `*.ObjectType`; a dotted base also matches its final component (`ObjectType`). Only the class name is suppressed; its members and body are controlled by `--ignore-bodies-if-inherits-from` and `--ignore-definitions-if-inherits-from`. |
|`--ignore-names-if-decorated-with`         | list | Ignores names of an expression, which is decorated with one of the provided decorator names. |
|`--ignore-bodies-of`                       | list | Ignores body of an expression if its name matches any of the provided names. |
|`--ignore-bodies-if-decorated-with`        | list | Ignores body of an expression if its decorated with one of the provided decorator names. |
|`--ignore-bodies-if-inherits-from`         | list | Ignores body of a class if it inherits from any of the provided class names. The class name may be a plain name, a dotted path such as `graphene.ObjectType`, or a glob such as `*.ObjectType`; a dotted base also matches its final component (`ObjectType`). |
|`--ignore-definitions`                     | list | Ignores definition (including name and body) if a name of an expression matches any of the provided ones. Applies to class, function, method and property definitions, not to variables, attributes or imports; use `--ignore-names` for those. |
|`--ignore-definitions-if-inherits-from`    | list | Ignores definition (including name and body) of a class if it inherits from any of the provided class names. The class name may be a plain name, a dotted path such as `graphene.ObjectType`, or a glob such as `*.ObjectType`; a dotted base also matches its final component (`ObjectType`). |
|`--ignore-definitions-if-decorated-with`   | list | Ignores definition (including name and body) of an expression, which is decorated with any of the provided decorator names. |
|`--no-color`                               | -    | Removes colors from the output. |
|`--count`                                  | -    | Provides the count of the detected unused names instead of printing them all out. |
|`--quiet`                                  | -    | Does not output anything. The command exits with code 1 if unused names are found. |
|`-V`, `--version`                          | -    | Shows `deadcode` version. |
|`-v`, `--verbose`                          | -    | Shows verbose logging output. |

### Glossary
- `name` - variable, function or class name.
- `body` - code block which follows after `:` in function or class definition. A body ignore suppresses every definition inside the expression, including nested classes and functions.
- `definition` - whole class or function definition expression including its name and body.

### Decorator matching
Decorator names are written as in the source, including the leading `@`; a pattern without `@` matches nothing.
Entries are glob patterns matched with `fnmatch.fnmatchcase`, so `*`, `?` and `[seq]` apply and `*` also crosses dots
(`@app.*` matches `@app.route`). Matching is case-sensitive.
Decorator call arguments are ignored, so `@app.route("/")` is matched as `@app.route`.
Stacked decorators match when any one decorator matches.
All three decorated-with options behave the same way, covering classes, functions, async functions, methods and properties;
variables, attributes and imports are not covered.
Definitions decorated with `@abstractmethod` or `@override` are always ignored, with no option needed.
The recognized spellings are `@abstractmethod`, `@abc.abstractmethod`, `@override`, `@typing.override` and `@typing_extensions.override`.
The built-in markers match the decorator name only and, like the options, still analyse the decorated body for its own unused code.
Imports and aliases are not resolved, so `@aliased.route` needs `@aliased.*` rather than `@app.*`, and
`from abc import abstractmethod as abstract` renders `@abstract` and is not ignored.

```toml
[tool.deadcode]
ignore-names-if-decorated-with = ["@app.route"]
```

```python
@app.route("/", methods=["POST"])
def post_tax_adder_customer():
    pass
```

### Exit status

- `0` — no dead code found.
- `1` — dead code found (in any output mode).
- `2` — invalid command line usage.
- Unexpected errors print a Python traceback and exit `1`.

The status is independent of `--quiet`, `--count`, `--only`, `--dry`, and `--fix`.
A `--fix` run exits `1` on the run that found items and `0` on a subsequent run
over the cleaned tree.

## Ignoring checks with noqa comments
Inline `# noqa` comments can be used to ignore `deadcode` checks.
E.g. unused `Foo` class wont be detected/fixed because `# noqa: DC03` comment is used:

```python
class Foo:  # noqa: DC03
    pass
```

For a decorated function, method, property, or class, place the comment on the physical line of the `def`, `async def`, or `class` keyword:

```python
@cache
def foo():  # noqa: DC02
    pass
```

A comment on the first decorator line is still accepted.

### Rules
| Code   | Name               | Message        |
|--------|--------------------|----------------|
| DC01  | unused-variable      | Variable `{name}` is never used
| DC02  | unused-function      | Function `{name}` is never used
| DC03  | unused-class         | Class `{name}` is never used
| DC04  | unused-method        | Method `{name}` is never used
| DC05  | unused-attribute     | Attribute `{name}` is never used
| DC06  | unused-name          | Name `{name}` is never used
| DC07  | unused-import        | Import `{name}` is never used
| DC08  | unused-property      | Property `{name}` is never used
| DC09  | unreachable-body     | Unreachable body of a conditional statement or loop
| DC11  | empty-file           | Empty Python file
| DC12  | commented-out-code   | Commented out code
| DC13  | unreachable-code     | Code after terminal statement, e.g. `return`, `raise`, `continue`, `break`
| DC    | ignore-expression    | Do not show any findings for an expression, which starts on current line (this code can only be used in `# noqa: DC` comments)

## Ignoring unittest lifecycle methods
`unittest` lifecycle methods (`setUp`, `tearDown`, `setUpClass`, `tearDownClass`, `asyncSetUp`, `asyncTearDown`, `setUpModule`, `tearDownModule`) declared in test files are ignored by default, alongside the existing pytest hooks.
Declarations with those names outside test files are still reported as unused code.

## Ignoring Django test lifecycle methods
Django test lifecycle methods (`setUpTestData`, the `django.test.TestCase` class method invoked by the framework, and the internal hooks `_pre_setup`, `_post_teardown`, `_fixture_setup`, `_fixture_teardown`) declared in test files are ignored by default.
Declarations with those names outside test files are still reported as unused code.
Django helpers that your test code invokes itself are not suppressed, so an unreferenced `assertContains`, `assertNumQueries`, `settings`, `modify_settings`, or `captureOnCommitCallbacks` is still reported.

## Contributing

Create a feature branch from `main`, open a pull request targeting `main`, and
wait for review. Do not commit feature changes directly to `main`; release
commits are made by the maintainer on `main`.

- `make check` - runs unit tests and other checks using virtual environment.
- `make test` - runs the test suite in parallel with `pytest-xdist`, using one worker per logical CPU minus one.
  Set `PYTEST_XDIST_WORKERS` to change the worker count (`make test PYTEST_XDIST_WORKERS=2`), or pass
  `PYTEST_ME_PLEASE="-n 0"` to run serially.

### Enhancement proposals

A change that adds an analyser feature, changes rule semantics, or changes a documented process needs a Deadcode Enhancement Proposal (DEP).
The published process and template page is <https://deadcode.readthedocs.io/en/stable/dep.html>. The repository index of existing proposals is
`enhancement_proposals/dep_0.md`.

## Security

The runtime dependencies in `requirements.txt` and the development dependencies in `requirements-dev.txt` are audited for known
vulnerabilities with `pip-audit`. The `Vulnerability audit` workflow in `.github/workflows/vulnerability-audit.yml` runs on every pull request,
on every push to `main`, and weekly on a schedule. Run the same audit locally with `make audit`, `make audit-runtime`, or
`make audit-development`.

Read the [security documentation](https://deadcode.readthedocs.io/en/latest/security.html) for how to read and fix a finding. The only accepted
exception is `filelock==4.1.0` on Python 3.10, where the fix requires Python 3.11 or newer.

## Rationale
[ruff](https://pypi.org/project/ruff/) and
[flake8](https://pypi.org/project/flake8/) - don't have rules for unused global
code detection, only for local ones `F823`, `F841`, `F842`. `deadcode` package
tries to add new `DCXXX` checks for detecting variables/functions/classes/files
which are not used in a whole code base.

`deadcode` - is supposed to be used inline with other static code checkers like `ruff`.

There is an alternative [vulture](https://pypi.org/project/vulture/) package.

## Known limitations
In case there are several definitions using the same name - they all wont be
reported if at least one usage of that name is being detected.

Files with syntax errors will be ignored, because `deadcode` uses `ast` to
build abstract syntax tree for name usage detection.

It is assumed that `deadcode` will be run using the same or higher Python version as the
code base is implemented in.

Wildcard imports are resolved by module basename, without package paths, so modules with the same basename are treated as one.
`__all__` is honoured only when it is a statically readable module-level list or tuple of strings; modules with unknown exports
(dynamic `__all__`, unreadable or unparsable files, or modules outside the analysed file set) are not restricted. Without `__all__`,
the public module-level names are exported.

## Feature requests
A checked entry is implemented on `main` and is included in the next release; published releases may lag behind `main`.

- [x] Replace `.*` with only `*` in regexp matching.
- [x] Add unused class method detection DC04 check.
- [x] Add `--fix` option to automatically remove detected dead code occourencies
- [x] Add a check for empty python files.
- [x] Split error codes into DC01, DC02, DC03 for variables, functions, class.
    - [x] Should have different codes for ignoring name and ignoring whole definition (reserved DCxx0 - ignore name, DCxx1 - ignore definition).
    - [ ] Allow to disable each check separately using:
        - [ ] inline comment.
        - [ ] pyproject.toml file
- [x] Add a check for code in comments.
- [x] DC06: detect an unused name.
- [x] DC09: report an unreachable body, e.g. an `if` or `while` block that cannot run.
- [ ] Add target python version option, if specified it will be used for code base check.
- [ ] Add a `--depth` parameter to ignore nested code.. (To only check global scope use 0).
- [ ] Add options:
    - [x] --ignore-definitions
    - [x] --ignore-definitions-if-inherits-from
    - [x] --ignore-definitions-if-decorated-with
    - [x] --ignore-names-if-inherits-from
    - [x] --ignore-names-if-decorated-with
    - [x] --ignore-bodies-of
    - [x] --ignore-bodies-if-decorated-with
    - [x] --ignore-bodies-if-inherits-from
        - Question: would it be possible to ignore only certain types of checks for a body, e.g. only variable attributes of TypedDict and still check usage of methods and properties?
        - What expression would allow this type of precission?
- [ ] Distinguish between definitions with same name, but different files.
- [ ] Repeated application of `deadcode` till the output stops changing.
- [x] Unreachable code detection and fixing: this should only be scoped for if statements and only limited to primitive variables.
- [ ] Benchmarking performance with larger projects (time, CPU and memory consumption) in order to optimize.
- [ ] `--fix` could accept a list of filenames as well (only those files would be changed, but the summary could would be full).
    (This might be confusing, because filenames, which have to be considered are provided without any flag, --fix is expected to not accept arguments)
- [ ] pre-commit-hook.
- [ ] language server.
- [x] DC13: remove code after terminal statements like `raise`, `return`, `break`, `continue` and comes in the same scope.
- [ ] Add `ignore` and `per-file-ignores` command line and pyproject.toml options, which allows to skip some rules.
- [ ] Make sure that all rules are being skipped by `noqa` comment and all rules react to `noqa: rule_id` comments.
- [ ] Include package names into code item scope (dot-separated path), e.g. "package1.package2.module.class.method.variable".
- [ ] All options should be able to accept dot-separated path or a generic name, e.g. "marshmallow.Schema" vs "Schema",
  documentation should cleary demonstrate the behaviour/example that "Schema" means "*.Schema".
- [ ] Redefinition of an existing name makes previous name unreachable, unless it is assigned somehow.
- [ ] Check if file is still valid/parsable after automatic fixing, if not: halt the change and report error.
- [ ] Investigate ways of extracting and backporting Python3.10+ `ast` implementation to lower Python versions.

## Release notes
- next:
    - Features:
        - Document a staged Rust accelerator plan for issue #67 and list it in the DEP index
        - Publish the Deadcode Enhancement Proposal (DEP) process, template, and index.
        - Add a documentation page planning an experiment on large open source Python projects with candidate repositories, metrics and a measurement protocol.
        - Add DEP 4 proposing source-code tree pruning, with a survey of the JavaScript bundle-pruning tools that solve it and the capabilities expanding deadcode would require.
        - Add DEP 5 documenting how an unused definition shadowed by a used name could be detected.
        - Add DEP 7 documenting native SARIF output support and publish it in the DEP index
- **v2.6.1** `2026-11-11`:
    - Features:
        - Audit runtime and development dependencies for known vulnerabilities in CI on every pull request and weekly.
        - Declare the package development status as Beta.
        - Add a Django usage guide covering models, admin, views, forms, middleware, signals and more, plus Django `MIDDLEWARE` registration parsing and Django-aware qualified matching through absolute imports.
        - Django `MIDDLEWARE` registrations are treated as used and absolute-import qualified expressions resolve to their modules.
    - Bugfixes:
        - Support boolean flags such as `fix = true` and `dry = true` in `[tool.deadcode]` configuration.
- **v2.6.0** `2026-11-08`:
    - Features:
        - Add support for Python 3.13, 3.14 and 3.15.
        - Documentation is now published on Read the Docs at [deadcode.readthedocs.io](https://deadcode.readthedocs.io/).
        - Add `-V` as a short alias for `--version`.
        - `--ignore-definitions-if-decorated-with` now ignores whole decorated definitions
        - `--ignore-bodies-of` now suppresses the bodies of matching classes and functions
        - `--ignore-bodies-if-decorated-with` now suppresses the bodies of decorated definitions
        - `--ignore-names-if-inherits-from` now ignores class names matching a base class
        - `--ignore-definitions` now reliably ignores function, method, property and nested class definitions; its limits are documented
        - Add a code coverage badge to the README, fed by the coverage report uploaded from CI
        - Add a CI status badge for the test workflow to the README
        - Definitions decorated with `@abstractmethod` or `@override` are ignored by default (issue #40)
        - Implement DC06 unused names, DC09 unreachable bodies, DC12 commented-out code and DC13 unreachable code rules.
        - Enforce 100% line coverage of the `deadcode` package and keep every documented feature mapped to its source and tests.
        - Build the released version, stable and latest documentation automatically when `make publish` publishes a release
        - Add a documentation banner and a usage-section documentation callout to the README
    - Bugfixes:
        - Exit with code 1 when unused code is found, so CI jobs and pre-commit hooks can fail.
        - Fix `--fix` leaving invalid or partially removed imports when unused names are deleted from parenthesized or multi-line import statements.
        - Fix `--fix` leaving invalid or fragmented imports when removing names from backslash-continued, semicolon-separated, or commented import statements.
        - Fix `--fix` leaving the continuation lines of multi-line unused assignments behind and producing invalid Python (issue #26).
        - Do not crash when the terminal cannot encode CLI output, including the success message, warnings and verbose logs.
        - Fix `deadcode --fix` removing the `f` from the `from` keyword in multi-line parenthesized imports (issue #5)
        - Remove fully unused import statements, including multi-line parenthesized ones, without leaving broken syntax behind
        - Remove only the unused names from partially used import statements while keeping the used names and their order
        - Honor `# noqa` comments on the definition line of decorated functions, methods and classes.
        - Wildcard imports now honour a module `__all__` list or tuple, so excluded names are reported as unused. Wildcard imports stay unrestricted when `__all__` is dynamic or unknown, and explicit imports keep working. Without `__all__`, wildcard imports expose public module-level names.
        - Honour `--ignore-names-if-decorated-with` for dotted decorators such as `@app.route`, so route handlers are not reported as unused (issue #30).
        - Decorator names are reported as dotted identifiers such as `@app.get` instead of memory addresses
        - `--ignore-names-if-decorated-with` now suppresses decorated functions, methods, properties, and classes
        - Print verbose log messages as readable ASCII instead of a `bytes` repr when the output stream cannot encode a character.
        - `--ignore-bodies-if-inherits-from` and `--ignore-definitions-if-inherits-from` now recognize dotted base classes such as `graphene.ObjectType` and match their final component.
        - Render decorator names deterministically, including dotted names, and stop unusual decorators such as `@Class().function()` from crashing or producing memory addresses.
        - Stop reporting unittest lifecycle methods declared in test files as unused code (issue #21).
        - Use pytest instead of unittest.TestCase
        - Fix `ignore-names-if-inherits-from` having no effect when set in `pyproject.toml`; its accepted base-class forms and class-name-only scope are now documented (issue #25)
        - A scalar string in `pyproject.toml` is now honoured as one pattern instead of being split into characters
        - Names referenced from quoted type annotations (forward references) are no longer reported as unused imports.
        - Fix `--no-color` leaving colour codes in the success banner; Make `--count` count only findings reflected by `--only`; Make `--verbose` print INFO messages about ignored and scanned files
        - Rules now sit under Ignoring checks with noqa comments, the Glossary under Command line options, and Decorator matching is more concise.
        - Python 3.10+ requirement is now shown as a badge in the README
- **v2.5.0** `2026-11-07`:
        - Stop Codecov report comments on pull requests with no coverage findings
    - Bugfixes:
        - Fix a crash when a decorator has no `id` attribute.
- **v2.4.1** `2024-08-09`:
    - Features:
        - Add `--version` option to show `deadcode` version.
    - Bugfixes:
        - Use stdout for `deadcode` output.
- **v2.4.0** `2024-07-12`:
    - Features:
        - Add `--only` option that accepts filenames only which will be reflected in the output and modified.
          This option can be used with `--fix` and `--fix --dry` options as well as for simple unused code detection without fixing.
- **v2.3.2** `2024-07-10`:
    - Features:
        - Add `pre-commit` hook support.
        - Drop support for Python 3.8 and 3.9 versions, since their `ast` implementation is lacking features.
- **v2.3.1** `2024-07-03`:
    - Bugfixes:
        - Started analysing files in bytes instead of trying to convert them into UTF-8 encoded strings.
        - Improved automatic removal of unused imports.
- **v2.3.0** `2024-04-07`:
    - Features:
        - Add `--dry` option.
        - Update error codes to use DCXX format instead of DCXXX.

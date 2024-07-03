[![Deadcode Logo](https://raw.githubusercontent.com/albertas/deadcode/main/docs/_static/deadcode-logo-readme.png)](https://deadcode.readthedocs.io/en/stable/)

<h2 align="center">Find and Fix Unused Python Code</h2>

<p align="center">
<a href="https://github.com/albertas/deadcode/blob/main/LICENSE"><img alt="License: AGPLv3" src="https://raw.githubusercontent.com/albertas/deadcode/main/docs/_static/AGPLv3-license.svg"></a>
<a href="https://pypi.org/project/deadcode/"><img alt="PyPI" src="https://img.shields.io/pypi/v/deadcode"></a>
<a href="https://pepy.tech/project/deadcode"><img alt="Downloads" src="https://static.pepy.tech/badge/deadcode"></a>
</p>


## Installation
```shell
pip install deadcode
```

## Usage
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
deadcode . --fix --dry foo.py
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
```

## Command line options

| Option&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Type | Meaning  |
|-------------------------------------------|------|----------------------------------------------------------------------|
|`--fix`                                    | -    | Automatically remove detected unused code expressions from the code base. |
|`--dry`                                    | - or list | Show changes which would be made in files. Shows changes for provided filenames or shows all changes if no filename is specified. |
|`--exclude`                                | list | Filenames (or path expressions), which will be completely skipped without being analysed. |
|`--ignore-names`                           | list | Removes provided list of names from the output. Regexp expressions to match multiple names can also be provided, e.g. `*Mixin` will match all classes ending with `Mixin`. |
|`--ignore-names-in-files`                  | list | Ignores unused names in files, which filenames match provided path expressions. |
|`--ignore-names-if-inherits-from`          | list | Ignores names of classes, which inherit from provided class names. |
|`--ignore-names-if-decorated-with`         | list | Ignores names of an expression, which is decorated with one of the provided decorator names. |
|`--ignore-bodies-of`                       | list | Ignores body of an expression if its name matches any of the provided names. |
|`--ignore-bodies-if-decorated-with`        | list | Ignores body of an expression if its decorated with one of the provided decorator names. |
|`--ignore-bodies-if-inherits-from`         | list | Ignores body of a class if it inherits from any of the provided class names. |
|`--ignore-definitions`                     | list | Ignores definition (including name and body) if a name of an expression matches any of the provided ones. |
|`--ignore-definitions-if-inherits-from`    | list | Ignores definition (including name and body) of a class if it inherits from any of the provided class names. |
|`--ignore-definitions-if-decorated-with`   | list | Ignores definition (including name and body) of an expression, which is decorated with any of the provided decorator names. |
|`--no-color`                               | -    | Removes colors from the output. |
|`--count`                                  | -    | Provides the count of the detected unused names instead of printing them all out. |
|`--quiet`                                  | -    | Does not output anything. Makefile still fails with exit code 1 if unused names are found. |


##### Glossory
name - variable, function or class name.
body - code block which follows after `:` in function or class definition.
definition - whole class or function definition expression including its name and body.


## Rules
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
| DC09  | unreachable-if-block | Unreachable conditional statement block
| DC11  | empty-file           | Empty Python file
| DC12  | commented-out-code   | Commented out code
| DC13  | unreachable-code     | Code after terminal statement, e.g. `return`, `raise`, `continue`, `break`
| DC    | ignore-expression    | Do not show any findings for an expression, which starts on current line (this code can only be used in `# noqa: DC` comments)

## Ignoring checks with noqa comments
Inline `# noqa` comments can be used to ignore `deadcode` checks.
E.g. unused `Foo` class wont be detected/fixed because `# noqa: DC03` comment is used:

```python
class Foo:  # noqa: DC03
    pass
```

## Contributing
- `make check` - runs unit tests and other checks using virtual environment.

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

## Feature requests
- [x] Replace `.*` with only `*` in regexp matching.
- [x] Add unused class method detection DC04 check.
- [x] Add `--fix` option to automatically remove detected dead code occourencies
- [x] Add a check for empty python files.
- [x] Split error codes into DC01, DC02, DC03 for variables, functions, class.
    - [x] Should have different codes for ignoring name and ignoring whole definition (reserved DCxx0 - ignore name, DCxx1 - ignore definition).
    - [ ] Allow to disable each check separately using:
        - [ ] inline comment.
        - [ ] pyproject.toml file
- [ ] Add a check for code in comments.
- [ ] Add target python version option, if specified it will be used for code base check.
- [ ] Add a `--depth` parameter to ignore nested code.. (To only check global scope use 0).
- [ ] Add options:
    - [x] --ignore-definitions
    - [x] --ignore-definitions-if-inherits-from
    - [ ] --ignore-definitions-if-decorated-with
    - [ ] --ignore-names-if-inherits-from
    - [ ] --ignore-names-if-decorated-with
    - [ ] --ignore-bodies-of
    - [ ] --ignore-bodies-if-decorated-with
    - [ ] --ignore-bodies-if-inherits-from
    - [ ] --ignore-definitions
    - [ ] --ignore-definitions-if-inherits-from
    - [ ] --ignore-definitions-if-decorated-with
        - Question: would it be possible to ignore only certain types of checks for a body, e.g. only variable attributes of TypedDict and still check usage of methods and properties?
        - What expression would allow this type of precission?
- [ ] Distinguish between definitions with same name, but different files.
- [ ] Repeated application of `deadcode` till the output stops changing.
- [ ] Unreachable code detection and fixing: this should only be scoped for if statements and only limited to primitive variables.
- [x] `--fix --dry [filenames]` - only show whats about to change in the listed filenames.
- [ ] Benchmarking performance with larger projects (time, CPU and memory consumption) in order to optimize.
- [ ] `--fix` could accept a list of filenames as well (only those files would be changed, but the summary could would be full).
    (This might be confusing, because filenames, which have to be considered are provided without any flag, --fix is expected to not accept arguments)
- [ ] pre-commit-hook.
- [ ] language server.
- [x] Use only two digits for error codes instead of 3. Two is plenty and it simplifies usage a bit
- [ ] DC10: remove code after terminal statements like `raise`, `return`, `break`, `continue` and comes in the same scope.
- [ ] Add `ignore` and `per-file-ignores` command line and pyproject.toml options, which allows to skip some rules.
- [ ] Make sure that all rules are being skipped by `noqa` comment and all rules react to `noqa: rule_id` comments.
- [ ] Include package names into code item scope (dot-separated path), e.g. "package1.package2.module.class.method.variable".
- [ ] All options should be able to accept dot-separated path or a generic name, e.g. "marshmallow.Schema" vs "Schema",
  documentation should cleary demonstrate the behaviour/example that "Schema" means "*.Schema".
- [ ] Redefinition of an existing name makes previous name unreachable, unless it is assigned somehow.
- [ ] Check if file is still valid/parsable after automatic fixing, if not: halt the change and report error.

## Release notes
- v2.3.1:
    - Started analysing files in bytes instead of trying to convert them into UTF-8 encoded strings.
    - Improved automatic removal of unused imports.
- v2.3.0:
    - Add `--dry` option.
    - Update error codes to use DCXX format instead of DCXXX.

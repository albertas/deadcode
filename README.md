# deadcode
`deadcode` allows to detect and fix unused Python code. It implements `DCXXX`
static code linting rules for detecting unused code such as
variables, functions and classes.

## Installation
```shell
pip install deadcode
```

## Usage
```shell
deadcode .
```

Or with command line options:
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

### Command line options

| Option&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Type | Meaning  |
|-------------------------------------------|------|----------------------------------------------------------------------|
|`--fix`                                    | -    | Automatically remove detected unused code expressions from the code base. |
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
| DC001  | unused-variable    | Variable `{name}` is never used
| DC002  | unused-function    | Function `{name}` is never used
| DC003  | unused-class       | Class `{name}` is never used
| DC004  | unused-method      | Method `{name}` is never used
| DC005  | unused-attribute   | Attribute `{name}` is never used
| DC006  | unused-name        | Name `{name}` is never used
| DC007  | unused-import      | Import `{name}` is never used
| DC008  | unused-property    | Property `{name}` is never used
| DC009  | unreachable-code   | Unreachable `else` block
| DC011  | empty-file         | Empty file
| DC012* | commented-out-code | Commented out code
| DC013* | ignore-expression  | *This error code can ony be used in `# noqa: DC013` comments (no errors will be reported for expression which begins in current line)*

`*` - are not yet implemented rules.

## Ignoring checks with noqa comments
Inline `# noqa` comments can be used to ignore `deadcode` checks.
E.g. unused `Foo` class wont be detected/fixed because `# noqa: DC003` comment is used:

```python
class Foo:  # noqa: DC003
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
- [x] Add unused class method detection DC004 check.
- [x] Add `--fix` option to automatically remove detected dead code occourencies
- [x] Add a check for empty python files.
- [x] Split error codes into DC001, DC002, DC003 for variables, functions, class.
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
- [ ] Distinguish between definitions with same name, but different files.

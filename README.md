# deadcode
`deadcode` package implements `DC100` - `unused-global-name` check for detecting
variable/function/class names which are never used in a whole code base.
Only globally defined names are being checked.
Unused local names can be detected by other tools like [ruff](https://pypi.org/project/ruff/).

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
ignore-names = ["BaseTestCase"]
ignore-names-in-files = ["migrations"]
```

### Command line options

| Option&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Type | Meaning  |
|--------------------------|------|----------|
|`--fix`                   | None | Automatically remove detected unused code parts from the code base. |
|`--exclude`               | list | Path expressions to completely skip files from being analysed. |
|`--ignore-names`          | list | Removes provided list of names from the error output. Regexp expressions to match multiple names can also be provided, e.g. `*Mixin` will match all classes ending with `Mixin`. |
|`--ignore-names-in-files` | list | Unused names from files matching provided path expressions. |
|`--no-color`              | None | Removes colors from the output. |
|`--count`                 | None | Provides the count of the detected unused names instead of printing them all out. |
|`--quiet`                 | None | Does not output anything. Makefile still fails with exit code 1 if unused names are found. |


## Contributing
- `make check` - runs unit tests and other checks using virtual environment.

## Rationale
[ruff](https://pypi.org/project/ruff/) and
[flake8](https://pypi.org/project/flake8/) - don't have rules for unused global
code detection, only for local ones `F823`, `F841`, `F842`. `deadcode` package
tries to add a new `DC100` check for detecting variables/functions/classes
which are not used in a whole code base.

There is an alternative [vulture](https://pypi.org/project/vulture/) package,
which provides many false positives.
`deadcode` - tries to find less, but findings are with higher confidence.
`deadcode` - is supposed to be used inline with other static code checkers like `ruff`.

## Known limitations
If the same unused name is repeated in several files - it wont be detected.

Files with syntax errors will be ignored, because `deadcode` uses `ast` to
build abstract syntax tree for name usage detection.

It is assumed that `deadcode` will be run using the same Python version as the
checked code base is implemented in.

## Feature requests
- [x] Replace `.*` with only `*` in regexp matching.
- [x] Add unused class method detection DC310 check.
- [x] Add `--fix` option to automatically remove detected dead code occourencies
- [x] Add a check for empty python files.
- [x] Split error codes into DC010, DC020, DC030 for variables, functions, class.
    - [x] Should have different codes for ignoring name and ignoring whole definition (reserved DCxx0 - ignore name, DCxx1 - ignore definition).
    - [ ] Allow to disable each check separately using:
        - [ ] inline comment.
        - [ ] pyproject.toml file
- [ ] Add a check for code in comments.
- [ ] Add target python version option, if specified it will be used for code base check.
- [ ] Add a `--depth` parameter to ignore nested code.. (To only check global scope use 0).
- [ ] Add options:
    - [ ] --ignore-definitions
    - [ ] --ignore-definitions-if-inherits-from
    - [ ] --ignore-definitions-if-decorated-with
    - [ ] --ignore-names-if-inherits-from
    - [ ] --ignore-names-if-decorated-with
- [ ] Distinguish between definitions with same name, but different files.

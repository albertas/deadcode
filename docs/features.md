# Features

This page maps every behaviour that the README advertises to the source code that implements it and to the pytest files that cover it.
The map is a contract: `tests/documented_examples/test_documented_features.py` parses the table below and fails when a documented option, rule, feature, source
path, or test path disappears, when a feature name is duplicated, when a cell is empty, or when a row has fewer than its declared minimum
number of test cases.

Use the table when you add a README feature: add a row, point it at the implementation and at least three test functions, and keep the
feature name unique. Use it when you review a change: a behaviour change that touches a row must update the row in the same pull request.

## Coverage map

Each row names one behaviour from the README, the README section that documents it, the source files that implement it, and the pytest
files that exercise it. `Minimum test cases` is the number of test functions that the union of the row's test files must define; it is `3`
for every row.

| Feature | README | Source | Tests | Minimum test cases |
|---|---|---|---|---|
| Detection and usage examples | `## Usage` | `deadcode/cli.py`, `deadcode/actions/find_unused_names.py` | `tests/cli/test_deadcode.py`, `tests/cli/test_output.py` | 3 |
| `--fix` | `## Command line options` | `deadcode/actions/fix_or_show_unused_code.py` | `tests/cli_args/test_fix.py`, `tests/fix/test_assign.py` | 3 |
| `--dry` | `## Command line options` | `deadcode/actions/fix_or_show_unused_code.py`, `deadcode/actions/parse_arguments.py` | `tests/cli_args/test_dry.py` | 3 |
| `--only` | `## Command line options` | `deadcode/actions/get_unused_names_error_message.py` | `tests/cli_args/test_only.py` | 3 |
| `--exclude` | `## Command line options` | `deadcode/actions/find_python_filenames.py` | `tests/cli_args/test_exclude.py` | 3 |
| `--ignore-names` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_names.py` | 3 |
| `--ignore-names-in-files` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_names_in_files.py` | 3 |
| `--ignore-names-if-inherits-from` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_names_if_inherits_from.py` | 3 |
| `--ignore-names-if-decorated-with` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_names_if_decorated_with.py` | 3 |
| `--ignore-bodies-of` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_bodies_of.py` | 3 |
| `--ignore-bodies-if-decorated-with` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_bodies_if_decorated_with.py` | 3 |
| `--ignore-bodies-if-inherits-from` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_bodies_if_inherits_from.py` | 3 |
| `--ignore-definitions` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_definitions.py` | 3 |
| `--ignore-definitions-if-inherits-from` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_definitions_if_inherits_from.py` | 3 |
| `--ignore-definitions-if-decorated-with` | `## Command line options` | `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_definitions_if_decorated_with.py` | 3 |
| `[tool.deadcode]` settings | `## Usage` | `deadcode/actions/parse_arguments.py` | `tests/cli_args/test_parsing.py`, `tests/configuration/test_decorator_pyproject_configuration.py` | 3 |
| `--no-color` | `## Command line options` | `deadcode/utils/add_colors_to_diff.py` | `tests/cli_args/test_no_color.py`, `tests/cli/test_output.py` | 3 |
| `--count` | `## Command line options` | `deadcode/actions/get_unused_names_error_message.py` | `tests/cli_args/test_count.py` | 3 |
| `--quiet` | `## Command line options` | `deadcode/actions/get_unused_names_error_message.py` | `tests/cli_args/test_quiet.py` | 3 |
| `-V` / `--version` | `## Command line options` | `deadcode/cli.py`, `deadcode/__init__.py` | `tests/cli_args/test_version.py` | 3 |
| `-v` / `--verbose` | `## Command line options` | `deadcode/actions/find_python_filenames.py` | `tests/cli_args/test_verbose.py`, `tests/cli/test_verbose_output_encoding.py` | 3 |
| Decorator matching rules | `### Decorator matching` | `deadcode/visitor/utils.py`, `deadcode/visitor/dead_code_visitor.py` | `tests/cli_args/test_ignore_names_if_decorated_with.py`, `tests/visitor/test_ignore_interface_decorators.py` | 3 |
| Exit status | `### Exit status` | `deadcode/cli.py` | `tests/cli/test_cli_exit_status.py` | 3 |
| Rules `DC01`-`DC09`, `DC11`-`DC13`, `DC` | `### Rules` | `deadcode/constants.py`, `deadcode/visitor/dead_code_visitor.py` | `tests/documented_examples/test_documented_rules.py`, `tests/noqa/test_noqa_comments.py` | 3 |
| Per-rule fixing | `### Rules` | `deadcode/actions/remove_file_parts_from_content.py` | `tests/fix/test_unused_imports.py`, `tests/fix/test_assign.py` | 3 |
| `# noqa` comments | `## Ignoring checks with noqa comments` | `deadcode/visitor/noqa.py` | `tests/noqa/test_noqa_comments.py` | 3 |
| Unittest lifecycle methods | `## Ignoring unittest lifecycle methods` | `deadcode/visitor/ignore.py` | `tests/visitor/test_unittest_lifecycle_methods.py` | 3 |
| Django test lifecycle methods | `## Ignoring Django test lifecycle methods` | `deadcode/visitor/ignore.py` | `tests/visitor/test_django_lifecycle_methods.py` | 3 |
| FastAPI guide | `## Using deadcode on a FastAPI project` | `deadcode/actions/parse_arguments.py` | `tests/documented_examples/test_fastapi.py`, `tests/documented_examples/test_fastapi_documentation.py` | 3 |
| Django guide | `## Using deadcode on a Django project` | `deadcode/actions/parse_arguments.py` | `tests/documented_examples/test_django.py` | 3 |
| Pre-commit hook | `## Pre-commit hook` | `.pre-commit-hooks.yaml` | `tests/documented_examples/test_pre_commit_hook_configuration.py` | 3 |
| Wildcard imports and `__all__` | `## Known limitations` | `deadcode/visitor/module_exports.py` | `tests/visitor/test_wildcard_imports.py` | 3 |
| Syntax-error files | `## Known limitations` | `deadcode/actions/parse_abstract_syntax_tree.py` | `tests/visitor/test_imports.py`, `tests/cli/test_deadcode.py` | 3 |
| Quoted annotations | `## Release notes` | `deadcode/visitor/utils.py` | `tests/visitor/test_imports.py` | 3 |
| Coverage badge | badge block | `.github/workflows/test.yml` | `tests/documented_examples/test_documented_features.py` | 3 |

## Not behaviour

These README sections are context rather than behaviour and are deliberately not contract rows: Installation, Rationale, Feature requests,
Glossary, Release notes, Contributing.

## Coverage policy

The measured scope is the `deadcode` package only, and the line-coverage target is 100%. Coverage is line-based: the project does not enable
branch coverage and adds no coverage configuration table.

A line may carry `# pragma: no cover` only when no Python version supported by the interpreter floor can execute it. The pragmas are limited to
those ten lines: the `importlib.metadata` fallback in `deadcode/__init__.py`, the two interpreter-conditional `tomllib`/`tomli` imports in
`deadcode/actions/parse_arguments.py`, and the two `except UnicodeError:` clauses in `deadcode/utils/fix_indent.py` (`bytes` and `str`). Every
other line is covered by a test that asserts an observable value or output, not merely that the line ran.

`make coverage-new BASE_BRANCH=origin/main` enforces 100% diff coverage for newly introduced package lines, and the pytest gate enforces 100%
package coverage for the whole suite. A defensive branch that a test cannot reach must be justified in the specification before it receives a
pragma; lowering the threshold is not an option.

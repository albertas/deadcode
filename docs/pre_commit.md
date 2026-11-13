# Pre-commit hook

This page explains how to set up the deadcode pre-commit hook, how to use it, and why its behaviour can differ from a direct `deadcode .` run.

## What the hook checks

The hook runs deadcode on the Python files that pre-commit passes to it. The commit is blocked when deadcode finds unused code, because the hook exits with a non-zero status.

## Install

Install pre-commit in the environment where you create commits:

```shell
pip install pre-commit
```

Then install the Git hook in the repository:

```shell
pre-commit install
```

## Configuration

Create a `.pre-commit-config.yaml` file in the root of your project directory, if it does not exist, and add the following:

```yaml
repos:
  - repo: https://github.com/albertas/deadcode
    rev: v2.6.2
    hooks:
      - id: deadcode
```

## The rev is a release tag

`rev` must be a released `X.Y.Z` tag, not a branch name or a raw commit SHA. The tag matches the version published on PyPI, so the hook installs the same released package.

To move to a newer release, run `pre-commit autoupdate`. It updates `rev` to the latest release tag.

## Automatic fixing

Add `args: [--fix]` to let the hook remove the findings instead of only reporting them:

```yaml
repos:
  - repo: https://github.com/albertas/deadcode
    rev: v2.6.2
    hooks:
      - id: deadcode
        args: [--fix]
```

The findings are removed from the changed files, and the hook exits `1` on the run that changed files. Review the changes with `git diff`, then run the commit again.

## Passing options and file selection

pre-commit appends the matched filenames to the hook command, so the effective command is `deadcode <matched files>` rather than the `deadcode .` you type in a terminal. Use the hook definition to control the file set:

- `types: [python]` selects Python files only.
- `exclude: ^tests/` skips files whose paths match the exclusion expression.
- `require_serial: true` runs the hook one file batch at a time instead of in parallel.

Extra deadcode options go under `args`, for example `args: [--no-color]` or `args: [--exclude, venv]`.

## Ignoring rules globally

Pass `--ignore` with one or more rule codes to suppress those findings for the whole hook run:

```yaml
repos:
  - repo: https://github.com/albertas/deadcode
    rev: v2.6.2
    hooks:
      - id: deadcode
        args: [--ignore, DC12]
```

The same rule codes can be configured once in `pyproject.toml` with `[tool.deadcode] ignore = ["DC12"]`.

## Exit status

- `0` when nothing is found.
- `1` when unused code is found.
- `2` for invalid command-line usage.

pre-commit reports any non-zero hook exit status as a failed hook.

## Running on all files

To check the whole repository instead of only the staged files, run:

```shell
pre-commit run deadcode --all-files
```

## Troubleshooting: why the hook differs from deadcode .

A hook run and a direct `deadcode .` run can give different results. There are three concrete causes:

1. The hook runs the console script installed from the pinned `rev` inside pre-commit's isolated environment, not the deadcode installed in your shell. An older `rev` therefore runs an older deadcode version.
2. The hook analyses only the files matched by `types` and `exclude`, while `deadcode .` walks the whole tree you point it at.
3. The hook's output is a captured pipe, and its encoding follows the platform code page (the report showed `cp1252` on Windows). Older deadcode versions used a direct `print` for some messages and could not encode characters such as `✨` on that code page. Current versions protect all CLI output, including the parse-failure warning and verbose messages, not only the success message.

## Solving it

Update `rev` to `v2.6.0` or newer. Those releases contain the Unicode-safe output chain for CLI messages in general: the success banner, findings, the parse-failure warning and verbose output use a plain print first, then `sys.stdout.reconfigure(encoding='utf-8')`, then ASCII with `?` replacements. The crash no longer occurs.

Setting `PYTHONUTF8=1` in the environment is an additional user-side workaround for older pinned versions.
